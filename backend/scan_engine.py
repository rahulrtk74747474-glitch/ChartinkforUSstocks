"""Reusable technical-indicator and rule evaluation engine.

Indicators are computed locally from provider OHLCV bars. Rules can target a
historical offset, compare indicators, and count true values over a lookback.
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd

INDICATORS = {
    "open", "high", "low", "close", "volume", "change_pct",
    "sma", "ema", "wma", "rsi", "macd", "macd_signal", "macd_hist",
    "bb_upper", "bb_middle", "bb_lower", "atr", "stoch_k", "stoch_d",
    "obv", "vwap", "roc", "cci", "adx", "plus_di", "minus_di", "vertex_control",
}

OPERATORS = {"gt", "gte", "lt", "lte", "eq", "ne", "cross_above", "cross_below"}

def _period(rule: dict, default=14) -> int:
    p = int(rule.get("period", default))
    if p < 1 or p > 500: raise ValueError("Indicator period must be 1–500")
    return p

def _vertex_control(frame: pd.DataFrame, length: int) -> pd.Series:
    """Vertex red Control line using prior completed bars (matchExport=true)."""
    close = frame["close"].astype(float).to_numpy()
    high = frame["high"].astype(float).to_numpy() if "high" in frame else close
    low = frame["low"].astype(float).to_numpy() if "low" in frame else close
    result = np.full(len(frame), np.nan, dtype=float)
    for i in range(len(frame)):
        running_high, running_low = -np.inf, np.inf
        up_sum = down_sum = 0.0
        bars_used = 0
        for j in range(i - 1, max(-1, i - length - 1), -1):
            if not np.isfinite(close[j]):
                continue
            bars_used += 1
            if high[j] > running_high:
                running_high = high[j]
                up_sum += close[j]
            if low[j] < running_low:
                running_low = low[j]
                down_sum += close[j]
        if bars_used == 0:
            result[i] = 0.0
        elif up_sum != 0.0 and down_sum != 0.0:
            result[i] = down_sum / up_sum - up_sum / down_sum
    return pd.Series(result, index=frame.index, name="vertex_control")

def indicator_series(frame: pd.DataFrame, name: str, period: int = 14,
                     fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    n = name.lower()
    close = frame["close"].astype(float)
    high = frame["high"].astype(float) if "high" in frame else close
    low = frame["low"].astype(float) if "low" in frame else close
    volume = frame["volume"].astype(float).fillna(0) if "volume" in frame else close * 0
    if n in frame.columns: return frame[n].astype(float)
    if n == "vertex": n = "vertex_control"
    if n == "vertex_control": return _vertex_control(frame, period)
    if n == "open" or n == "high" or n == "low" or n == "close" or n == "volume":
        return frame[n].astype(float)
    if n == "change_pct": return close.pct_change() * 100
    if n == "sma": return close.rolling(period, min_periods=period).mean()
    if n == "ema": return close.ewm(span=period, adjust=False, min_periods=period).mean()
    if n == "wma":
        weights = np.arange(1, period + 1, dtype=float)
        return close.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    if n == "rsi":
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        loss = -delta.clip(upper=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        out = 100 - 100/(1+rs)
        return out.where(loss != 0, 100).where(~((gain == 0) & (loss == 0)), 50)
    if n in {"macd", "macd_signal", "macd_hist"}:
        line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        sig = line.ewm(span=signal, adjust=False).mean()
        return {"macd": line, "macd_signal": sig, "macd_hist": line-sig}[n]
    if n in {"bb_upper", "bb_middle", "bb_lower"}:
        mid = close.rolling(period).mean()
        std = close.rolling(period).std(ddof=0)
        return {"bb_upper":mid+2*std,"bb_middle":mid,"bb_lower":mid-2*std}[n]
    prev_close = close.shift(1)
    tr = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    if n == "atr": return tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    if n in {"stoch_k", "stoch_d"}:
        k = 100*(close-low.rolling(period).min())/(high.rolling(period).max()-low.rolling(period).min()).replace(0,np.nan)
        return k if n == "stoch_k" else k.rolling(3).mean()
    if n == "obv": return (np.sign(close.diff()).fillna(0)*volume).cumsum()
    if n == "vwap":
        typical = (high+low+close)/3
        return (typical*volume).rolling(period).sum()/volume.rolling(period).sum().replace(0,np.nan)
    if n == "roc": return (close/close.shift(period)-1)*100
    if n == "cci":
        typical=(high+low+close)/3; avg=typical.rolling(period).mean()
        dev=typical.rolling(period).apply(lambda x: np.mean(np.abs(x-np.mean(x))),raw=True)
        return (typical-avg)/(0.015*dev.replace(0,np.nan))
    if n in {"adx","plus_di","minus_di"}:
        up=high.diff(); down=-low.diff()
        plus=up.where((up>down)&(up>0),0.0); minus=down.where((down>up)&(down>0),0.0)
        atr=tr.ewm(alpha=1/period,min_periods=period,adjust=False).mean().replace(0,np.nan)
        pdi=100*plus.ewm(alpha=1/period,min_periods=period,adjust=False).mean()/atr
        mdi=100*minus.ewm(alpha=1/period,min_periods=period,adjust=False).mean()/atr
        dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
        return {"adx":dx.ewm(alpha=1/period,min_periods=period,adjust=False).mean(),"plus_di":pdi,"minus_di":mdi}[n]
    raise ValueError(f"Unsupported indicator: {name}")

def _safe_float(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def evaluate_rule(frame: pd.DataFrame, rule: dict) -> pd.Series:
    left_name=rule.get("indicator","close")
    left=indicator_series(frame,left_name,_period(rule))
    offset=int(rule.get("offset",0))
    if offset < 0 or offset > 500: raise ValueError("Offset must be 0–500 bars ago")
    if offset: left=left.shift(offset)
    if rule.get("value_type","number")=="indicator":
        right=indicator_series(frame,str(rule.get("value","close")),_period(rule,14))
        ro=int(rule.get("right_offset",offset))
        if ro<0 or ro>500: raise ValueError("Right offset must be 0–500")
        if ro: right=right.shift(ro)
    else:
        value=_safe_float(rule.get("value",0))
        if value is None: raise ValueError("Rule numeric value is invalid")
        right=pd.Series(value,index=frame.index)
    op=rule.get("operator","gt")
    if op not in OPERATORS: raise ValueError(f"Unsupported operator: {op}")
    if op=="gt": result=left>right
    elif op=="gte": result=left>=right
    elif op=="lt": result=left<right
    elif op=="lte": result=left<=right
    elif op=="eq": result=np.isclose(left,right,rtol=1e-8,atol=1e-8,equal_nan=False)
    elif op=="ne": result=left!=right
    elif op=="cross_above": result=(left.shift(1)<=right.shift(1))&(left>right)
    else: result=(left.shift(1)>=right.shift(1))&(left<right)
    return pd.Series(result,index=frame.index).fillna(False).astype(bool)

def evaluate_scan(frame: pd.DataFrame, scan: dict) -> pd.Series:
    """Evaluate all/any rules, nested groups, and count rules on every bar."""
    def group(node):
        terms=[]
        for rule in node.get('rules',[]):
            if 'count' in rule:
                base=evaluate_rule(frame,rule)
                lookback=int(rule.get('lookback',10))
                if not 1<=lookback<=500: raise ValueError('Count lookback must be 1–500')
                count=int(rule['count'])
                if count<0 or count>lookback: raise ValueError('Count must be between zero and lookback')
                term=base.astype(int).rolling(lookback,min_periods=lookback).sum() >= count
            else: term=evaluate_rule(frame,rule)
            terms.append(term)
        terms.extend(group(child) for child in node.get('groups',[]))
        if not terms: return pd.Series(False,index=frame.index)
        logic=node.get('logic',scan.get('logic','AND'))
        if logic not in {'AND','OR'}: raise ValueError('Group logic must be AND or OR')
        return pd.concat(terms,axis=1).all(axis=1) if logic=='AND' else pd.concat(terms,axis=1).any(axis=1)
    return group(scan)

def latest_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    result={}
    for name in ("open","high","low","close","volume","change_pct"):
        try: result[name]=_safe_float(indicator_series(frame,name).iloc[-1])
        except Exception: result[name]=None
    for name,p in (("sma",20),("sma",50),("sma",200),("ema",20),("ema",50),("ema",200),("rsi",14),("macd",12),("macd_signal",12),("macd_hist",12),("bb_upper",20),("bb_middle",20),("bb_lower",20),("atr",14),("adx",14),("vertex_control",14),("rsi",3)):
        key=f"{name}{p}"
        try: result[key]=_safe_float(indicator_series(frame,name,p).iloc[-1])
        except Exception: result[key]=None
    return result
