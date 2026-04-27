import os
import json
from pathlib import Path

if os.name == "nt":
    CONFIG_DIR = Path.home() / "AppData" / "Roaming" / "EquinorMediaMonitor"
else:
    CONFIG_DIR = Path.home() / ".equinor-media-monitor"

CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_config()
    existing.update(data)
    with open(CONFIG_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def get_key(name):
    return os.getenv(name) or load_config().get(name, "")


def is_configured():
    return bool(get_key("ANTHROPIC_API_KEY") and get_key("NEWS_API_KEY"))


def get_email_config():
    return load_config().get("email", {})


def save_email_config(data):
    cfg = load_config()
    existing = cfg.get("email", {})
    existing.update(data)
    save_config({"email": existing})


def get_alert_config():
    from alerts import get_alert_config as _get
    return _get()


def save_alert_config(data):
    from alerts import save_alert_config as _save
    _save(data)
