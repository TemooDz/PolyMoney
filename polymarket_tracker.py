"""
Polymarket Top Trader Intersection Tracker
==========================================
Fetches the top 20 traders by all-time PnL from Polymarket,
collects their active positions, finds shared/overlapping positions,
and emails a ranked report to you daily.

Setup:
  1. pip install requests python-dotenv
  2. Create a .env file (see .env.example)
  3. python polymarket_tracker.py
"""

import os
import sys
import time
import smtplib
import requests
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env vars must be set manually if python-dotenv isn't installed

# ── Configuration ─────────────────────────────────────────────────────────────

LEADERBOARD_URL = "https://data-api.polymarket.com/v1/leaderboard"
POSITIONS_URL   = "https://data-api.polymarket.com/positions"

TOP_N_TRADERS   = 50     # How many top traders to track
TOP_N_TIMEFRAME = "MONTH"  # DAY | WEEK | MONTH | ALL
MIN_TRADERS     = 3      # Minimum traders sharing a position to include in report

GMAIL_USER      = os.environ.get("GMAIL_USER", "temoodzneladze@gmail.com")
GMAIL_PASSWORD  = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT       = os.environ.get("RECIPIENT_EMAIL", "temoodzneladze@gmail.com")

HEADERS = {"User-Agent": "polymarket-tracker/1.0"}

# ── API helpers ────────────────────────────────────────────────────────────────

def get_leaderboard(limit=20):
    """Fetch top traders from Polymarket leaderboard."""
    params = {
        "limit": limit,
        "timePeriod": TOP_N_TIMEFRAME,
        "orderBy": "PNL",
    }
    resp = requests.get(LEADERBOARD_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_positions(proxy_wallet, retries=3):
    """Fetch all active positions for a wallet address."""
    params = {
        "user": proxy_wallet,
        "limit": 500,
        "sizeThreshold": 0.01,  # exclude dust
        "sortBy": "CURRENT",
        "sortDirection": "DESC",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(POSITIONS_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e
    return []

# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze(traders_positions):
    """
    Find markets held by multiple top traders.
    Returns a list of (market_key, [holder_info, ...], market_meta)
    sorted by holder count descending.
    """
    holders_by_market = defaultdict(list)  # (conditionId, outcome) -> [holder dicts]
    meta_by_market    = {}

    for wallet, positions in traders_positions.items():
        for pos in positions:
            condition_id = pos.get("conditionId", "")
            outcome      = pos.get("outcome", "")
            if not condition_id:
                continue

            key = (condition_id, outcome)
            holders_by_market[key].append({
                "wallet":        wallet,
                "size":          pos.get("size", 0),
                "avgPrice":      pos.get("avgPrice", 0),
                "curPrice":      pos.get("curPrice", 0),
                "currentValue":  pos.get("currentValue", 0),
                "cashPnl":       pos.get("cashPnl", 0),
                "percentPnl":    pos.get("percentPnl", 0),
            })

            if key not in meta_by_market:
                meta_by_market[key] = {
                    "title":    pos.get("title", "Unknown Market"),
                    "outcome":  outcome,
                    "endDate":  pos.get("endDate", ""),
                    "slug":     pos.get("slug", ""),
                    "eventSlug":pos.get("eventSlug", ""),
                }

    # Sort by number of holders descending
    sorted_markets = sorted(
        holders_by_market.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )
    return sorted_markets, meta_by_market

# ── Email builder ──────────────────────────────────────────────────────────────

def build_html(sorted_markets, meta_by_market, leaderboard, min_traders=2):
    """Render a clean HTML email with all intersections."""

    # Map wallet -> display name
    name_map = {}
    for i, t in enumerate(leaderboard):
        w = t.get("proxyWallet", "")
        n = t.get("userName") or f"Trader #{i+1}"
        name_map[w] = n

    date_str = datetime.now().strftime("%B %d, %Y at %H:%M UTC")

    intersections = [(k, v) for k, v in sorted_markets if len(v) >= min_traders]

    # Summary stats
    total_markets  = len(intersections)
    max_overlap    = max((len(v) for _, v in intersections), default=0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
          background: #0f1117; color: #e2e8f0; padding: 24px; }}
  .container {{ max-width: 760px; margin: 0 auto; }}
  .header {{ background: linear-gradient(135deg, #1e2a47, #16213e);
             border-radius: 12px; padding: 28px; margin-bottom: 24px;
             border: 1px solid #2d3a5e; }}
  .header h1 {{ font-size: 24px; color: #60a5fa; margin-bottom: 6px; }}
  .header p  {{ color: #94a3b8; font-size: 14px; }}
  .stats {{ display: flex; gap: 16px; margin: 16px 0 0; }}
  .stat  {{ background: rgba(255,255,255,0.05); border-radius: 8px;
            padding: 12px 18px; flex: 1; text-align: center; }}
  .stat .num {{ font-size: 28px; font-weight: 700; color: #60a5fa; }}
  .stat .lbl {{ font-size: 12px; color: #94a3b8; margin-top: 2px; }}
  .section-title {{ font-size: 13px; text-transform: uppercase; letter-spacing: 1px;
                    color: #64748b; margin: 24px 0 12px; }}
  .card {{ background: #1a2035; border: 1px solid #2d3a5e; border-radius: 10px;
           padding: 18px; margin-bottom: 14px; }}
  .card-header {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }}
  .badge {{ background: #3b4fd4; color: white; border-radius: 20px;
            padding: 4px 12px; font-size: 12px; font-weight: 700;
            white-space: nowrap; flex-shrink: 0; }}
  .badge.high {{ background: #059669; }}
  .badge.medium {{ background: #d97706; }}
  .market-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; line-height: 1.4; }}
  .market-title a {{ color: #60a5fa; text-decoration: none; }}
  .market-title a:hover {{ text-decoration: underline; }}
  .meta {{ display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }}
  .meta-item {{ font-size: 12px; }}
  .meta-item .label {{ color: #64748b; }}
  .meta-item .value {{ color: #e2e8f0; font-weight: 600; }}
  .outcome-yes {{ color: #34d399; }}
  .outcome-no  {{ color: #f87171; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead tr {{ background: rgba(255,255,255,0.04); }}
  th {{ text-align: left; padding: 8px 10px; color: #64748b;
        font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ padding: 8px 10px; border-top: 1px solid #232b3e; color: #cbd5e1; }}
  .pos {{ color: #34d399; }}
  .neg {{ color: #f87171; }}
  .footer {{ text-align: center; color: #475569; font-size: 12px;
             margin-top: 32px; padding-top: 20px; border-top: 1px solid #1e293b; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>🎯 Polymarket — Weekly Smart Money Intersections</h1>
    <p>{date_str} &nbsp;·&nbsp; Top {len(leaderboard)} traders by This Week's PnL</p>
    <div class="stats">
      <div class="stat"><div class="num">{total_markets}</div><div class="lbl">Shared Positions</div></div>
      <div class="stat"><div class="num">{max_overlap}</div><div class="lbl">Highest Overlap</div></div>
      <div class="stat"><div class="num">{len(leaderboard)}</div><div class="lbl">Traders Tracked</div></div>
    </div>
  </div>
"""

    if not intersections:
        html += """
  <div class="card" style="text-align:center; padding:40px; color:#64748b;">
    No shared positions found among the top traders right now.
  </div>
"""
    else:
        html += '<p class="section-title">Positions ranked by number of top traders holding them</p>'

        for (condition_id, outcome), holders in intersections:
            count = len(holders)
            meta  = meta_by_market.get((condition_id, outcome), {})
            title = meta.get("title", "Unknown Market")
            slug  = meta.get("eventSlug") or meta.get("slug", "")
            end_date_raw = meta.get("endDate", "")
            end_date = end_date_raw[:10] if end_date_raw else "—"

            market_url = f"https://polymarket.com/event/{slug}" if slug else ""

            total_value = sum(h["currentValue"] for h in holders)
            avg_price   = sum(h["curPrice"] for h in holders) / count

            # Badge color
            if count >= 10:
                badge_class = "badge high"
            elif count >= 5:
                badge_class = "badge medium"
            else:
                badge_class = "badge"

            outcome_class = "outcome-yes" if outcome.upper() in ("YES", "YES", "1") else "outcome-no"

            title_html = (
                f'<a href="{market_url}">{title}</a>'
                if market_url else title
            )

            html += f"""
  <div class="card">
    <div class="card-header">
      <span class="{badge_class}">{count} traders</span>
      <div class="market-title">{title_html}</div>
    </div>
    <div class="meta">
      <div class="meta-item"><span class="label">Side: </span><span class="value {outcome_class}">{outcome}</span></div>
      <div class="meta-item"><span class="label">Mkt Price: </span><span class="value">{avg_price:.1%}</span></div>
      <div class="meta-item"><span class="label">Total Value: </span><span class="value">${total_value:,.0f}</span></div>
      <div class="meta-item"><span class="label">Resolves: </span><span class="value">{end_date}</span></div>
    </div>
    <table>
      <thead><tr>
        <th>Trader</th>
        <th>Shares</th>
        <th>Avg Buy</th>
        <th>Curr Price</th>
        <th>Value</th>
        <th>PnL $</th>
        <th>PnL %</th>
      </tr></thead>
      <tbody>
"""
            for h in sorted(holders, key=lambda x: x["currentValue"], reverse=True):
                name    = name_map.get(h["wallet"], h["wallet"][:10] + "…")
                pnl_cls = "pos" if h["cashPnl"] >= 0 else "neg"
                pct_cls = "pos" if h["percentPnl"] >= 0 else "neg"
                html += f"""
        <tr>
          <td>{name}</td>
          <td>{h['size']:,.0f}</td>
          <td>{h['avgPrice']:.1%}</td>
          <td>{h['curPrice']:.1%}</td>
          <td>${h['currentValue']:,.0f}</td>
          <td class="{pnl_cls}">${h['cashPnl']:+,.0f}</td>
          <td class="{pct_cls}">{h['percentPnl']:+.1f}%</td>
        </tr>"""

            html += """
      </tbody>
    </table>
  </div>
"""

    html += f"""
  <div class="footer">
    Generated by Polymarket Tracker &nbsp;·&nbsp; Data: data-api.polymarket.com<br>
    Unsubscribe by removing the scheduled task.
  </div>
</div>
</body>
</html>"""

    return html


# ── Email sender ───────────────────────────────────────────────────────────────

def send_email(subject, html_body, recipient, sender, password):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        print(f"  [ok] Email sent to {recipient}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("  Polymarket Top Trader Intersection Tracker")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 56)

    # 1. Leaderboard
    print(f"\n[1/3] Fetching top {TOP_N_TRADERS} traders (timeframe={TOP_N_TIMEFRAME} = this week's top traders)...")
    leaderboard = get_leaderboard(TOP_N_TRADERS)
    print(f"      Found {len(leaderboard)} traders")

    # 2. Positions
    print(f"\n[2/3] Fetching active positions for each trader...")
    traders_positions = {}
    for i, trader in enumerate(leaderboard):
        wallet = trader.get("proxyWallet", "")
        name   = trader.get("userName") or f"Trader #{i+1}"
        pnl    = trader.get("pnl", 0)
        if not wallet:
            continue
        print(f"  [{i+1:2d}] {name:<25} PnL=${pnl:>12,.0f}", end="  ->  ")
        try:
            positions = get_positions(wallet)
            active = [p for p in positions if p.get("currentValue", 0) > 0]
            traders_positions[wallet] = active
            print(f"{len(active)} active positions")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.3)  # be polite to the API

    # 3. Analysis
    print(f"\n[3/3] Analyzing intersections...")
    sorted_markets, meta_by_market = analyze(traders_positions)
    intersections = [(k, v) for k, v in sorted_markets if len(v) >= MIN_TRADERS]
    print(f"      {len(intersections)} markets held by {MIN_TRADERS}+ top traders")

    if intersections:
        print("\n  Top intersections:")
        for (cid, outcome), holders in intersections[:10]:
            meta  = meta_by_market.get((cid, outcome), {})
            title = meta.get("title", "?")[:50]
            print(f"  [{len(holders):2d} traders]  {outcome:<5} — {title}")

    # 4. Email / save report
    html    = build_html(sorted_markets, meta_by_market, leaderboard, MIN_TRADERS)
    subject = (
        f"🎯 Polymarket Weekly: {len(intersections)} smart-money overlaps "
        f"— Week of {datetime.now().strftime('%b %d, %Y')}"
    )

    report_path = os.path.join(os.path.dirname(__file__), "polymarket_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  Report saved -> {report_path}")

    if GMAIL_PASSWORD:
        print(f"\n  Sending email to {RECIPIENT}...")
        try:
            send_email(subject, html, RECIPIENT, GMAIL_USER, GMAIL_PASSWORD)
        except smtplib.SMTPAuthenticationError:
            print("  [x] Gmail auth failed - check GMAIL_APP_PASSWORD in .env")
            sys.exit(1)
    else:
        print("\n  [!] GMAIL_APP_PASSWORD not set.")
        print("     Report saved locally. Set the env var to enable email delivery.")
        print("     See README_SETUP.txt for instructions.")

    print("\n  Done!\n")


if __name__ == "__main__":
    main()
