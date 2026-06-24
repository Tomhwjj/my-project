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
        "fid": "f3",
        "po": "1",
        "pz": "200",
        "pn": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": "m:90",
        "fields": "f2,f3,f4,f12,f14,f62,f6,f20",
    }
    data = _api("clist/get", params)
    if not data or "diff" not in data:
        print(json.dumps({"error": "无板块数据", "sectors": []}, ensure_ascii=False))
        sys.exit(1)

    # API 对 m:90 返回 dict 格式 diff，b:BKxxxx 返回 list 格式
    raw = data["diff"]
    if isinstance(raw, dict):
        items = list(raw.values())
    else:
        items = raw

    sectors = []
    for item in items:
        sectors.append({
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "price": item.get("f2", "-"),
            "pct": item.get("f3", 0),
            "change": item.get("f4", 0),
            "fund_flow": item.get("f62", 0) or 0,
            "turnover": item.get("f6", 0) or 0,
            "market_cap": item.get("f20", 0) or 0,
        })

    result = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(sectors),
        "sectors": sectors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── stocks ─────────────────────────────────────────────

def cmd_stocks():
    """拉取指定板块成分股，支持批量。

    用法: python fetcher.py stocks BK1137 BK1036 BK1101
    """
    if len(sys.argv) < 3:
        print("用法: python fetcher.py stocks <板块代码...>", file=sys.stderr)
        print("示例: python fetcher.py stocks BK1137 BK1036 BK1101", file=sys.stderr)
        sys.exit(1)

    sector_codes = sys.argv[2:]
    all_results = []

    for idx, sector_code in enumerate(sector_codes):
        if idx > 0:
            time.sleep(1.5)  # 批量请求间隔，防限流

        params = {
            "fid": "f3",
            "po": "1",
            "pz": "200",
            "pn": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fs": f"b:{sector_code}",
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f62,f66,f184",
        }
        data = _api("clist/get", params)
        if not data or "diff" not in data:
            all_results.append({"sector_code": sector_code, "total": 0, "stocks": [], "error": "无数据"})
            continue

        stocks = []
        raw_stocks = data["diff"]
        stock_items = list(raw_stocks.values()) if isinstance(raw_stocks, dict) else raw_stocks
        for item in stock_items:
            if item.get("f2") == "-":
                continue
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
                "fund_flow": item.get("f62", 0) or 0,
                "super_large_flow": item.get("f66", 0) or 0,
                "pct_5d": item.get("f184", 0),
            })

        all_results.append({
            "sector_code": sector_code,
            "total": len(stocks),
            "stocks": stocks,
        })

    result = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": all_results,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── detail ─────────────────────────────────────────────

def _guess_market(code):
    """根据代码猜测市场: 6开头=沪(1), 0/3开头=深(0)"""
    if code.startswith("6"):
        return 1
    return 0

def cmd_detail():
    """拉取个股深度数据。

    用法: python fetcher.py detail 600900
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
    quote_data = _api("stock/get", quote_params)
    time.sleep(1)

    # K 线数据（日K，最近120天）
    # 尝试独立的 kline 接口
    kline_data = _api("stock/kline/get", {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "lmt": "120",
    })

    result = {"updated": time.strftime("%Y-%m-%d %H:%M:%S"), "code": code, "market": market}

    # 解析行情
    if quote_data:
        q = quote_data
        result["quote"] = {
            "name": q.get("f58", ""),
            "price": (q.get("f43", 0) or 0) / 100 if (q.get("f43", 0) or 0) > 100 else q.get("f43", 0),
            "high": (q.get("f44", 0) or 0) / 100 if (q.get("f44", 0) or 0) > 100 else q.get("f44", 0),
            "low": (q.get("f45", 0) or 0) / 100 if (q.get("f45", 0) or 0) > 100 else q.get("f45", 0),
            "open": (q.get("f46", 0) or 0) / 100 if (q.get("f46", 0) or 0) > 100 else q.get("f46", 0),
            "volume": q.get("f47", 0) or 0,
            "turnover": q.get("f48", 0) or 0,
            "volume_ratio": q.get("f50", 0),
            "market_cap": q.get("f116", 0) or 0,
            "pe": round((q.get("f162", 0) or 0) / 100, 2) if (q.get("f162", 0) or 0) > 500 else q.get("f162", 0),
            "turnover_rate": q.get("f167", 0),
        }
    else:
        result["quote"] = {}

    # K 线数据 → 技术指标
    closes = []
    highs = []
    lows = []
    if kline_data and kline_data.get("klines"):
        for k in kline_data["klines"]:
            parts = k.split(",")
            if len(parts) >= 5:
                closes.append(float(parts[2]))
                highs.append(float(parts[3]))
                lows.append(float(parts[4]))

    if closes:
        def sma(arr, n):
            if len(arr) < n:
                return None
            return round(sum(arr[-n:]) / n, 2)

        def ema(arr, n):
            if len(arr) < n:
                return None
            k = 2 / (n + 1)
            result = sum(arr[:n]) / n
            for v in arr[n:]:
                result = v * k + result * (1 - k)
            return round(result, 2)

        ma5 = sma(closes, 5)
        ma10 = sma(closes, 10)
        ma20 = sma(closes, 20)
        ma60 = sma(closes, 60)

        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        dif = round(ema12 - ema26, 2) if (ema12 is not None and ema26 is not None) else None

        dea = None
        macd_bar = None
        if dif is not None and len(closes) >= 35:
            difs = []
            e12 = sum(closes[:12]) / 12
            e26 = sum(closes[:26]) / 26
            for v in closes[26:]:
                e12 = v * (2/13) + e12 * (11/13)
                e26 = v * (2/27) + e26 * (25/27)
                difs.append(e12 - e26)
            if len(difs) >= 9:
                dea = sum(difs[:9]) / 9
                for d in difs[9:]:
                    dea = d * (2/10) + dea * (8/10)
                dea = round(dea, 2)
                macd_bar = round((dif - dea) * 2, 2)

        k_val = d_val = j_val = None
        if len(closes) >= 9:
            n = 9
            high_n = max(highs[-n:])
            low_n = min(lows[-n:])
            if high_n != low_n:
                rsv = (closes[-1] - low_n) / (high_n - low_n) * 100
            else:
                rsv = 50
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
            "close_series": closes[-5:],
        }
    else:
        result["technicals"] = {}

    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── main ───────────────────────────────────────────────

COMMANDS = {
    "sectors": cmd_sectors,
    "stocks": cmd_stocks,
    "detail": cmd_detail,
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
