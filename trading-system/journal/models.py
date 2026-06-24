"""交易日志 — SQLite 数据层"""
import sqlite3
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL,
    direction   TEXT NOT NULL CHECK(direction IN ('buy','sell')),
    price       REAL NOT NULL,
    trade_time  TEXT NOT NULL,
    position    TEXT DEFAULT '',
    strategy    TEXT DEFAULT '',
    emotion     TEXT DEFAULT '',
    -- 自动补全
    name        TEXT DEFAULT '',
    volume      INTEGER DEFAULT 0,
    turnover_rate REAL DEFAULT 0,
    market_env  TEXT DEFAULT '',
    sector      TEXT DEFAULT '',
    sector_pct  REAL DEFAULT 0,
    -- 自动计算
    hold_days   INTEGER DEFAULT 0,
    profit_loss REAL DEFAULT 0,
    profit_pct  REAL DEFAULT 0,
    trade_date  TEXT DEFAULT '',
    -- 元数据
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""


def init_db(db_path=None):
    """初始化数据库，返回连接"""
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'trading.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_trade(conn, data: dict) -> int:
    """新增交易，返回 id"""
    fields = "code,direction,price,trade_time,position,strategy,emotion,name,volume,turnover_rate,market_env,sector,sector_pct,hold_days,profit_loss,profit_pct,trade_date"
    placeholders = ",".join(["?"] * len(fields.split(",")))
    values = [
        data.get("code"), data.get("direction"), data.get("price"),
        data.get("trade_time"), data.get("position", ""), data.get("strategy", ""),
        data.get("emotion", ""), data.get("name", ""), data.get("volume", 0),
        data.get("turnover_rate", 0), data.get("market_env", ""), data.get("sector", ""),
        data.get("sector_pct", 0), data.get("hold_days", 0),
        data.get("profit_loss", 0), data.get("profit_pct", 0), data.get("trade_date", ""),
    ]
    sql = f"INSERT INTO trades ({fields}) VALUES ({placeholders})"
    cur = conn.execute(sql, values)
    conn.commit()
    return cur.lastrowid


def get_trades(conn, limit=50, offset=0):
    """交易列表，按时间倒序"""
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY trade_time DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def get_trade_by_id(conn, tid: int):
    """单条交易"""
    row = conn.execute("SELECT * FROM trades WHERE id=?", (tid,)).fetchone()
    return dict(row) if row else None


def update_trade(conn, tid: int, data: dict):
    """更新交易（只更新传入的字段）"""
    if not data:
        return
    sets = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [tid]
    conn.execute(f"UPDATE trades SET {sets} WHERE id=?", values)
    conn.commit()


def delete_trade(conn, tid: int):
    """删除交易"""
    conn.execute("DELETE FROM trades WHERE id=?", (tid,))
    conn.commit()


def get_stats(conn, period="2026-06"):
    """月度统计"""
    rows = conn.execute(
        "SELECT * FROM trades WHERE trade_date LIKE ? AND direction='sell'",
        (period + "%",)
    ).fetchall()

    sells = [dict(r) for r in rows]
    total = len(sells)
    wins = sum(1 for s in sells if s["profit_loss"] > 0)
    losses = sum(1 for s in sells if s["profit_loss"] < 0)
    total_profit = sum(s["profit_loss"] for s in sells)
    total_pct = sum(s["profit_pct"] for s in sells)

    max_consecutive_loss = 0
    current_streak = 0
    for s in sells:
        if s["profit_loss"] < 0:
            current_streak += 1
            max_consecutive_loss = max(max_consecutive_loss, current_streak)
        else:
            current_streak = 0

    all_trades = conn.execute(
        "SELECT COUNT(*) as cnt FROM trades WHERE trade_date LIKE ?",
        (period + "%",)
    ).fetchone()

    return {
        "period": period,
        "total_trades": all_trades["cnt"],
        "completed_trades": total,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "profit_loss": round(total_profit, 2),
        "profit_pct": round(total_pct, 2),
        "avg_profit_per_trade": round(total_profit / total, 2) if total > 0 else 0,
        "max_consecutive_loss": max_consecutive_loss,
    }


def get_positions(conn):
    """当前持仓：同代码买入数 > 卖出数的部分"""
    buys = conn.execute(
        "SELECT code,COUNT(*) as cnt FROM trades WHERE direction='buy' GROUP BY code"
    ).fetchall()
    sells = conn.execute(
        "SELECT code,COUNT(*) as cnt FROM trades WHERE direction='sell' GROUP BY code"
    ).fetchall()
    sell_map = {r["code"]: r["cnt"] for r in sells}
    positions = []
    for b in buys:
        sold = sell_map.get(b["code"], 0)
        if b["cnt"] > sold:
            # 取最近一次买入价
            last = conn.execute(
                "SELECT price,name FROM trades WHERE code=? AND direction='buy' ORDER BY trade_time DESC LIMIT 1",
                (b["code"],)
            ).fetchone()
            positions.append({
                "code": b["code"],
                "name": last["name"] if last else "",
                "price": last["price"] if last else 0,
                "hold_count": b["cnt"] - sold,
            })
    return positions
