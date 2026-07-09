# KRX Stock Scoring Dashboard

Mobile-friendly local dashboard for a KRX-based watchlist scoring workflow.

## What It Scores

- Relative strength: stock change rate versus the same-day market proxy
- Trading value maintenance: current trading value versus stored history
- ETF exposure: manually maintained score until ETF PDF automation is added
- Growth evidence: manually maintained score based on earnings, exports, and margin evidence
- Risk: liquidity weakness, sharp selloff, and manual risk notes

## Quick Start

```powershell
python -m stocks.krx_dashboard --update-on-start
```

Open:

```text
http://127.0.0.1:8765
```

For mobile access, keep the PC and phone on the same Wi-Fi and open:

```text
http://<PC-IP-address>:8765
```

## Daily 3-Time Updates

The server updates automatically at the times in:

```text
stocks/krx_dashboard/config.json
```

Default:

```json
["09:20", "12:30", "16:00"]
```

The server must be running for the built-in scheduler to execute. For Windows Task Scheduler, create three triggers that run:

```text
powershell.exe
```

Arguments:

```text
-ExecutionPolicy Bypass -File stocks\krx_dashboard\update_once.ps1
```

Start in:

```text
C:\Users\gimoo\Documents\시장공부
```

## Manual Inputs

Edit:

```text
data/krx_universe.csv
```

Columns:

- `ticker`: six-digit stock code
- `name`: display name
- `market`: KOSPI/KOSDAQ/etc.
- `sector`: your sector label
- `growth_score`: 0-100 evidence score from earnings, exports, margins, or orders
- `etf_exposure_score`: 0-100 ETF/PDF exposure score
- `risk_note`: risk memo; non-empty values reduce the score
- `thesis`: short reason to watch

## Data Files

- `data/krx_snapshots.csv`: stored raw snapshots
- `data/krx_scores.csv`: latest score table
- `data/krx_events.csv`: update log

If KRX download fails, the app falls back to `data/krx_universe.csv` so the dashboard remains usable.

