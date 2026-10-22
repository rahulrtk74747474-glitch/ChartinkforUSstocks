"""Live validation of Vertex Control < -10 AND TradingView-style RSI(3) < 5."""
import math
import pandas as pd
from backend.providers.twelve_data import get_daily_prices
from backend.scan_engine import indicator_series

# Small initial liquid-US-stock sample; expand only after API credit/plan limits are confirmed.
SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX", "INTC"]

def rsi_wilder(close: pd.Series, period: int = 3) -> pd.Series:
    """TradingView ta.rsi-style Wilder smoothing, initialized with an SMA."""
    delta = close.astype(float).diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    out = pd.Series(float("nan"), index=close.index, dtype=float)
    if len(close) <= period:
        return out
    avg_gain = gains.iloc[1:period + 1].mean()
    avg_loss = losses.iloc[1:period + 1].mean()
    def value(g, l):
        if l == 0:
            return 50.0 if g == 0 else 100.0
        return 100.0 - 100.0 / (1.0 + g / l)
    out.iloc[period] = value(avg_gain, avg_loss)
    for i in range(period + 1, len(close)):
        avg_gain = ((period - 1) * avg_gain + gains.iloc[i]) / period
        avg_loss = ((period - 1) * avg_loss + losses.iloc[i]) / period
        out.iloc[i] = value(avg_gain, avg_loss)
    return out

def main():
    print("Vertex / RSI(3) live test — daily bars; completed-bar Vertex")
    print("Criteria: Vertex Control < -10 AND RSI(3) < 5")
    print("symbol,date,close,vertex_control,rsi3,match")
    errors = []
    matches = []
    for symbol in SYMBOLS:
        try:
            frame = get_daily_prices(symbol, outputsize=100)
            frame = frame.sort_index()
            if len(frame) < 20:
                raise ValueError("Not enough daily bars")
            vertex = indicator_series(frame, "vertex_control", period=14).iloc[-1]
            rsi3 = rsi_wilder(frame["close"], 3).iloc[-1]
            close = float(frame["close"].iloc[-1])
            date = frame.index[-1].date().isoformat()
            valid = math.isfinite(float(vertex)) and math.isfinite(float(rsi3))
            match = bool(valid and vertex < -10 and rsi3 < 5)
            print(f"{symbol},{date},{close:.4f},{vertex:.6f},{rsi3:.4f},{match}")
            if match:
                matches.append(symbol)
        except Exception as exc:
            errors.append((symbol, type(exc).__name__))
            print(f"{symbol},ERROR,{type(exc).__name__}")
    print("\nMATCHES:", ", ".join(matches) if matches else "None in tested sample")
    print("ERRORS:", ", ".join(f"{s}:{e}" for s,e in errors) if errors else "None")
    print("TESTED:", len(SYMBOLS), "symbols; this is a sample, not the entire US market.")

if __name__ == "__main__":
    main()
