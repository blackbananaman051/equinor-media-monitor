import os
import sys
import json
import threading
import webbrowser
import time
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, jsonify, request, redirect, Response, stream_with_context
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
from config import get_key, is_configured, save_config as _save_config, get_email_config, save_email_config

for _key in ("ANTHROPIC_API_KEY", "NEWS_API_KEY"):
    _val = get_key(_key)
    if _val:
        os.environ[_key] = _val

from fetcher import fetch_articles
from analyzer import run_full_analysis, analyze_article, synthesize_briefing, get_client as get_analyzer_client, compare_reports
from reporter import save_report, load_report, load_latest_report, list_report_dates, get_trend_data
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
    today        = datetime.utcnow().strftime("%Y-%m-%d")
    report       = load_report(today) or load_latest_report()
    report_dates = list_report_dates()
    trend_data   = get_trend_data()
    email_cfg    = get_email_config()
    return render_template(
        "index.html",
        report=report,
        report_dates=report_dates,
        today=today,
        admin_enabled=bool(ADMIN_PASSWORD),
        trend_data=trend_data,
        email_configured=bool(email_cfg.get("enabled")),
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


@app.route("/analyze/stream", methods=["POST"])
def analyze_stream():
    # All request-context reads must happen here, outside the generator.
    if ADMIN_PASSWORD:
        provided = (
            request.headers.get("X-Admin-Password")
            or (request.get_json(silent=True) or {}).get("admin_password", "")
        )
        if provided != ADMIN_PASSWORD:
            return jsonify({"error": "Unauthorized."}), 401

    anthropic_key = (request.headers.get("X-Anthropic-Key") or "").strip() or os.getenv("ANTHROPIC_API_KEY", "")
    news_key      = (request.headers.get("X-News-Key")      or "").strip() or os.getenv("NEWS_API_KEY", "")

    missing = [k for k, v in [("ANTHROPIC_API_KEY", anthropic_key), ("NEWS_API_KEY", news_key)] if not v]
    if missing:
        return jsonify({"error": f"Missing API keys: {', '.join(missing)}."}), 400

    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    os.environ["NEWS_API_KEY"]      = news_key

    def generate():
        def evt(data):
            return f"data: {json.dumps(data)}\n\n"

        try:
            yield evt({"status": "fetching", "message": "Fetching latest news..."})

            articles = fetch_articles()
            total    = len(articles)
            yield evt({"status": "fetched", "count": total})

            client   = get_analyzer_client()
            analyzed = [None] * total
            completed_count = 0

            def _do(i):
                return i, {**articles[i], **analyze_article(client, articles[i])}

            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(_do, i): i for i in range(total)}
                for future in as_completed(futures):
                    i, merged = future.result()
                    analyzed[i]      = merged
                    completed_count += 1
                    yield evt({
                        "status":  "analyzing",
                        "current": completed_count,
                        "total":   total,
                        "title":   articles[i]["title"][:65],
                    })

            yield evt({"status": "synthesizing", "message": "Generating intelligence briefing..."})

            briefing = synthesize_briefing(client, analyzed)
            briefing["date"]           = datetime.utcnow().strftime("%Y-%m-%d")
            briefing["articles"]       = analyzed
            briefing["articles_count"] = total
            briefing["relevant_count"] = sum(
                1 for a in analyzed if a.get("equinor_relevance") in ("high", "medium")
            )
            save_report(briefing)

            # Week-over-week comparison
            try:
                all_dates = list_report_dates()
                if len(all_dates) >= 2:
                    prev = load_report(all_dates[1])
                    if prev:
                        yield evt({"status": "comparing", "message": "Generating week-over-week analysis..."})
                        diff = compare_reports(client, briefing, prev)
                        if diff:
                            briefing["week_over_week"] = diff
                            briefing["prev_date"]      = all_dates[1]
                            save_report(briefing)
            except Exception:
                pass

            yield evt({"status": "done", "report": briefing})

        except Exception as e:
            yield evt({"status": "error", "error": str(e)})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


@app.route("/api/market")
def market_data():
    try:
        from market import get_market_data
        return jsonify(get_market_data())
    except ImportError:
        return jsonify({"error": "yfinance not installed"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/market/history")
def market_history():
    try:
        from market import get_stock_history
        period = request.args.get("period", "1y")
        return jsonify(get_stock_history(period))
    except ImportError:
        return jsonify({"error": "yfinance not installed"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/trends")
def trends():
    return jsonify(get_trend_data())


@app.route("/save-email-config", methods=["POST"])
def save_email_config_route():
    data = request.get_json() or {}
    save_email_config(data)
    return jsonify({"success": True})


@app.route("/test-email", methods=["POST"])
def test_email():
    from emailer import send_digest
    from reporter import load_latest_report as _latest
    report = _latest()
    if not report:
        return jsonify({"error": "No report to send — run an analysis first."}), 400
    email_cfg = get_email_config()
    ok, msg   = send_digest(report, email_cfg)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"error": msg}), 400


@app.route("/save-alert-config", methods=["POST"])
def save_alert_config_route():
    from alerts import save_alert_config
    data = request.get_json() or {}
    save_alert_config(data)
    return jsonify({"success": True})


COMPANY_SLUGS = {
    "equinor":       ("Equinor",        ["equinor", "statoil"]),
    "aker-bp":       ("Aker BP",        ["aker bp", "akrbp"]),
    "var-energi":    ("Vår Energi",     ["vår energi", "var energi"]),
    "petoro":        ("Petoro",         ["petoro"]),
    "lundin":        ("Lundin",         ["lundin"]),
    "totalenergies": ("TotalEnergies",  ["totalenergies", "total norway"]),
}


@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify({"results": [], "query": q})

    results  = []
    seen     = set()

    for date in list_report_dates()[:24]:
        report = load_report(date)
        if not report:
            continue

        # Search inside articles
        for a in report.get("articles", []):
            text = (a.get("title","") + " " + a.get("summary","") + " " + a.get("description","")).lower()
            if q in text and a.get("title") not in seen:
                seen.add(a.get("title",""))
                results.append({
                    "type":       "article",
                    "title":      a.get("title",""),
                    "url":        a.get("url",""),
                    "summary":    (a.get("summary") or a.get("description") or "")[:180],
                    "source":     a.get("source",""),
                    "sentiment":  a.get("sentiment","neutral"),
                    "relevance":  a.get("equinor_relevance","low"),
                    "date":       date,
                })

        # Search in briefing fields
        briefing_text = " ".join(filter(None, [
            report.get("headline"), report.get("situation_summary"),
            report.get("top_risk"), report.get("top_opportunity"),
        ])).lower()
        key = f"brief:{date}"
        if q in briefing_text and key not in seen:
            seen.add(key)
            results.append({
                "type":    "briefing",
                "title":   report.get("headline","Weekly brief")[:90],
                "url":     f"/?date={date}",
                "summary": report.get("situation_summary","")[:180],
                "source":  "Intelligence Brief",
                "date":    date,
            })

    results.sort(key=lambda r: r["date"], reverse=True)
    return jsonify({"results": results[:40], "query": q})


@app.route("/company/<slug>")
def company_page(slug):
    if slug not in COMPANY_SLUGS:
        return "Company not found", 404

    display_name, search_terms = COMPANY_SLUGS[slug]
    articles        = []
    sentiment_trend = []

    for date in list_report_dates()[:16]:
        report = load_report(date)
        if not report:
            continue
        day_articles = [
            {**a, "report_date": date}
            for a in report.get("articles", [])
            if any(t in (a.get("title","") + str(a.get("tags",""))).lower() for t in search_terms)
        ]
        articles.extend(day_articles)
        if day_articles:
            pos  = sum(1 for a in day_articles if a.get("sentiment") == "positive")
            neg  = sum(1 for a in day_articles if a.get("sentiment") == "negative")
            sentiment_trend.append({
                "date": date, "positive": pos,
                "negative": neg, "neutral": len(day_articles) - pos - neg,
                "total": len(day_articles),
            })

    articles.sort(key=lambda a: a.get("report_date",""), reverse=True)
    return render_template(
        "company.html",
        company_name=display_name,
        company_slug=slug,
        articles=articles[:60],
        sentiment_trend=list(reversed(sentiment_trend[-8:])),
        today=datetime.utcnow().strftime("%Y-%m-%d"),
    )


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
