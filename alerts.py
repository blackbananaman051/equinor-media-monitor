from config import load_config, save_config

DEFAULTS = {
    "enabled":           False,
    "alert_negative":    False,
    "alert_falling_oil": False,
    "alert_both":        True,
}


def get_alert_config():
    return {**DEFAULTS, **load_config().get("alerts", {})}


def save_alert_config(data):
    cfg = load_config()
    existing = cfg.get("alerts", {})
    existing.update(data)
    save_config({"alerts": existing})


def check_alerts(report):
    cfg = get_alert_config()
    if not cfg.get("enabled"):
        return []

    sentiment  = report.get("market_sentiment", "neutral")
    oil_trend  = report.get("oil_price_trend",  "stable")
    is_neg     = sentiment == "negative"
    is_falling = oil_trend == "falling"

    triggered = []
    if cfg.get("alert_both") and is_neg and is_falling:
        triggered.append({
            "level":   "critical",
            "message": f"CRITICAL: Negative sentiment + falling oil prices. Risk: {report.get('top_risk', '')[:120]}",
        })
    elif cfg.get("alert_negative") and is_neg:
        triggered.append({
            "level":   "warning",
            "message": f"Market sentiment is negative. {report.get('headline', '')[:120]}",
        })
    elif cfg.get("alert_falling_oil") and is_falling:
        triggered.append({
            "level":   "warning",
            "message": f"Oil price is falling. Risk: {report.get('top_risk', '')[:120]}",
        })

    return triggered
