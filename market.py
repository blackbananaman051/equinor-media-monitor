import time
import yfinance as yf
from datetime import datetime

TICKERS = {
    "EQNR":   ("EQNR.OL",  "Equinor",    "NOK"),
    "AKRBP":  ("AKRBP.OL", "Aker BP",    "NOK"),
    "VAR":    ("VAR.OL",   "Vår Energi", "NOK"),
    "BRENT":  ("BZ=F",     "Brent",      "USD"),
    "NOKUSD": ("NOKUSD=X", "NOK/USD",    ""),
}

_cache         = {"data": None, "ts": 0}
_history_cache = {}
CACHE_TTL      = 300   # 5 minutes
HISTORY_TTL    = 3600  # 1 hour


def get_market_data():
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        return _cache["data"]

    result = {}
    for key, (symbol, name, currency) in TICKERS.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d")
            if hist.empty:
                result[key] = {"name": name, "currency": currency, "price": None, "change": None}
                continue
            cur  = round(float(hist["Close"].iloc[-1]), 2)
            prev = round(float(hist["Close"].iloc[-2]), 2) if len(hist) > 1 else cur
            chg  = round(((cur - prev) / prev) * 100, 2) if prev else 0
            result[key] = {
                "name": name, "symbol": symbol, "currency": currency,
                "price": cur, "change": chg,
            }
        except Exception as e:
            result[key] = {"name": name, "currency": currency, "price": None, "change": None, "error": str(e)}

    result["_ts"] = datetime.utcnow().strftime("%H:%M UTC")
    _cache["data"] = result
    _cache["ts"]   = now
    return result


# Norwegian oil stocks for the history chart (Brent on secondary axis)
HISTORY_STOCKS = {
    "EQNR":  ("EQNR.OL",  "Equinor",    "NOK", "#3b82f6"),
    "AKRBP": ("AKRBP.OL", "Aker BP",    "NOK", "#10b981"),
    "VAR":   ("VAR.OL",   "Vår Energi", "NOK", "#f59e0b"),
    "BRENT": ("BZ=F",     "Brent crude","USD", "#ef4444"),
}

PERIOD_MAP = {
    "3mo": "3mo",
    "6mo": "6mo",
    "1y":  "1y",
}


def get_stock_history(period="1y"):
    cache_key = period
    now = time.time()
    cached = _history_cache.get(cache_key)
    if cached and now - cached["ts"] < HISTORY_TTL:
        return cached["data"]

    yf_period = PERIOD_MAP.get(period, "1y")
    labels = None
    series = []
    stats  = []

    for key, (symbol, name, currency, color) in HISTORY_STOCKS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist   = ticker.history(period=yf_period, interval="1wk")
            if hist.empty:
                continue

            closes = hist["Close"].dropna()
            dates  = [d.strftime("%Y-%m-%d") for d in closes.index]

            if labels is None:
                labels = dates
            else:
                # align to the shorter set
                if len(dates) < len(labels):
                    labels = dates

            prices = [round(float(p), 2) for p in closes.tolist()]

            # Indexed to 100 at start of period for fair comparison
            base = prices[0] if prices[0] != 0 else 1
            indexed = [round(p / base * 100, 2) for p in prices]

            first = prices[0]
            last  = prices[-1]
            pct   = round((last - first) / first * 100, 2) if first else 0
            high  = round(float(closes.max()), 2)
            low   = round(float(closes.min()), 2)

            series.append({
                "key":      key,
                "name":     name,
                "symbol":   symbol,
                "currency": currency,
                "color":    color,
                "prices":   prices,
                "indexed":  indexed,
            })
            stats.append({
                "key":      key,
                "name":     name,
                "currency": currency,
                "color":    color,
                "current":  last,
                "change":   pct,
                "high":     high,
                "low":      low,
            })
        except Exception:
            continue

    data = {"labels": labels or [], "series": series, "stats": stats, "period": period}
    _history_cache[cache_key] = {"data": data, "ts": now}
    return data
