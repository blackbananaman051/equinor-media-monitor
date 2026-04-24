import os
import json
from datetime import datetime

REPORTS_DIR = os.getenv("REPORTS_DIR", os.path.join(os.path.dirname(__file__), "reports"))


def save_report(briefing):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    date_str = briefing.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    path = os.path.join(REPORTS_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)
    return path


def load_report(date_str):
    path = os.path.join(REPORTS_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_report():
    if not os.path.exists(REPORTS_DIR):
        return None
    files = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")],
        reverse=True,
    )
    if not files:
        return None
    with open(os.path.join(REPORTS_DIR, files[0]), "r", encoding="utf-8") as f:
        return json.load(f)


def list_report_dates():
    if not os.path.exists(REPORTS_DIR):
        return []
    return sorted(
        [f.replace(".json", "") for f in os.listdir(REPORTS_DIR) if f.endswith(".json")],
        reverse=True,
    )
