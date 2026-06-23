# 选股工作流 实施计划

> **For agentic workers:** 按任务顺序逐项执行，每步完成后确认通过再继续。使用 checkbox (`- [ ]`) 语法跟踪进度。

**Goal:** 构建三层选股工作流：Python 数据层（取东方财富API）→ Skill 层（编排分析）→ 用户通过 Claude Code 交互使用。

**Architecture:** 3 个文件：`fetcher/fetcher.py`（三个子命令取数→JSON）、`fetcher/requirements.txt`（requests）、`skill/STOCK.md`（Claude Code Skill，编排日报+钻取流程）。

**Tech Stack:** Python 3 + requests + 东方财富 push2 API（免费公开接口）

## Global Constraints

- Python 依赖仅 `requests` 一个外部包
- API 请求间隔 ≥ 1 秒，避免限流
- 所有数据输出 JSON 到 stdout，错误输出到 stderr
- 投资决策由用户自行做出，工具仅提供数据
- 项目目录：`D:\Agent\git\stock-workflow\`

---

### Task 1: 创建项目骨架 + fetcher.py sectors 命令

**Files:**
- Create: `D:\Agent\git\stock-workflow\fetcher\fetcher.py`
- Create: `D:\Agent\git\stock-workflow\fetcher\requirements.txt`

**Interfaces:**
- Produces: `python fetcher/fetcher.py sectors` → JSON stdout 打印全部行业板块排行（涨幅+资金流），exit code 0

- [ ] **Step 1: 创建目录结构**

```powershell
New-Item -ItemType Directory -Force -Path "D:\Agent\git\stock-workflow\fetcher"
New-Item -ItemType Directory -Force -Path "D:\Agent\git\stock-workflow\skill"
```

- [ ] **Step 2: 写 requirements.txt**

```txt
requests>=2.28.0
```

- [ ] **Step 3: 安装依赖**

```powershell
pip install -r D:\Agent\git\stock-workflow\fetcher\requirements.txt
```

- [ ] **Step 4: 写 fetcher.py — 骨架 + sectors 命令**

```python
"""选股工作流 — 东方财富公开数据接口

用法:
    python fetcher.py sectors           行业板块排行（涨幅+资金流）
    python fetcher.py stocks BK0428     板块成分股
    python fetcher.py detail 600900     个股深度数据
"""

import sys
import json
import time
import requests

EASTMONEY_BASE = "https://push2.eastmoney.com/api/qt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# ── 工具函数 ──────────────────────────────────────────

def _api(path, params, timeout=15):
    """统一API调用，自动重试一次，返回 parsed JSON data"""
    url = f"{EASTMONEY_BASE}/{path}"
    for attempt in range(2):
        try:
            if attempt > 0:
                time.sleep(2)
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("data") is not None:
                return data["data"]
            if attempt == 0:
                time.sleep(1)
                continue
            return None
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            print(f"API 调用失败: {e}", file=sys.stderr)
            return None

# ── sectors ────────────────────────────────────────────

def cmd_sectors():
    """拉取全部行业板块排行（东方财富行业板块 m:90+t3）。

    返回字段：
        f2  - 最新价（板块指数）
        f3  - 涨跌幅(%)
        f4  - 涨跌额
        f12 - 板块代码（如 BK0428）
        f14 - 板块名称（如 电力）
        f62 - 主力净流入(元)
        f6  - 成交额(元)
        f20 - 总市值
    """
    params = {
        "fid": "f3",       # 按涨跌幅排序
        "po": "1",
        "pz": "200",       # 全量行业板块
        "pn": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": "m:90+t3",   # 行业板块
        "fields": "f2,f3,f4,f12,f14,f62,f6,f20",
    }
    data = _api("qt/clist/get", params)
    if not data or "diff" not in data:
        print(json.dumps({"error": "无板块数据", "sectors": []}, ensure_ascii=False))
        sys.exit(1)

    sectors = []
    for item in data["diff"]:
        sectors.append({
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "price": item.get("f2", "-"),
            "pct": item.get("f3", 0),
            "change": item.get("f4", 0),
            "fund_flow": item.get("f62", 0) or 0,     # 主力净流入(元)
            "turnover": item.get("f6", 0) or 0,         # 成交额(元)
            "market_cap": item.get("f20", 0) or 0,      # 总市值
        })

    result = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(sectors),
        "sectors": sectors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── main ───────────────────────────────────────────────

COMMANDS = {
    "sectors": cmd_sectors,
    # "stocks": cmd_stocks,    # Task 2
    # "detail": cmd_detail,    # Task 3
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fetcher.py <sectors|stocks|detail> [参数]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}，可用: {list(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    COMMANDS[cmd]()
```

- [ ] **Step 5: 运行验证 sectors**

```powershell
python D:\Agent\git\stock-workflow\fetcher\fetcher.py sectors
```

Expected: JSON 输出，含 `sectors` 数组，每项有 `code/name/pct/fund_flow/turnover`，`total > 0`。

- [ ] **Step 6: Commit**

```powershell
cd D:\Agent\git
git add stock-workflow\fetcher\fetcher.py stock-workflow\fetcher\requirements.txt
git commit -m "feat: fetcher.py sectors 命令 — 行业板块排行"
```

---

### Task 2: fetcher.py stocks 命令

**Files:**
- Modify: `D:\Agent\git\stock-workflow\fetcher\fetcher.py` — 追加 `cmd_stocks` 函数并注册

**Interfaces:**
- Consumes: `_api()` from Task 1
- Produces: `python fetcher/fetcher.py stocks BK0428` → JSON stdout 打印板块成分股，按涨幅降序

- [ ] **Step 1: 追加 cmd_stocks 函数**

在 `cmd_sectors` 函数后面、`COMMANDS` 字典前面，追加：

```python
# ── stocks ─────────────────────────────────────────────

# 板块代码 → 市场前缀的映射缓存
_sector_market_cache = {}

def _get_sector_market(code):
    """获取板块对应的市场前缀 (1=SH, 0=SZ)"""
    if code in _sector_market_cache:
        return _sector_market_cache[code]
    # 查板块详情取市场
    secid = f"90.{code}"
    params = {"secid": secid, "fields": "f57,f58"}
    data = _api("qt/stock/get", params)
    if data:
        _sector_market_cache[code] = 0  # 板块默认用0
    return 0

def cmd_stocks():
    """拉取指定板块成分股。

    用法: python fetcher.py stocks BK0428

    返回字段：
        f2  - 现价
        f3  - 涨跌幅(%)
        f4  - 涨跌额
        f5  - 成交量(手)
        f6  - 成交额(元)
        f7  - 振幅(%)
        f8  - 量比
        f9  - 市盈率(动态)
        f10 - 换手率(%)
        f12 - 股票代码
        f13 - 市场(1=沪, 0=深)
        f14 - 股票名称
        f15 - 最高价
        f16 - 最低价
        f17 - 今开
        f18 - 昨收
        f20 - 总市值
        f62 - 主力净流入(元)
        f66 - 超大单净流入(元)
        f184- 5日涨跌幅(%)
    """
    if len(sys.argv) < 3:
        print("用法: python fetcher.py stocks <板块代码>", file=sys.stderr)
        print("示例: python fetcher.py stocks BK0428", file=sys.stderr)
        sys.exit(1)

    sector_code = sys.argv[2]
    params = {
        "fid": "f3",          # 按涨跌幅排序
        "po": "1",
        "pz": "200",
        "pn": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": f"b:{sector_code}",   # 板块成分股
        "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f62,f66,f184",
    }
    data = _api("qt/clist/get", params)
    if not data or "diff" not in data:
        print(json.dumps({"error": f"无板块 {sector_code} 数据", "stocks": []}, ensure_ascii=False))
        sys.exit(1)

    stocks = []
    for item in data["diff"]:
        if item.get("f2") == "-":
            continue  # 跳过停牌
        stocks.append({
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "market": item.get("f13", 0),
            "price": item.get("f2", 0),
            "pct": item.get("f3", 0),
            "change": item.get("f4", 0),
            "volume": item.get("f5", 0) or 0,
            "turnover": item.get("f6", 0) or 0,
            "amplitude": item.get("f7", 0),
            "volume_ratio": item.get("f8", 0),
            "pe": item.get("f9", 0),
            "turnover_rate": item.get("f10", 0),
            "high": item.get("f15", 0),
            "low": item.get("f16", 0),
            "open": item.get("f17", 0),
            "prev_close": item.get("f18", 0),
            "market_cap": item.get("f20", 0) or 0,
            "fund_flow": item.get("f62", 0) or 0,       # 主力净流入(元)
            "super_large_flow": item.get("f66", 0) or 0, # 超大单净流入(元)
            "pct_5d": item.get("f184", 0),                # 5日涨跌幅(%)
        })

    result = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sector_code": sector_code,
        "total": len(stocks),
        "stocks": stocks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

- [ ] **Step 2: 注册 stocks 命令**

修改 `COMMANDS` 字典：

```python
COMMANDS = {
    "sectors": cmd_sectors,
    "stocks": cmd_stocks,
    # "detail": cmd_detail,    # Task 3
}
```

- [ ] **Step 3: 运行验证 stocks**

```powershell
python D:\Agent\git\stock-workflow\fetcher\fetcher.py stocks BK0428
```

Expected: JSON 含 `stocks` 数组，`sector_code: "BK0428"`，每项有 name/pct/pe/fund_flow 等字段，`total > 0`。

- [ ] **Step 4: 测试无参报错**

```powershell
python D:\Agent\git\stock-workflow\fetcher\fetcher.py stocks
```

Expected: exit code 1，stderr 提示用法。

- [ ] **Step 5: Commit**

```powershell
cd D:\Agent\git
git add stock-workflow\fetcher\fetcher.py
git commit -m "feat: fetcher.py stocks 命令 — 板块成分股"
```

---

### Task 3: fetcher.py detail 命令

**Files:**
- Modify: `D:\Agent\git\stock-workflow\fetcher\fetcher.py` — 追加 `cmd_detail` 函数并注册

**Interfaces:**
- Consumes: `_api()` from Task 1
- Produces: `python fetcher/fetcher.py detail 600900` → JSON stdout 打印个股深度数据

- [ ] **Step 1: 追加 cmd_detail 函数**

在 `cmd_stocks` 函数后面追加：

```python
# ── detail ─────────────────────────────────────────────

def _guess_market(code):
    """根据代码猜测市场: 6开头=沪(1), 0/3开头=深(0), 4/8开头=北交所(0)"""
    if code.startswith("6"):
        return 1
    return 0

def cmd_detail():
    """拉取个股深度数据。

    用法: python fetcher.py detail 600900

    返回:
        quote: 实时行情（价/量/换手/振幅/量比/PE/总市值）
        fund: 资金面（主力净流入/净比）
        kline: 日K技术指标（MA5/MA10/MA20/MA60/MACD/KDJ）
    """
    if len(sys.argv) < 3:
        print("用法: python fetcher.py detail <股票代码>", file=sys.stderr)
        print("示例: python fetcher.py detail 600900", file=sys.stderr)
        sys.exit(1)

    code = sys.argv[2]
    market = _guess_market(code)
    secid = f"{market}.{code}"

    # 实时行情快照
    quote_fields = "f43,f44,f45,f46,f47,f48,f50,f57,f58,f116,f162,f167,f168,f169,f170,f171"
    quote_params = {"secid": secid, "fields": quote_fields}
    quote_data = _api("qt/stock/get", quote_params)
    time.sleep(1)

    # K 线数据（最近 120 个交易日，用于计算技术指标）
    kline_params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",  # 日K
        "fqt": "1",    # 前复权
        "lmt": "120",
    }
    kline_data = _api("qt/stock/get", kline_params)

    result = {"updated": time.strftime("%Y-%m-%d %H:%M:%S"), "code": code, "market": market}

    # 解析行情
    if quote_data:
        q = quote_data
        result["quote"] = {
            "name": q.get("f58", ""),
            "price": q.get("f43", 0),
            "high": q.get("f44", 0),
            "low": q.get("f45", 0),
            "open": q.get("f46", 0),
            "volume": q.get("f47", 0) or 0,
            "turnover": q.get("f48", 0) or 0,
            "volume_ratio": q.get("f50", 0),
            "market_cap": q.get("f116", 0) or 0,
            "pe": q.get("f162", 0),
            "turnover_rate": q.get("f167", 0),
            "amplitude": q.get("f50", 0),  # 振幅用当日计算
        }
    else:
        result["quote"] = {}

    # 计算技术指标
    if kline_data and "klines" in kline_data:
        klines = kline_data["klines"]
        closes = []
        highs = []
        lows = []
        for k in klines[-120:]:
            parts = k.split(",")
            closes.append(float(parts[2]))
            highs.append(float(parts[3]))
            lows.append(float(parts[4]))

        def sma(arr, n):
            if len(arr) < n:
                return None
            return round(sum(arr[-n:]) / n, 2)

        # 均线
        ma5 = sma(closes, 5)
        ma10 = sma(closes, 10)
        ma20 = sma(closes, 20)
        ma60 = sma(closes, 60)

        # MACD (12,26,9)
        def ema(arr, n):
            if len(arr) < n:
                return None
            k = 2 / (n + 1)
            result = sum(arr[:n]) / n
            for v in arr[n:]:
                result = v * k + result * (1 - k)
            return round(result, 2)

        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        dif = round(ema12 - ema26, 2) if (ema12 and ema26) else None

        # 计算 DIF 序列求 DEA
        difs = []
        if len(closes) >= 26:
            e12 = sum(closes[:12]) / 12
            e26 = sum(closes[:26]) / 26
            for v in closes[26:]:
                e12 = v * (2/13) + e12 * (11/13)
                e26 = v * (2/27) + e26 * (25/27)
                difs.append(e12 - e26)

        dea = None
        macd_bar = None
        if len(difs) >= 9:
            dea = round(sum(difs[:9]) / 9, 2)
            for d in difs[9:]:
                dea = d * (2/10) + dea * (8/10)
            dea = round(dea, 2)
            if dif is not None and dea is not None:
                macd_bar = round((dif - dea) * 2, 2)

        # KDJ (9,3,3)
        k_val = d_val = j_val = None
        if len(closes) >= 9:
            n = 9
            high_n = max(highs[-n:])
            low_n = min(lows[-n:])
            rsv = (closes[-1] - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
            # 简化: 单次 KDJ 近似（无历史序列迭代）
            k_val = round(rsv * 1/3 + 50 * 2/3, 2)
            d_val = round(k_val * 1/3 + 50 * 2/3, 2)
            j_val = round(3 * k_val - 2 * d_val, 2)

        result["technicals"] = {
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            "macd_dif": dif,
            "macd_dea": dea,
            "macd_bar": macd_bar,
            "kdj_k": k_val,
            "kdj_d": d_val,
            "kdj_j": j_val,
            "close_series": closes[-5:],  # 最近5天收盘价
        }
    else:
        result["technicals"] = {}

    print(json.dumps(result, ensure_ascii=False, indent=2))
```

- [ ] **Step 2: 注册 detail 命令**

```python
COMMANDS = {
    "sectors": cmd_sectors,
    "stocks": cmd_stocks,
    "detail": cmd_detail,
}
```

- [ ] **Step 3: 运行验证 detail**

```powershell
python D:\Agent\git\stock-workflow\fetcher\fetcher.py detail 600900
```

Expected: JSON 含 `quote`（name/price/pe/volume_ratio/market_cap）和 `technicals`（ma5/ma10/ma20/ma60/macd_dif/macd_bar/kdj_k/kdj_d/kdj_j）。

- [ ] **Step 4: Commit**

```powershell
cd D:\Agent\git
git add stock-workflow\fetcher\fetcher.py
git commit -m "feat: fetcher.py detail 命令 — 个股深度数据+技术指标"
```

---

### Task 4: SKILL.md — Claude Code Skill 编排层

**Files:**
- Create: `D:\Agent\git\stock-workflow\skill\STOCK.md`

**Interfaces:**
- Consumes: `python fetcher/fetcher.py sectors|stocks|detail` from Tasks 1-3
- Produces: Claude Code 可调用的选股工作流 Skill

- [ ] **Step 1: 写 STOCK.md**

```markdown
# 选股工作流

中线波段选股辅助工具。先看板块，再挑个股——找到资金流入的强势板块，从板块中筛选优质标的。

## 触发条件

- `/daily-report` 或 "日报" "今日速报" → 执行完整日报流程
- "看板块" "板块排行" "哪些板块在涨" → 板块扫描
- "看<板块名>" 如 "看电力板块" → 指定板块选股
- "分析<股票名>" 如 "分析长江电力" → 个股深度分析
- "筛<条件>" 如 "筛PE<20且ROE>15%" → 条件选股

## 工作流：日报 (/daily-report)

### Step 1 — 板块扫描

执行: `python fetcher/fetcher.py sectors`

分析规则:
1. 筛选「涨跌幅 > 0」且「主力净流入 > 0」的板块
2. 按涨幅排名 TOP10 + 按资金流入排名 TOP10，取交集 → 锁定 3-5 个强势板块
3. 对锁定板块标注 5 日趋势（若板块有 5 日涨跌数据则判断连红/震荡/转弱）

### Step 2 — 板块选股

对每个锁定板块，执行: `python fetcher/fetcher.py stocks <板块代码>`

加权打分规则 (满分 10 分):
- 资金面 (50%，5 分)：主力净流入占比 = 主力净流入/成交额。> 10% = 5 分, 5-10% = 4 分, 0-5% = 3 分, -5-0% = 2 分, < -5% = 1 分
- 基本面 (35%，3.5 分)：PE 在 5-50 之间且 >0 得 1.5 分（合理估值），PE < 0 得 0 分（亏损）；量比 > 1.5 得 1 分（活跃）；ROE 用 PE 倒数近似估算，> 10% 得 1 分
- 技术面 (15%，1.5 分)：5日涨跌幅 > 0 且今日涨幅 > 0 得 1.5 分（趋势向上）; 仅一项 > 0 得 0.8 分; 均跌得 0 分

每板块取 TOP3，去重（同一股票只保留评分最高的那次），生成标的池。

### Step 3 — 风险速览

取大盘数据：比较板块总资金流向、涨跌板块数量比。

策略判断:
- 进攻：强势板块 ≥ 3 个，资金整体流入
- 观望：1-2 个强势板块，资金分化
- 防守：0 个强势板块，资金整体流出

### Step 4 — 输出格式

```markdown
## 📊 YYYY-MM-DD 收盘速报

### 🔥 强势板块
| 排名 | 板块 | 涨幅% | 主力净流入 | 成交额 | 5日趋势 |

### 🎯 标的池
| 排名 | 股票 | 代码 | 板块 | 涨幅% | 主力净比 | PE | 量比 | 评分 |

### ⚠️ 风险速览
- 大盘资金: 流入/流出 xx 亿
- 涨跌板块: 上涨 xx 个 / 下跌 xx 个
- 策略: 进攻/观望/防守
```

## 工作流：按需钻取

### 看板块

用户说"看板块排行" → 执行 `python fetcher/fetcher.py sectors` → 输出涨幅 TOP15 + 资金流入 TOP15 双表。

### 看指定板块

用户说"看电力板块" → 解析板块名对应的代码 → 执行 `python fetcher/fetcher.py stocks BK0428` → 按上述打分规则排序 → 输出 TOP10 标的表。

### 分析个股

用户说"分析长江电力" → 执行 `python fetcher/fetcher.py detail 600900` → 输出：
- 行情快照（现价/涨跌/PE/市值/换手/量比）
- 资金面（主力净流入/净比/超大单）
- 技术面（MA5/10/20/60 均线状态，MACD 金叉/死叉，KDJ 超买/超卖）
- 综合一句话评价（不构成投资建议）

### 条件筛选

用户说"筛PE<20且ROE>10%" → 取全部板块 → 遍历取成分股 → 按条件筛选 → 输出结果表。

## 数据来源

东方财富公开 API（push2.eastmoney.com），免费使用。

## 免责声明

⚠️ 本工具仅供数据分析参考，不构成任何投资建议。所有投资决策由用户自行做出，风险自负。股市有风险，投资需谨慎。
```

- [ ] **Step 2: Commit**

```powershell
cd D:\Agent\git
git add stock-workflow\skill\STOCK.md
git commit -m "feat: SKILL.md — 选股工作流 Skill 编排层"
```

---

### Task 5: 集成测试 — 跑通完整日报

**Files:**
- 无新建文件

**验证:** 三个数据命令都能正常返回，Skill 流程可走通。

- [ ] **Step 1: 验证 sectors → stocks → detail 串联**

```powershell
# 1. 取板块列表，找到电力板块代码
python D:\Agent\git\stock-workflow\fetcher\fetcher.py sectors | python -c "import sys,json; d=json.load(sys.stdin); elec=[s for s in d['sectors'] if '电' in s['name']]; print(json.dumps(elec, ensure_ascii=False, indent=2))"
```

Expected: 输出含「电力」板块条目。

```powershell
# 2. 取电力板块成分股，取第一只股票的代码
python D:\Agent\git\stock-workflow\fetcher\fetcher.py stocks BK0428 | python -c "import sys,json; d=json.load(sys.stdin); print(d['stocks'][0]['code'], d['stocks'][0]['name'])"
```

Expected: 输出第一只电力股代码和名称。

```powershell
# 3. 取该个股深度数据
python D:\Agent\git\stock-workflow\fetcher\fetcher.py detail 600900
```

Expected: JSON 含 quote 和 technicals。

- [ ] **Step 2: 验证错误处理**

```powershell
# 无参数
python D:\Agent\git\stock-workflow\fetcher\fetcher.py
# Expected: exit code 1, stderr 提示用法

# 无效板块代码
python D:\Agent\git\stock-workflow\fetcher\fetcher.py stocks XXXXXX
# Expected: JSON 含 error 信息，exit code 1
```

- [ ] **Step 3: Commit**

```powershell
cd D:\Agent\git
git add -A
git commit -m "test: 集成测试通过 — sectors→stocks→detail 链路正常"
```

---

### Task 6: README.md

**Files:**
- Create: `D:\Agent\git\stock-workflow\README.md`

- [ ] **Step 1: 写 README.md**

```markdown
# 选股工作流

Claude Code 选股辅助工具。中线波段为主，先看板块再挑个股。

## 快速开始

```bash
# 安装依赖
pip install -r fetcher/requirements.txt

# 测试数据层
python fetcher/fetcher.py sectors          # 行业板块排行
python fetcher/fetcher.py stocks BK0428    # 电力板块成分股
python fetcher/fetcher.py detail 600900    # 长江电力深度数据
```

## 搭配 Claude Code 使用

将 `skill/STOCK.md` 安装为 Claude Code Skill，然后对话：

- `/daily-report` — 每日收盘速报
- "看板块" — 板块排行
- "看电力板块" — 指定板块选股
- "分析长江电力" — 个股深度

## 工作原理

三层架构：Claude Skill 编排 → Python fetcher 取数 → 东方财富 API

## 免责声明

⚠️ 本工具仅供数据分析参考，不构成任何投资建议。投资有风险，决策需谨慎。
```

- [ ] **Step 2: Commit**

```powershell
cd D:\Agent\git
git add stock-workflow\README.md
git commit -m "docs: README"
```

---

### Task 7: 安装 Skill 到 Claude Code 并端到端测试

**Files:**
- Modify: 将 `STOCK.md` 安装到 `~/.claude/skills/`

- [ ] **Step 1: 安装 Skill**

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\stock-workflow"
Copy-Item "D:\Agent\git\stock-workflow\skill\STOCK.md" "$env:USERPROFILE\.claude\skills\stock-workflow\SKILL.md"
```

- [ ] **Step 2: 测试 /daily-report**

在 Claude Code 对话中输入 `/daily-report`，验证 Skill 被触发，板块扫描→选股→风险速览链路完整。

- [ ] **Step 3: 测试钻取**

输入 "看电力板块" / "分析长江电力"，验证按需钻取正常。

- [ ] **Step 4: Commit**

```powershell
# 无需 commit，Skill 安装在用户目录
# 记录完成状态
```
```

