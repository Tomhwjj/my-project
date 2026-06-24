# 交易日志系统 Phase 1 实施计划

> **For agentic workers:** 按任务顺序逐项执行，使用 checkbox (`- [ ]`) 跟踪进度。

**Goal:** 构建交易日志系统 Phase 1：对话+Web 双入口录入交易，自动补全技术面数据，SQLite 存储。

**Architecture:** FastAPI 后端 → SQLite + 东方财富 API，对话层（Claude Code Skill 解析自然语言）和 Web 层（单页看板+Chart.js）共用同一套 API。

**Tech Stack:** Python 3 + FastAPI + SQLite + uvicorn + Vanilla JS + Chart.js CDN

## Global Constraints

- 投资决策由用户自行做出
- 交易数据存储本地 SQLite，不上传
- 东方财富 API 请求间隔 ≥ 1 秒
- 复用已有 `fetcher/fetcher.py`，不重复造轮子
- 项目目录：`D:\Agent\git\trading-system\`

---

### Task 1: 项目初始化

**Files:**
- 迁移：`D:\Agent\git\stock-workflow\` → `D:\Agent\git\trading-system\`
- Create: `D:\Agent\git\trading-system\journal\__init__.py`（空文件）
- Create: `D:\Agent\git\trading-system\web\`（空目录）
- Modify: `D:\Agent\git\trading-system\fetcher\requirements.txt`

**Interfaces:**
- Produces: 项目基础目录就绪，依赖安装完毕

- [ ] **Step 1: 重命名项目目录**

```powershell
Rename-Item D:\Agent\git\stock-workflow D:\Agent\git\trading-system
```

- [ ] **Step 2: 创建新目录**

```powershell
New-Item -ItemType Directory -Force -Path "D:\Agent\git\trading-system\journal"
New-Item -ItemType File -Force -Path "D:\Agent\git\trading-system\journal\__init__.py"
New-Item -ItemType Directory -Force -Path "D:\Agent\git\trading-system\web"
```

- [ ] **Step 3: 更新依赖文件**

修改 `D:\Agent\git\trading-system\fetcher\requirements.txt`：

```txt
requests>=2.28.0
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
```

安装：

```powershell
pip install -r D:\Agent\git\trading-system\fetcher\requirements.txt -q
```

- [ ] **Step 4: Commit**

```powershell
cd D:\Agent\git
git add trading-system\journal trading-system\web trading-system\fetcher\requirements.txt
git rm -r stock-workflow
git commit -m "init: stock-workflow → trading-system，添加 journal/web 骨架"
```

---

### Task 2: models.py — SQLite 表结构

**Files:**
- Create: `D:\Agent\git\trading-system\journal\models.py`

**Interfaces:**
- Produces: `init_db(db_path)` → 返回 sqlite3.Connection，自动建表
- Produces: `insert_trade(conn, data)` → 写入一条记录，返回 id
- Produces: `get_trades(conn, limit, offset)` → 列表
- Produces: `get_trade_by_id(conn, id)` → 单条
- Produces: `update_trade(conn, id, data)` → 更新
- Produces: `delete_trade(conn, id)` → 删除
- Produces: `get_stats(conn, period)` → 统计 dict

- [ ] **Step 1: 写 models.py**

```python
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
    """初始化数据库，返回连接。db_path 默认项目根目录 trading.db"""
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

    # 最大连续亏损
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
        "details": sells,
    }


def get_positions(conn):
    """当前持仓：买入 - 卖出（同代码未配对部分）"""
    buys = conn.execute(
        "SELECT code,SUM(1) as buy_count,price FROM trades WHERE direction='buy' GROUP BY code"
    ).fetchall()
    sells = conn.execute(
        "SELECT code,SUM(1) as sell_count FROM trades WHERE direction='sell' GROUP BY code"
    ).fetchall()
    sell_map = {r["code"]: r["sell_count"] for r in sells}
    positions = []
    for b in buys:
        sold = sell_map.get(b["code"], 0)
        if b["buy_count"] > sold:
            positions.append({
                "code": b["code"],
                "price": b["price"],
                "hold_count": b["buy_count"] - sold,
            })
    return positions
```

- [ ] **Step 2: 验证建表**

```powershell
python -c "from journal.models import init_db; conn=init_db('test.db'); conn.close(); import os; os.remove('test.db'); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add trading-system\journal\models.py trading-system\journal\__init__.py
git commit -m "feat: journal/models.py — trades/config 表 + CRUD + 统计"
```

---

### Task 3: auto_fill.py — 东方财富自动补全

**Files:**
- Create: `D:\Agent\git\trading-system\journal\auto_fill.py`

**Interfaces:**
- Consumes: `fetcher/fetcher.py` 的 `_api` 函数（直接 import）
- Produces: `auto_fill(code, trade_time)` → dict {name, volume, turnover_rate, sector, sector_pct, market_env}
- Produces: `match_sell(code, buy_price)` → dict {hold_days, profit_loss, profit_pct}
- Produces: `get_market_env()` → str "牛"/"熊"/"震荡"

- [ ] **Step 1: 写 auto_fill.py**

```python
"""东方财富 API 自动补全交易字段"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fetcher'))
from fetcher import _api, HEADERS, EASTMONEY_BASE
import sqlite3
import time
from datetime import datetime, timedelta


def _guess_market(code):
    if code.startswith("6"):
        return 1
    return 0


def auto_fill(code: str, trade_time: str = None) -> dict:
    """给定股票代码，从东方财富拉实时数据补全字段。
    返回 {name, volume, turnover_rate, sector, sector_pct}
    """
    market = _guess_market(code)
    secid = f"{market}.{code}"
    fields = "f43,f47,f48,f50,f57,f58,f116,f162,f167"
    params = {"secid": secid, "fields": fields}
    data = _api("stock/get", params)

    result = {"name": "", "volume": 0, "turnover_rate": 0, "sector": "", "sector_pct": 0}
    if data:
        result["name"] = data.get("f58", "")
        result["volume"] = data.get("f47", 0) or 0
        result["turnover_rate"] = data.get("f167", 0)

    # 查所属板块（从 sectors 数据中模糊匹配）
    try:
        sectors_data = _api("clist/get", {
            "fid": "f3", "po": "1", "pz": "200", "pn": "1",
            "np": "1", "fltt": "2", "invt": "2", "fs": "m:90",
            "fields": "f2,f3,f12,f14"
        })
        time.sleep(0.5)
        if sectors_data:
            raw = sectors_data.get("diff", {})
            items = list(raw.values()) if isinstance(raw, dict) else raw
            for s in items:
                # 简单匹配：取第一个涨幅最大且有名字的板块
                if result["sector"] == "" and s.get("f14"):
                    result["sector"] = s.get("f14", "")
                    result["sector_pct"] = s.get("f3", 0)
    except:
        pass

    return result


def match_sell(conn: sqlite3.Connection, code: str, sell_price: float, sell_time: str) -> dict:
    """卖出时匹配最近一次同代码买入，计算持仓天数和盈亏。
    返回 {hold_days, profit_loss, profit_pct}
    """
    row = conn.execute(
        "SELECT * FROM trades WHERE code=? AND direction='buy' ORDER BY trade_time DESC LIMIT 1",
        (code,)
    ).fetchone()

    if not row:
        return {"hold_days": 0, "profit_loss": 0, "profit_pct": 0}

    buy = dict(row)
    buy_price = buy["price"]
    buy_time = buy["trade_time"]

    profit_loss = round((sell_price - buy_price) * 100, 2)  # 每股盈亏 × 100股
    profit_pct = round((sell_price - buy_price) / buy_price * 100, 2)

    try:
        bt = datetime.strptime(buy_time[:10], "%Y-%m-%d")
        st = datetime.strptime(sell_time[:10], "%Y-%m-%d") if sell_time else datetime.now()
        hold_days = (st - bt).days
    except:
        hold_days = 0

    return {"hold_days": hold_days, "profit_loss": profit_loss, "profit_pct": profit_pct}


def get_market_env() -> str:
    """近30日沪深300涨跌判断市场环境"""
    try:
        params = {
            "secid": "1.000300",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101", "fqt": "1", "lmt": "30",
        }
        data = _api("stock/kline/get", params)
        if data and data.get("klines"):
            closes = [float(k.split(",")[2]) for k in data["klines"] if len(k.split(",")) >= 3]
            if len(closes) >= 20:
                pct_30d = (closes[-1] - closes[0]) / closes[0] * 100
                if pct_30d > 5:
                    return "牛市"
                elif pct_30d < -5:
                    return "熊市"
                return "震荡"
    except:
        pass
    return "震荡"
```

- [ ] **Step 2: 验证 auto_fill**

```powershell
python -c "
import sys; sys.path.insert(0, r'D:\Agent\git\trading-system\fetcher')
from journal.auto_fill import auto_fill, get_market_env
r = auto_fill('600900')
assert r['name'] != '', f'name empty, got {r}'
print(f'name={r[\"name\"]} volume={r[\"volume\"]} sector={r[\"sector\"]}')
env = get_market_env()
print(f'market_env={env}')
print('OK')
"
```
Expected: `name=长江电力 volume=... sector=... market_env=震荡 OK`

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add trading-system\journal\auto_fill.py
git commit -m "feat: journal/auto_fill.py — 东方财富自动补全+大盘环境判定"
```

---

### Task 4: routes.py — FastAPI 接口

**Files:**
- Create: `D:\Agent\git\trading-system\journal\routes.py`

**Interfaces:**
- Consumes: `models.*`, `auto_fill.*`
- Produces: FastAPI APIRouter，包含全部 REST 接口

- [ ] **Step 1: 写 routes.py**

```python
"""交易日志 — FastAPI 路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import sqlite3
from . import models
from . import auto_fill

router = APIRouter(prefix="/api", tags=["trades"])

# 全局 DB 连接（main.py 启动时初始化）
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
    position: str = ""       # 轻/半/满/试错
    strategy: str = ""       # ABC浪/量能突破/板块跟风/情绪化
    emotion: str = ""        # 冲动/止损/止盈/补仓/割肉/追高/正常


@router.get("/trades")
def list_trades(limit: int = 50, offset: int = 0):
    conn = get_db()
    trades = models.get_trades(conn, limit, offset)
    return {"trades": trades, "total": len(trades)}


@router.post("/trades")
def create_trade(trade: TradeInput):
    conn = get_db()
    data = trade.model_dump()

    # 自动补全行情数据
    fill = auto_fill.auto_fill(trade.code, trade.trade_time)
    data.update(fill)

    # 自动补全大盘环境
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
```

- [ ] **Step 2: 验证路由可导入**

```powershell
python -c "from journal.routes import router; print('routes OK, endpoints:', [r.path for r in router.routes])"
```
Expected: 列出所有 API 路径

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add trading-system\journal\routes.py
git commit -m "feat: journal/routes.py — FastAPI CRUD + stats/positions"
```

---

### Task 5: main.py — 启动入口

**Files:**
- Create: `D:\Agent\git\trading-system\main.py`

**Interfaces:**
- Produces: `python main.py` → 启动 API 服务 http://localhost:8765，同时托管 Web 静态文件

- [ ] **Step 1: 写 main.py**

```python
"""交易系统 — 启动入口"""
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from journal.routes import router
from journal.models import init_db
import os

app = FastAPI(title="Trading System", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

# Web 静态文件
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

@app.on_event("startup")
def startup():
    init_db()
    print("✅ Trading System started — http://localhost:8765")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
```

- [ ] **Step 2: 启动验证**

```powershell
Start-Process python -ArgumentList "D:\Agent\git\trading-system\main.py" -WindowStyle Hidden
Start-Sleep 3
Invoke-RestMethod http://localhost:8765/api/trades
```
Expected: `{"trades": [], "total": 0}`

- [ ] **Step 3: 测试创建交易**

```powershell
$body = @{code="600900";direction="buy";price=26.5;trade_time="2026-06-24 14:30";position="半仓";strategy="波段";emotion="正常"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8765/api/trades -Method Post -Body $body -ContentType "application/json"
```
Expected: 返回 `{"id": 1, "trade": {...}}` 含自动补全字段

- [ ] **Step 4: Commit**

```powershell
cd D:\Agent\git
git add trading-system\main.py
git commit -m "feat: main.py — FastAPI 启动入口 + Web 静态托管"
```

---

### Task 6: Web 看板

**Files:**
- Create: `D:\Agent\git\trading-system\web\index.html`
- Create: `D:\Agent\git\trading-system\web\app.js`

**Interfaces:**
- Consumes: `GET /api/trades`, `POST /api/trades`, `GET /api/stats`
- Produces: 单页 Web 看板（交易列表 + 录入表单 + 统计图表）

- [ ] **Step 1: 写 index.html**

```html
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>交易日志</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
  .container { max-width: 1200px; margin: 0 auto; }
  h1 { margin-bottom: 20px; color: #38bdf8; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .card { background: #1e293b; border-radius: 8px; padding: 20px; }
  .card h2 { margin-bottom: 12px; font-size: 16px; color: #94a3b8; }
  form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  form input, form select, form button { padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 14px; }
  form button { grid-column: span 2; background: #38bdf8; color: #0f172a; font-weight: bold; cursor: pointer; border: none; }
  form button:hover { background: #7dd3fc; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 8px 6px; text-align: left; border-bottom: 1px solid #334155; }
  th { color: #94a3b8; font-weight: 500; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
  .tag-buy { background: #065f46; color: #6ee7b7; }
  .tag-sell { background: #7f1d1d; color: #fca5a5; }
  .tag-win { color: #f87171; }
  .tag-loss { color: #4ade80; }
  .stats-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 20px; }
  .stat { background: #1e293b; padding: 16px; border-radius: 8px; text-align: center; }
  .stat .num { font-size: 28px; font-weight: bold; color: #38bdf8; }
  .stat .lbl { font-size: 12px; color: #94a3b8; margin-top: 4px; }
  #chartContainer { height: 300px; margin-top: 20px; }
</style>
</head>
<body>
<div class="container">
  <h1>📊 交易日志</h1>
  <div class="stats-row" id="statsRow"></div>
  <div class="grid">
    <div class="card">
      <h2>✏️ 录入交易</h2>
      <form id="tradeForm">
        <input name="code" placeholder="代码 600900" required>
        <select name="direction" required><option value="buy">买入</option><option value="sell">卖出</option></select>
        <input name="price" type="number" step="0.01" placeholder="价格 26.50" required>
        <input name="trade_time" type="text" placeholder="时间 2026-06-24 14:30" required>
        <select name="position"><option value="">仓位</option><option>轻仓</option><option>半仓</option><option>满仓</option><option>试错</option></select>
        <select name="strategy"><option value="">策略</option><option>ABC浪</option><option>量能突破</option><option>板块跟风</option><option>情绪化</option></select>
        <select name="emotion"><option value="">情绪</option><option>正常</option><option>冲动</option><option>止损</option><option>止盈</option><option>补仓</option><option>割肉</option><option>追高</option></select>
        <button type="submit">提交</button>
      </form>
    </div>
    <div class="card">
      <h2>📋 最近交易</h2>
      <table><thead><tr><th>时间</th><th>代码</th><th>名称</th><th>方向</th><th>价格</th><th>盈亏</th><th>策略</th></tr></thead><tbody id="tradeList"></tbody></table>
    </div>
  </div>
  <div class="card" style="margin-top:20px">
    <h2>📈 盈亏曲线</h2>
    <canvas id="pnlChart"></canvas>
  </div>
</div>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 写 app.js**

```javascript
const API = '/api';

async function loadStats() {
  const r = await fetch(API + '/stats?period=2026-06');
  const d = await r.json();
  document.getElementById('statsRow').innerHTML = `
    <div class="stat"><div class="num">${d.win_rate}%</div><div class="lbl">胜率</div></div>
    <div class="stat"><div class="num">${d.completed_trades}</div><div class="lbl">已完结</div></div>
    <div class="stat"><div class="num">${d.profit_loss.toFixed(0)}</div><div class="lbl">总盈亏</div></div>
    <div class="stat"><div class="num">${d.max_consecutive_loss}</div><div class="lbl">最大连亏</div></div>
  `;
  return d;
}

async function loadTrades() {
  const r = await fetch(API + '/trades?limit=30');
  const d = await r.json();
  const tbody = document.getElementById('tradeList');
  tbody.innerHTML = d.trades.map(t => `
    <tr>
      <td>${t.trade_time}</td>
      <td>${t.code}</td>
      <td>${t.name}</td>
      <td><span class="tag tag-${t.direction}">${t.direction==='buy'?'买':'卖'}</span></td>
      <td>${t.price}</td>
      <td class="${t.profit_loss > 0 ? 'tag-win' : t.profit_loss < 0 ? 'tag-loss' : ''}">${t.direction==='sell' ? t.profit_pct.toFixed(2)+'%' : '-'}</td>
      <td>${t.strategy}</td>
    </tr>
  `).join('');

  // 盈亏曲线
  const sells = d.trades.filter(t => t.direction === 'sell').reverse();
  let cum = 0;
  const labels = sells.map(t => t.trade_time?.slice(5,10) || '');
  const data = sells.map(t => { cum += t.profit_loss; return cum; });

  if (window._pnlChart) window._pnlChart.destroy();
  const ctx = document.getElementById('pnlChart').getContext('2d');
  window._pnlChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: '累计盈亏', data, borderColor: '#38bdf8', tension: 0.3 }] },
    options: { responsive: true, plugins: { legend: { labels: { color: '#94a3b8' } } }, scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } } }
  });
}

document.getElementById('tradeForm').onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  body.price = parseFloat(body.price);
  const r = await fetch(API + '/trades', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  if (r.ok) { e.target.reset(); loadTrades(); loadStats(); }
  else { alert('录入失败'); }
};

loadStats();
loadTrades();
```

- [ ] **Step 3: 验证 Web 页面**

```powershell
Invoke-RestMethod http://localhost:8765/ | Select-String "交易日志"
```
Expected: 包含 "交易日志"

- [ ] **Step 4: Commit**

```powershell
cd D:\Agent\git
git add trading-system\web\index.html trading-system\web\app.js
git commit -m "feat: web/ — 交易日志单页看板（列表+表单+Chart.js盈亏曲线）"
```

---

### Task 7: skill/TRADING.md — 合并 Skill

**Files:**
- Create: `D:\Agent\git\trading-system\skill\TRADING.md`（基于 STOCK.md 扩展）

**Interfaces:**
- Consumes: 已有 fetcher 命令 + 新增 `/api/trades` 接口
- Produces: Claude Code Skill，选股+交易统一入口

- [ ] **Step 1: 写 TRADING.md**

在原有 STOCK.md 基础上，在"触发条件"段增加交易日志部分：

```markdown
## 交易日志触发（新增）

- **"记一笔 <方向> <代码> <价格> <时间> <仓位> <策略>"** → 调 POST /api/trades 录入
- **"记一笔 <方向> <代码> <价格> <时间> <仓位> <策略> <情绪>"** → 同上，含情绪标注
- **"记一笔 买入 600900 26.5 14:30 半仓 波段"** → 示例：默认今天日期
- **"交易记录" "最近交易"** → 调 GET /api/trades 展示列表
- **"本月统计" "胜率"** → 调 GET /api/stats 展示统计
- **"当前持仓"** → 调 GET /api/positions 展示持仓

录入确认格式：
```
✅ 已记录：[名称] [代码] [方向] [价格] [时间] [仓位]
   板块：[sector]  大盘：[market_env]  换手率：[turnover_rate]%
```
```

- [ ] **Step 2: 同步 Skill 到三个位置 + 删除旧 STOCK.md**

```powershell
Copy-Item "D:\Agent\git\trading-system\skill\TRADING.md" "D:\Agent\git\.claude\skills\trading-system\SKILL.md" -Force
Copy-Item "D:\Agent\git\trading-system\skill\TRADING.md" "$env:USERPROFILE\.agents\skills\trading-system\SKILL.md" -Force
Copy-Item "D:\Agent\git\trading-system\skill\TRADING.md" "$env:USERPROFILE\.claude\skills\trading-system\SKILL.md" -Force
# 清理旧名
Remove-Item "$env:USERPROFILE\.agents\skills\stock-workflow" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.claude\skills\stock-workflow" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "D:\Agent\git\.claude\skills\stock-workflow" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "D:\Agent\git\trading-system\skill\STOCK.md" -Force
```

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add trading-system\skill\TRADING.md
git rm trading-system\skill\STOCK.md
git commit -m "feat: skill/TRADING.md — 选股+交易日志合并，stock-workflow→trading-system"
```

---

### Task 8: README 更新 + 端到端测试

**Files:**
- Modify: `D:\Agent\git\trading-system\README.md`

- [ ] **Step 1: 更新 README.md**

```markdown
# 交易系统

个人 A 股交易辅助平台。选股（板块扫描+日报）+ 交易日志（录入+统计），共用东方财富数据管道。

## 快速开始

```bash
pip install -r fetcher/requirements.txt
python main.py
# 打开 http://localhost:8765
```

## 模块

- **fetcher/** — 东方财富数据管道（sectors/stocks/detail）
- **journal/** — 交易日志（录入/自动补全/统计）
- **web/** — Web 看板
- **skill/** — Claude Code Skill（选股+交易）

## 对话入口

- "日报" — 收盘速报
- "看板块" — 板块排行
- "记一笔 买入 600900 26.5 14:30 半仓 波段" — 录入交易
- "本月统计" — 交易统计

## 免责声明

⚠️ 不构成投资建议。投资决策由用户自行做出。
```

- [ ] **Step 2: 端到端测试**

```powershell
# 测试完整链路：API 录入 → 查询 → 统计
$body = @{code="600900";direction="buy";price=26.5;trade_time="2026-06-24 14:30";position="半仓";strategy="波段";emotion="正常"} | ConvertTo-Json
$r1 = Invoke-RestMethod -Uri http://localhost:8765/api/trades -Method Post -Body $body -ContentType "application/json"
Write-Output "Create: id=$($r1.id) name=$($r1.trade.name)"

$r2 = Invoke-RestMethod http://localhost:8765/api/trades
Write-Output "List: $($r2.total) trades"

$r3 = Invoke-RestMethod http://localhost:8765/api/stats
Write-Output "Stats: win_rate=$($r3.win_rate)%"

Write-Output "E2E PASS"
```
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add trading-system\README.md trading-system\trading.db
git commit -m "docs: README更新 + 端到端测试通过"
```

---

### Task 9: 清理 + 更新 CLAUDE.md

- [ ] **Step 1: 清理旧 skill 引用**

更新 `C:\Users\何伟\.claude\CLAUDE.md`，将 `stock-workflow` 替换为 `trading-system`：

```markdown
- **trading-system** — 选股工作流+交易日志（项目级 skill，`D:\Agent\git\.claude\skills\`），日报/板块扫描/交易录入/统计
```

- [ ] **Step 2: 最终验证**

Claude Code 对话中输入：

```
记一笔 买入 600900 26.5 14:30 半仓 波段
```

预期：自动调 API 录入，返回确认信息。

- [ ] **Step 3: Commit CLAUDE.md**

```powershell
cd D:\Agent\git
git add ..\..\Users\何伟\.claude\CLAUDE.md
git commit -m "docs: CLAUDE.md — stock-workflow→trading-system"
```
