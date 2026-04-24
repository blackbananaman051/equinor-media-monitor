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
