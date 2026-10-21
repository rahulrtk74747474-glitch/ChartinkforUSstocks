import pandas as pd
import pytest

from backend.scan_engine import evaluate_rule, evaluate_scan, indicator_series

@pytest.fixture
def bars():
    close = [10, 11, 12, 11, 13, 14, 15, 14, 16, 18, 17, 20, 22, 21, 23, 24, 25, 24, 27, 30, 31, 29, 32, 34, 35, 36, 34, 38, 40, 42]
    idx = pd.date_range("2025-01-01", periods=len(close), freq="D")
    return pd.DataFrame({"open":[x-.5 for x in close],"high":[x+1 for x in close],"low":[x-1 for x in close],"close":close,"volume":[1000+i*10 for i in range(len(close))]},index=idx)

def test_sma_and_ema(bars):
    sma=indicator_series(bars,"sma",20)
    assert pd.isna(sma.iloc[18])
    assert sma.iloc[19] == pytest.approx(sum(bars.close.iloc[:20])/20)
    assert indicator_series(bars,"ema",10).iloc[-1] > 0

def test_rsi_range(bars):
    values=indicator_series(bars,"rsi",14).dropna()
    assert len(values)>0
    assert ((values>=0)&(values<=100)).all()

def test_numeric_rule_and_historical_offset(bars):
    rule={"indicator":"close","operator":"gt","value_type":"value","value":30}
    assert evaluate_rule(bars,rule).iloc[-1]
    assert not evaluate_rule(bars,{"indicator":"close","operator":"gt","value_type":"value","value":30,"offset":5}).iloc[-1]

def test_indicator_comparison(bars):
    result=evaluate_rule(bars,{"indicator":"close","operator":"gt","value_type":"indicator","value":"sma"})
    assert isinstance(result,pd.Series)
    assert result.index.equals(bars.index)

def test_nested_groups_are_combined(bars):
    definition={"logic":"AND","rules":[{"indicator":"close","operator":"gt","value_type":"value","value":10}],
      "groups":[{"logic":"OR","rules":[{"indicator":"close","operator":"gt","value_type":"value","value":100},{"indicator":"close","operator":"gt","value_type":"value","value":20}]}]}
    signals=evaluate_scan(bars,definition)
    assert signals.iloc[-1]
    assert not signals.iloc[0]

def test_cross_operator_returns_boolean_series(bars):
    result=evaluate_rule(bars,{"indicator":"close","operator":"cross_above","value_type":"indicator","value":"sma","period":5})
    assert result.dtype == bool
    assert result.index.equals(bars.index)

def test_count_rule_lookback(bars):
    definition={"logic":"AND","rules":[{"indicator":"close","operator":"gt","value_type":"value","value":20,"count":3,"lookback":5}]}
    result=evaluate_scan(bars,definition)
    assert result.iloc[-1]
