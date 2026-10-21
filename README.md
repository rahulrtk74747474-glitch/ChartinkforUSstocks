# Chartink for US Stocks — Twelve Data Starter

This repository is currently a starter integration for Twelve Data. The original repository was empty when inspected, so this commit creates a safe, standalone data-provider foundation; it does not replace or claim to implement an existing scanner/dashboard.

## 1. Requirements
- Python 3.10+
- A Twelve Data API key and account with access to the requested symbol/endpoint
- Git

## 2. Local setup (Windows PowerShell)
```powershell
git clone https://github.com/rahulrtk74747474-glitch/ChartinkforUSstocks.git
cd ChartinkforUSstocks
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
Edit `.env` locally and set `TWELVE_DATA_API_KEY=your_real_key`. Never commit `.env`.

## 3. Verify the connection
```powershell
python test_twelve_data.py
```
The test requests five daily bars for AAPL. This consumes API credits. A successful result prints dates and OHLCV data.

## 4. Use as a Python module
```python
from backend.providers.twelve_data import get_daily_prices

df = get_daily_prices("AAPL", outputsize=100)
print(df.tail())
```
Returned rows are normalized to ascending time order with lowercase OHLCV column names where available.

## 5. GitHub Actions secret (when adding a workflow)
Repository → Settings → Secrets and variables → Actions → New repository secret.
Name: `TWELVE_DATA_API_KEY`; value: your API key. Workflows can expose it to Python as:
```yaml
env:
  TWELVE_DATA_API_KEY: ${{ secrets.TWELVE_DATA_API_KEY }}
```
Do not put a key in workflow YAML, source code, logs, or commits.

## Limits and data rights
API credits, supported exchanges, intraday/real-time access, and symbol availability depend on your Twelve Data plan. Free access is not a promise of unlimited requests or permission to redistribute data publicly. Confirm your plan's terms before exposing price data on a public website.

## Next integration steps
1. Add the existing scanner source code and workflow(s) to this repository (or identify the correct active repository/branch).
2. Add a market-specific symbol registry (ticker + exchange).
3. Add caching and request-budget controls before scanning a large universe.
4. Add formula implementations with tests and compare against known sample results.
5. Add deployment only after the application and data-licensing requirements are clear.
