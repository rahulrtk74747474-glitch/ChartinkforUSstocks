# Chartink for US Stocks

A Chartink-inspired technical scanner for US equities using Twelve Data daily OHLCV history. This is an original implementation and does not contain Chartink's proprietary code.

## Features
- Browser-based scan builder with AND/OR condition logic.
- Close, open, high, low, volume, SMA 20/50/200, RSI 14 and daily percentage change.
- Numeric or indicator comparisons, including cross-above and cross-below.
- Results table, per-ticker error reporting and CSV export.
- API key read only from the server environment.

## Run locally (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set TWELVE_DATA_API_KEY=your_real_key
uvicorn backend.app:app --reload
```
Open http://127.0.0.1:8000.

## API
- `GET /api/health` — configuration status; never returns the key.
- `POST /api/scan` — runs a scan.
- `GET /api/indicators` — supported indicator names.

Each ticker requests up to 220 daily bars to support SMA 200. A scan can use provider credits and take time; limit is 25 tickers per request. Check your Twelve Data plan and redistribution terms before public deployment. The application does not guarantee real-time prices.

Never commit `.env`, API keys, or credentials. A configured key does not prove a successful provider request; run a scan to verify access.

## Remaining work
This is the first scanner layer. Saved scans, accounts, scheduled scans, alerts, intraday scans, a broad US ticker master, caching and production rate limiting are not implemented yet.
