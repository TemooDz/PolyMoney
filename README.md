# Polymarket Top Trader Intersection Tracker

> **Follow the smart money.** Automatically finds prediction markets where multiple of Polymarket's top PnL traders are holding the same position — then emails you a ranked report on a schedule.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        POLYMARKET API                               │
│                   data-api.polymarket.com                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                    [1] Fetch Leaderboard
                    Top 50 traders by monthly PnL
                            │
                            ▼
          ┌─────────────────────────────────────┐
          │  Trader #1   Trader #2   Trader #3  │
          │  PnL: $820k  PnL: $640k PnL: $510k │
          │  ...         ...         ...        │
          └──────────┬──────────────────────────┘
                     │
             [2] For each trader,
             fetch active positions
                     │
        ┌────────────▼──────────────────────────┐
        │  Trader #1 holds:  Trader #2 holds:   │
        │   • Market A YES    • Market A YES     │
        │   • Market B YES    • Market C NO      │
        │   • Market D NO     • Market D NO      │
        └────────────┬──────────────────────────┘
                     │
              [3] Intersect:
        Which markets do 3+ traders share?
                     │
          ┌──────────▼──────────────┐
          │  Market A — 12 traders  │  ← HIGH CONVICTION
          │  Market D —  7 traders  │  ← MEDIUM
          │  Market F —  3 traders  │
          └──────────┬──────────────┘
                     │
              [4] Build & send
              HTML email report
                     │
                     ▼
           ┌─────────────────┐
           │   Your Inbox    │
           │  every Monday   │
           │   at 8:00 AM    │
           └─────────────────┘
```

---

## Report Preview

The email report is a dark-themed HTML page with this structure:

```
╔══════════════════════════════════════════════════════════════════╗
║  🎯 Polymarket — Weekly Smart Money Intersections                ║
║  June 02, 2026 at 08:00 UTC  ·  Top 50 traders by Monthly PnL  ║
║                                                                  ║
║   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         ║
║   │      14      │  │      12      │  │      50      │         ║
║   │ Shared Posns │  │ Highest Ovlp │  │ Traders Trkd │         ║
║   └──────────────┘  └──────────────┘  └──────────────┘         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │ [12 traders]  Will Trump win the 2026 midterms?         │    ║
║  │  Side: YES   Mkt Price: 62.3%   Total Value: $284,500   │    ║
║  │  ┌──────────┬────────┬─────────┬──────┬────────┬──────┐ │    ║
║  │  │ Trader   │ Shares │ Avg Buy │ Curr │ Value  │ PnL  │ │    ║
║  │  ├──────────┼────────┼─────────┼──────┼────────┼──────┤ │    ║
║  │  │ SirBets  │ 48,200 │  54.1%  │ 62%  │ $29,900│+$3.8k│ │    ║
║  │  │ WhaleX   │ 31,000 │  58.2%  │ 62%  │ $19,200│+$1.2k│ │    ║
║  │  │ ...      │  ...   │   ...   │ ...  │  ...   │  ... │ │    ║
║  │  └──────────┴────────┴─────────┴──────┴────────┴──────┘ │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  [ more cards ranked by overlap count... ]                       ║
╚══════════════════════════════════════════════════════════════════╝
```

Badge colors signal conviction level:

| Badge color | Meaning |
|-------------|---------|
| 🟢 Green | 10+ top traders share this position |
| 🟡 Amber | 5–9 top traders share this position |
| 🔵 Blue | 3–4 top traders share this position |

---

## Quick Start

### 1. Prerequisites

- Python 3.8+
- A Gmail account with [2-Step Verification](https://myaccount.google.com/security) enabled

### 2. Install

```bash
pip install requests python-dotenv
```

### 3. Configure credentials

Copy the example env file and fill in your details:

```bash
copy .env.example .env
```

Edit `.env`:

```ini
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 16-char App Password (not your real password)
RECIPIENT_EMAIL=you@gmail.com
```

**Getting a Gmail App Password:**

```
Google Account → Security → 2-Step Verification
→ Search "App passwords" → Mail / Windows Computer → Generate
```

### 4. Run

```bash
python polymarket_tracker.py
```

The script prints live progress, saves `polymarket_report.html` locally, and sends the email if credentials are set.

```
========================================================
  Polymarket Top Trader Intersection Tracker
  2026-06-02 08:00:01
========================================================

[1/3] Fetching top 50 traders (timeframe=MONTH)...
      Found 50 traders

[2/3] Fetching active positions for each trader...
  [ 1] SirBetsALot              PnL=  $820,400  ->  31 active positions
  [ 2] WhaleXYZ                 PnL=  $644,100  ->  18 active positions
  ...

[3/3] Analyzing intersections...
      14 markets held by 3+ top traders

  Top intersections:
  [12 traders]  YES  — Will Trump win the 2026 midterms?
  [ 7 traders]  YES  — Bitcoin above $120k before July?
  ...

  Report saved -> polymarket_report.html
  [ok] Email sent to you@gmail.com

  Done!
```

---

## Schedule Automated Runs (Windows)

### Easy — double-click

Run **`schedule_daily.bat`** as Administrator. It registers a Windows Task Scheduler job that fires every **Monday at 8:00 AM**.

### Manual

| Field | Value |
|-------|-------|
| Program | `python` |
| Arguments | `"C:\path\to\polymarket_tracker.py"` |
| Start in | `C:\path\to\this\folder` |
| Trigger | Weekly — Monday — 08:00 |

Verify: `schtasks /query /tn PolymarketWeeklyTracker`  
Run now: `schtasks /run /tn PolymarketWeeklyTracker`

---

## Configuration

All knobs are at the top of `polymarket_tracker.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOP_N_TRADERS` | `50` | How many leaderboard traders to track |
| `TOP_N_TIMEFRAME` | `"MONTH"` | Leaderboard window: `DAY` · `WEEK` · `MONTH` · `ALL` |
| `MIN_TRADERS` | `3` | Minimum overlap to include a market in the report |

**Examples:**

```python
# Track the all-time top 20 whales, only show 5+ trader overlaps
TOP_N_TRADERS   = 20
TOP_N_TIMEFRAME = "ALL"
MIN_TRADERS     = 5

# Daily signal — who's the hottest trader this week agreeing on something?
TOP_N_TRADERS   = 30
TOP_N_TIMEFRAME = "WEEK"
MIN_TRADERS     = 2
```

---

## Project Structure

```
polymarket_tracker.py   ← main script (single file, no database)
polymarket_report.html  ← generated on each run (open in browser to preview)
schedule_daily.bat      ← one-click Windows Task Scheduler setup
.env                    ← your credentials (never commit this)
.env.example            ← template to copy from
README_SETUP.txt        ← plain-text quickstart
```

---

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `data-api.polymarket.com/v1/leaderboard` | Top traders ranked by PnL |
| `data-api.polymarket.com/positions` | Active positions for a wallet |

No API key required. Requests are rate-limited politely (300 ms between wallets).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP calls to Polymarket API |
| `python-dotenv` | Load `.env` credentials |
| stdlib only | Everything else (`smtplib`, `email`, `collections`, `datetime`) |

---

## Security Notes

- **Never commit `.env`** — it contains your Gmail App Password.
- The App Password grants email-send access only; it cannot access your Google account.
- All API calls are read-only; no Polymarket account is required.
