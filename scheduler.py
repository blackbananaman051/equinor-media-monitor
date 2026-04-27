import schedule
import time
import threading
from fetcher import fetch_articles
from analyzer import run_full_analysis
from reporter import save_report


def run_daily_analysis():
    print("[Scheduler] Starting scheduled analysis...")
    try:
        articles = fetch_articles()
        briefing = run_full_analysis(articles)
        path     = save_report(briefing)
        print(f"[Scheduler] Report saved to {path}")

        # Check alerts and send email
        try:
            from alerts import check_alerts
            from config import get_email_config
            from emailer import send_digest

            triggered    = check_alerts(briefing)
            email_cfg    = get_email_config()
            should_email = email_cfg.get("enabled") and (
                email_cfg.get("send_always") or triggered
            )

            if should_email:
                ok, msg = send_digest(briefing, email_cfg, alert_messages=triggered or None)
                print(f"[Scheduler] Email: {msg}")

            if triggered:
                for a in triggered:
                    print(f"[Scheduler] Alert ({a['level']}): {a['message'][:80]}")

        except Exception as e:
            print(f"[Scheduler] Email/alert error: {e}")

    except Exception as e:
        print(f"[Scheduler] Analysis failed: {e}")


def start_scheduler():
    schedule.every().monday.at("08:00").do(run_daily_analysis)
    schedule.every().tuesday.at("08:00").do(run_daily_analysis)
    schedule.every().wednesday.at("08:00").do(run_daily_analysis)
    schedule.every().thursday.at("08:00").do(run_daily_analysis)
    schedule.every().friday.at("08:00").do(run_daily_analysis)

    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    print("[Scheduler] Started — weekdays at 08:00.")
