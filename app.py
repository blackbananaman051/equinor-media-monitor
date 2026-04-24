import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from fetcher import fetch_articles
from analyzer import run_full_analysis
from reporter import save_report, load_report, load_latest_report, list_report_dates
from scheduler import start_scheduler

load_dotenv()

app = Flask(__name__)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def check_api_keys():
    missing = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.getenv("NEWS_API_KEY"):
        missing.append("NEWS_API_KEY")
    return missing


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return jsonify({"error": "ADMIN_PASSWORD is not set on the server."}), 500
        provided = (
            request.headers.get("X-Admin-Password")
            or (request.get_json(silent=True) or {}).get("admin_password", "")
        )
        if provided != ADMIN_PASSWORD:
            return jsonify({"error": "Unauthorized. Incorrect admin password."}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    report = load_report(today) or load_latest_report()
    missing_keys = check_api_keys()
    report_dates = list_report_dates()
    admin_enabled = bool(ADMIN_PASSWORD)
    return render_template(
        "index.html",
        report=report,
        missing_keys=missing_keys,
        report_dates=report_dates,
        today=today,
        admin_enabled=admin_enabled,
    )


@app.route("/analyze", methods=["POST"])
@require_admin
def analyze():
    missing = check_api_keys()
    if missing:
        return jsonify({"error": f"Missing API keys: {', '.join(missing)}."}), 400

    try:
        print("Fetching articles...")
        articles = fetch_articles()
        print(f"Fetched {len(articles)} articles. Running AI analysis...")
        briefing = run_full_analysis(articles)
        path = save_report(briefing)
        print(f"Report saved: {path}")
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
        return jsonify({"error": "No reports available yet."}), 404
    return jsonify(report)


if __name__ == "__main__":
    start_scheduler()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
