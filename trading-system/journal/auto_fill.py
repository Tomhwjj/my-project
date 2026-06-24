"""东方财富 API 自动补全交易字段"""
import time
import requests
from datetime import datetime

EASTMONEY_BASE = "https://push2.eastmoney.com/api/qt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}


def _api(path, params, timeout=15):
    """统一API调用，自动重试"""
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
        except Exception:
            if attempt == 0:
                time.sleep(2)
                continue
    return None


def _guess_market(code):
    """6开头=沪市(1), 其余=深市(0)"""
    return 1 if code.startswith("6") else 0


def auto_fill(code: str) -> dict:
    """给定股票代码，从东方财富拉实时行情补全字段。
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

    # 查所属板块：从行业板块数据里匹配（用成交额最大的一个）
    try:
        sectors_data = _api("clist/get", {
            "fid": "f3", "po": "1", "pz": "200", "pn": "1",
            "np": "1", "fltt": "2", "invt": "2", "fs": "m:90",
            "fields": "f2,f3,f12,f14",
        })
        time.sleep(0.5)
        if sectors_data:
            raw = sectors_data.get("diff", {})
            items = list(raw.values()) if isinstance(raw, dict) else raw
            if items:
                result["sector"] = items[0].get("f14", "")
                result["sector_pct"] = items[0].get("f3", 0)
    except Exception:
        pass

    return result


def match_sell(conn, code: str, sell_price: float, sell_time: str) -> dict:
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

    # 每股盈亏 × 100股
    profit_loss = round((sell_price - buy_price) * 100, 2)
    profit_pct = round((sell_price - buy_price) / buy_price * 100, 2)

    try:
        bt = datetime.strptime(buy_time[:10], "%Y-%m-%d")
        st = datetime.strptime(sell_time[:10], "%Y-%m-%d")
        hold_days = (st - bt).days
    except Exception:
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
    except Exception:
        pass
    return "震荡"
