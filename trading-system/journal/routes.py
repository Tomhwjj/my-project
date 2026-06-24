"""交易日志 — FastAPI 路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import sqlite3
from . import models
from . import auto_fill

router = APIRouter(prefix="/api", tags=["trades"])

_db_conn: Optional[sqlite3.Connection] = None


def get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = models.init_db()
    return _db_conn


class TradeInput(BaseModel):
    code: str
    direction: str           # buy / sell
    price: float
    trade_time: str          # "2026-06-24 14:30"
    position: str = ""
    strategy: str = ""
    emotion: str = ""


@router.get("/trades")
def list_trades(limit: int = 50, offset: int = 0):
    conn = get_db()
    trades = models.get_trades(conn, limit, offset)
    return {"trades": trades, "total": len(trades)}


@router.post("/trades")
def create_trade(trade: TradeInput):
    conn = get_db()
    data = trade.model_dump()

    # 自动补全行情
    fill = auto_fill.auto_fill(trade.code)
    data.update(fill)

    # 大盘环境
    data["market_env"] = auto_fill.get_market_env()

    # 提取日期
    data["trade_date"] = trade.trade_time[:10] if trade.trade_time else ""

    # 卖出自动计算盈亏
    if trade.direction == "sell":
        match = auto_fill.match_sell(conn, trade.code, trade.price, trade.trade_time)
        data.update(match)

    tid = models.insert_trade(conn, data)
    trade_record = models.get_trade_by_id(conn, tid)
    return {"id": tid, "trade": trade_record}


@router.get("/trades/{tid}")
def get_trade(tid: int):
    conn = get_db()
    trade = models.get_trade_by_id(conn, tid)
    if not trade:
        raise HTTPException(status_code=404, detail="不存在")
    return {"trade": trade}


@router.put("/trades/{tid}")
def update_trade(tid: int, trade: TradeInput):
    conn = get_db()
    existing = models.get_trade_by_id(conn, tid)
    if not existing:
        raise HTTPException(status_code=404, detail="不存在")
    data = trade.model_dump(exclude_unset=True)
    models.update_trade(conn, tid, data)
    return {"trade": models.get_trade_by_id(conn, tid)}


@router.delete("/trades/{tid}")
def delete_trade(tid: int):
    conn = get_db()
    if not models.get_trade_by_id(conn, tid):
        raise HTTPException(status_code=404, detail="不存在")
    models.delete_trade(conn, tid)
    return {"ok": True}


@router.get("/stats")
def get_stats(period: str = Query(default="2026-06")):
    conn = get_db()
    return models.get_stats(conn, period)


@router.get("/positions")
def get_positions():
    conn = get_db()
    return {"positions": models.get_positions(conn)}
