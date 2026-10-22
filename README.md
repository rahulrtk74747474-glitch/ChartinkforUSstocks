# Chartink for US Stocks

A Chartink-inspired technical screener for US equities, using Twelve Data market history. It is an independent implementation, not Chartink source code or a claim of full feature parity.

Full feature inventory and remaining work: [Chartink feature parity audit](docs/feature-parity.md).

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


## Deploy a live demo (Render)

A Render Blueprint is included in `render.yaml`. To create the hosted service:
1. Open the [Render Blueprint deploy page](https://render.com/deploy?repo=https://github.com/rahulrtk74747474-glitch/ChartinkforUSstocks).
2. Sign in to Render and select **Deploy** for the `chartink-us-stocks` service.
3. When prompted, enter your Twelve Data key as `TWELVE_DATA_API_KEY`. Do not put it in source code or send it in chat.
4. Wait for the service to finish deploying, then open the generated `onrender.com` URL and confirm `/api/health` reports `api_key_configured: true`.
5. In the scanner, click **Vertex + RSI(3) test**. This sets daily conditions to Vertex Control (red) < -10 AND RSI(3) < 10. Then click **Run scan**.

The hosting provider must be authorized by the repository owner; this repository change cannot create a Render account or enter a secret on the owner's behalf. Render's free service may sleep while idle, and its local SQLite file is not durable across all restarts/redeploys. Use persistent storage or a managed database before relying on saved scans in production.
