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

_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 minutes


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
