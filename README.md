# Chartink for US Stocks

A Chartink-inspired technical screener for US equities, using Twelve Data market history. It is an independent implementation, not Chartink source code or a claim of full feature parity.

## Current implementation
- Rule engine: AND/OR groups, nested groups, historical bar offsets, indicator-vs-number or indicator-vs-indicator comparisons, crosses, and count-of-events over a lookback.
- Indicators: OHLCV, SMA, EMA, WMA, RSI, MACD line/signal/histogram, Bollinger Bands, ATR, Stochastic %K/%D, OBV, VWAP, ROC, CCI, ADX and directional indicators.
- Web interface with scanner conditions, result table and CSV export.
- FastAPI endpoints for health and scans; Twelve Data key remains server-side.

## Run locally (PowerShell)
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
- `GET /api/health`
- `GET /api/indicators`
- `POST /api/scan`

## Important
Twelve Data interval, historical depth, exchange coverage and request quotas depend on your subscription. Intraday and multi-timeframe scans require provider support and appropriate access. No API key is returned by the application. Never commit `.env`.

## Not yet equivalent to all Chartink features
This project still needs persistent user accounts and permissions, saved scans UI and sharing, scheduled/live alerts, full historical backtesting charts, broad symbol/universe and fundamentals datasets, multi-timeframe synchronization, charting and drawing tools, magic/natural-language filters, and production hosting, cache and queue. Treat the features page and scan engine as a foundation, not complete parity.
