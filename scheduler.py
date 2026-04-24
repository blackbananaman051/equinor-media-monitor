import schedule
import time
import threading
from fetcher import fetch_articles
from analyzer import run_full_analysis
from reporter import save_report


def run_daily_analysis():
    print("[Scheduler] Starting scheduled daily analysis...")
    try:
        articles = fetch_articles()
        briefing = run_full_analysis(articles)
        path = save_report(briefing)
        print(f"[Scheduler] Report saved to {path}")
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
    print("[Scheduler] Started — will run analysis weekdays at 08:00.")
