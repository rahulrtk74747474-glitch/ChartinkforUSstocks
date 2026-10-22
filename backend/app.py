"""FastAPI application for the Chartink-inspired US stock scanner."""
from __future__ import annotations
import json, os, re, sqlite3
from pathlib import Path
from typing import Any, Literal
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from backend.providers.twelve_data import get_daily_prices
from backend.scan_engine import INDICATORS, evaluate_scan, latest_metrics

ROOT=Path(__file__).resolve().parent.parent
WEB_DIR=ROOT/"web"
DB_PATH=Path(os.getenv("CHARTINK_DB_PATH",str(ROOT/"chartink_scans.sqlite3")))
app=FastAPI(title="Chartink US Scanner",version="0.2.0",description="Independent technical screening application")
app.mount("/assets",StaticFiles(directory=str(WEB_DIR)),name="assets")

class ScanRequest(BaseModel):
    symbols:list[str]=Field(min_length=1,max_length=25)
    logic:Literal["AND","OR"]="AND"
    timeframe:Literal["1min","5min","15min","30min","45min","1h","2h","4h","1day","1week","1month"]="1day"
    rules:list[dict[str,Any]]=Field(default_factory=list,max_length=30)
    groups:list[dict[str,Any]]=Field(default_factory=list,max_length=20)
    @field_validator("symbols")
    @classmethod
    def clean_symbols(cls,values):
        out=[]
        for item in values:
            s=item.strip().upper()
            if not s or len(s)>20 or not all(c.isalnum() or c in ".-" for c in s):
                raise ValueError("Invalid ticker: "+item)
            if s not in out:out.append(s)
        if not out:raise ValueError("Enter at least one ticker")
        return out
    def scan_definition(self):
        return {"logic":self.logic,"timeframe":self.timeframe,"rules":self.rules,"groups":self.groups}

class SaveScan(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    definition:dict[str,Any]

def init_db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS saved_scans(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          definition TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
init_db()

@app.get("/",include_in_schema=False)
def index():return FileResponse(WEB_DIR/"index.html")

@app.get("/api/health")
def health():
    key=os.getenv("TWELVE_DATA_API_KEY","").strip()
    return {"status":"ok","api_key_configured":bool(key and key not in {"replace_me","YOUR_API_KEY"}),"provider":"Twelve Data","database":"sqlite","features":{"technical_indicators":True,"nested_groups":True,"historical_offsets":True,"count_rules":True,"saved_scans":True,"backtest_api":True,"intraday":True,"live_alerts":False}}

@app.get("/api/indicators")
def indicators():
    return {"indicators":sorted(INDICATORS),"operators":["gt","gte","lt","lte","eq","ne","cross_above","cross_below"],"rule_fields":{"indicator":"indicator name","period":"indicator lookback period","operator":"comparison operator","value_type":"number or indicator","value":"number or indicator name","offset":"bars ago (0 is latest)","count":"optional required count of true bars","lookback":"count window length"}}

@app.post("/api/scan")
def scan(request:ScanRequest):
    definition=request.scan_definition()
    if not definition["rules"] and not definition["groups"]:
        raise HTTPException(422,"Add at least one rule or condition group")
    results=[];errors=[]
    for symbol in request.symbols:
        try:
            frame=get_daily_prices(symbol,outputsize=220,interval=request.timeframe)
            matches=evaluate_scan(frame,definition)
            if bool(matches.iloc[-1]):
                results.append({"symbol":symbol,**latest_metrics(frame)})
        except Exception as exc:
            errors.append({"symbol":symbol,"message":str(exc)[:180]})
    results.sort(key=lambda x:x.get("change_pct") if x.get("change_pct") is not None else float("-inf"),reverse=True)
    return {"scanned":len(request.symbols),"matched":len(results),"results":results,"errors":errors,"logic":request.logic}

@app.get("/api/saved-scans")
def list_saved_scans():
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory=sqlite3.Row
        rows=con.execute("SELECT id,name,definition,created_at,updated_at FROM saved_scans ORDER BY updated_at DESC").fetchall()
    return {"scans":[{"id":r["id"],"name":r["name"],"definition":json.loads(r["definition"]),"created_at":r["created_at"],"updated_at":r["updated_at"]} for r in rows]}

@app.post("/api/saved-scans")
def save_scan(body:SaveScan):
    definition=body.definition
    if not isinstance(definition.get("symbols",[]),list):raise HTTPException(422,"symbols must be a list")
    with sqlite3.connect(DB_PATH) as con:
        cur=con.execute("INSERT INTO saved_scans(name,definition) VALUES(?,?)",(body.name.strip(),json.dumps(definition)))
        scan_id=cur.lastrowid
    return {"id":scan_id,"name":body.name.strip(),"definition":definition}

@app.get("/api/saved-scans/{scan_id}")
def get_saved_scan(scan_id:int):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory=sqlite3.Row
        row=con.execute("SELECT id,name,definition,created_at,updated_at FROM saved_scans WHERE id=?",(scan_id,)).fetchone()
    if not row:raise HTTPException(404,"Saved scan not found")
    return {"id":row["id"],"name":row["name"],"definition":json.loads(row["definition"]),"created_at":row["created_at"],"updated_at":row["updated_at"]}

@app.delete("/api/saved-scans/{scan_id}")
def delete_saved_scan(scan_id:int):
    with sqlite3.connect(DB_PATH) as con:cur=con.execute("DELETE FROM saved_scans WHERE id=?",(scan_id,))
    if not cur.rowcount:raise HTTPException(404,"Saved scan not found")
    return {"deleted":True,"id":scan_id}

@app.post("/api/backtest")
def backtest(request:ScanRequest):
    """Daily historical signal history. Each bar is evaluated only against its own prefix."""
    definition=request.scan_definition()
    if not definition["rules"] and not definition["groups"]:raise HTTPException(422,"Add scan conditions")
    output=[];errors=[]
    for symbol in request.symbols:
        try:
            frame=get_daily_prices(symbol,outputsize=220,interval=request.timeframe)
            signals=evaluate_scan(frame,definition)
            bars=[]
            for idx in range(len(frame)):
                if bool(signals.iloc[idx]):
                    bars.append({"date":str(frame.index[idx].date()),"close":float(frame["close"].iloc[idx])})
            output.append({"symbol":symbol,"signals":bars,"signal_count":len(bars)})
        except Exception as exc:errors.append({"symbol":symbol,"message":str(exc)[:180]})
    return {"timeframe":request.timeframe,"results":output,"errors":errors,"note":"Historical signals use provider-returned daily bars. Intraday, split/dividend-adjusted fidelity and portfolio-grade execution simulation are not implemented."}
