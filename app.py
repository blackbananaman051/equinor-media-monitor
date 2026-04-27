import os
import sys
import threading
import webbrowser
import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, request, redirect
from dotenv import load_dotenv

# ── Path setup for PyInstaller frozen .exe ──
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(os.path.expanduser("~"), "EquinorMediaMonitor")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "reports")

REPORTS_DIR = os.path.join(DATA_DIR, "reports") if getattr(sys, "frozen", False) else DATA_DIR
os.environ["REPORTS_DIR"] = REPORTS_DIR
os.makedirs(REPORTS_DIR, exist_ok=True)

load_dotenv()

# Inject stored API keys into os.environ so fetcher/analyzer can read them
from config import get_key, is_configured, save_config as _save_config

for _key in ("ANTHROPIC_API_KEY", "NEWS_API_KEY"):
    _val = get_key(_key)
    if _val:
        os.environ[_key] = _val

from fetcher import fetch_articles
from analyzer import run_full_analysis
from reporter import save_report, load_report, load_latest_report, list_report_dates
from scheduler import start_scheduler

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if ADMIN_PASSWORD:
            provided = (
                request.headers.get("X-Admin-Password")
                or (request.get_json(silent=True) or {}).get("admin_password", "")
            )
            if provided != ADMIN_PASSWORD:
                return jsonify({"error": "Unauthorized."}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    if not is_configured():
        return redirect("/setup")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    report = load_report(today) or load_latest_report()
    report_dates = list_report_dates()
    admin_enabled = bool(ADMIN_PASSWORD)
    return render_template(
        "index.html",
        report=report,
        report_dates=report_dates,
        today=today,
        admin_enabled=admin_enabled,
    )


@app.route("/setup")
def setup():
    return render_template("setup.html", configured=is_configured())


@app.route("/save-config", methods=["POST"])
def save_config_route():
    data = request.get_json()
    anthropic_key = (data.get("ANTHROPIC_API_KEY") or "").strip()
    news_key = (data.get("NEWS_API_KEY") or "").strip()

    if not anthropic_key or not news_key:
        return jsonify({"error": "Both API keys are required."}), 400

    _save_config({"ANTHROPIC_API_KEY": anthropic_key, "NEWS_API_KEY": news_key})
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    os.environ["NEWS_API_KEY"] = news_key

    return jsonify({"success": True})


@app.route("/analyze", methods=["POST"])
@require_admin
def analyze():
    # Allow callers to supply their own API keys in request headers.
    # This lets anyone use a shared/hosted deployment with their own keys.
    req_anthropic = request.headers.get("X-Anthropic-Key", "").strip()
    req_news      = request.headers.get("X-News-Key", "").strip()

    anthropic_key = req_anthropic or os.getenv("ANTHROPIC_API_KEY", "")
    news_key      = req_news      or os.getenv("NEWS_API_KEY", "")

    if not anthropic_key or not news_key:
        missing = []
        if not anthropic_key: missing.append("ANTHROPIC_API_KEY")
        if not news_key:      missing.append("NEWS_API_KEY")
        return jsonify({"error": f"Missing API keys: {', '.join(missing)}."}), 400

    # Inject into env for this request so fetcher/analyzer pick them up
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    os.environ["NEWS_API_KEY"]      = news_key

    try:
        print("Fetching articles...")
        articles = fetch_articles()
        print(f"Fetched {len(articles)} articles. Running AI analysis...")
        briefing = run_full_analysis(articles)
        save_report(briefing)
        print("Done.")
        return jsonify({"success": True, "report": briefing})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/report/<date>")
def get_report(date):
    report = load_report(date)
    if not report:
        return jsonify({"error": f"No report found for {date}"}), 404
    return jsonify(report)


@app.route("/api/latest")
def latest_report():
    report = load_latest_report()
    if not report:
        return jsonify({"error": "No reports yet."}), 404
    return jsonify(report)


def find_free_port(start=5000):
    import socket
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def open_browser(port):
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    start_scheduler()
    port = find_free_port(int(os.getenv("PORT", 5000)))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    if not debug:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
