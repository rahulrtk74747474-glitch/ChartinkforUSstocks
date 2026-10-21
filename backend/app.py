"""Chartink-inspired US equity scanner API and web application."""
from __future__ import annotations
import math, os
from pathlib import Path
from typing import Any, Literal
import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from backend.providers.twelve_data import get_daily_prices

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
app = FastAPI(title="Chartink US Scanner", version="0.1.0")
app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")
ALLOWED = {"close", "open", "high", "low", "volume", "sma20", "sma50", "sma200", "rsi14", "change_pct"}

class Rule(BaseModel):
    indicator: str
    operator: Literal["gt", "gte", "lt", "lte", "eq", "cross_above", "cross_below"]
    value_type: Literal["value", "indicator"] = "value"
    value: float | str
    @field_validator("indicator")
    @classmethod
    def valid_indicator(cls, value):
        if value not in ALLOWED: raise ValueError("Unsupported indicator")
        return value
    @field_validator("value")
    @classmethod
    def valid_value(cls, value):
        if isinstance(value, str) and value not in ALLOWED: raise ValueError("Unsupported comparison indicator")
        if isinstance(value, (float, int)) and not math.isfinite(value): raise ValueError("Value must be finite")
        return value

class ScanRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=25)
    logic: Literal["AND", "OR"] = "AND"
    rules: list[Rule] = Field(min_length=1, max_length=12)
    @field_validator("symbols")
    @classmethod
    def clean_symbols(cls, values):
        out = []
        for item in values:
            symbol = item.strip().upper()
            if not symbol or len(symbol) > 20 or not all(c.isalnum() or c in ".-" for c in symbol):
                raise ValueError("Invalid ticker: " + item)
            if symbol not in out: out.append(symbol)
        if not out: raise ValueError("Enter at least one valid ticker")
        return out

def number(v):
    try:
        x = float(v)
        return round(x, 6) if math.isfinite(x) else None
    except (TypeError, ValueError): return None

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100/(1+rs)
    out = out.where(loss != 0, 100)
    return out.where(~((gain == 0) & (loss == 0)), 50)

def metrics(frame):
    close = frame["close"]
    out = {c: number(frame[c].iloc[-1]) if c in frame else None for c in ("open","high","low","close","volume")}
    out["change_pct"] = number((close.iloc[-1]/close.iloc[-2]-1)*100) if len(close)>1 and close.iloc[-2] else None
    for p in (20,50,200): out["sma"+str(p)] = number(close.rolling(p).mean().iloc[-1]) if len(close)>=p else None
    out["rsi14"] = number(rsi(close).iloc[-1]) if len(close)>=15 else None
    return out

def compare(cur, op, target, prev=None, prevtarget=None):
    if cur is None or target is None: return False
    if op=="gt": return cur>target
    if op=="gte": return cur>=target
    if op=="lt": return cur<target
    if op=="lte": return cur<=target
    if op=="eq": return math.isclose(cur,target,rel_tol=1e-8,abs_tol=1e-8)
    if prev is None or prevtarget is None: return False
    if op=="cross_above": return prev<=prevtarget and cur>target
    if op=="cross_below": return prev>=prevtarget and cur<target
    return False

def evaluate(frame, rules, logic):
    current = metrics(frame)
    previous = metrics(frame.iloc[:-1]) if len(frame)>=3 else {}
    checks=[]
    for rule in rules:
        target = current.get(rule.value) if rule.value_type=="indicator" else (current.get(rule.value) if isinstance(rule.value,str) else rule.value)
        pt = previous.get(rule.value) if rule.value_type=="indicator" and isinstance(rule.value,str) else target
        checks.append(compare(current.get(rule.indicator),rule.operator,target,previous.get(rule.indicator),pt))
    return (all(checks) if logic=="AND" else any(checks)), current

@app.get("/", include_in_schema=False)
def index(): return FileResponse(WEB_DIR / "index.html")

@app.get("/api/health")
def health():
    key=os.getenv("TWELVE_DATA_API_KEY","").strip()
    return {"status":"ok","api_key_configured":bool(key and key not in {"replace_me","YOUR_API_KEY"}),"provider":"Twelve Data"}

@app.get("/api/indicators")
def indicators(): return {"indicators":sorted(ALLOWED)}

@app.post("/api/scan")
def scan(request: ScanRequest):
    results, errors = [], []
    for symbol in request.symbols:
        try:
            frame=get_daily_prices(symbol,outputsize=220)
            matched, values=evaluate(frame,request.rules,request.logic)
            if matched: results.append({"symbol":symbol,**values})
        except Exception as exc:
            errors.append({"symbol":symbol,"message":str(exc)[:180]})
    results.sort(key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -math.inf,reverse=True)
    return {"scanned":len(request.symbols),"matched":len(results),"results":results,"errors":errors,"logic":request.logic}
