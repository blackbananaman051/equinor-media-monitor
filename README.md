# Equinor AI Media Monitor

A local web app that aggregates Norwegian oil & energy news from multiple sources, analyzes each article with Claude AI, and produces a structured weekly intelligence briefing. Runs entirely on your own machine.

The website you can use to run the program is:

https://norskenergianalyse-com.onrender.com/

---

## Features

- **AI briefing** — Claude analyzes up to 50 articles in parallel and synthesizes a structured report: headline, situation summary, top risk, top opportunity, market sentiment, key themes, and strategic observations
- **Live market data** — real-time prices for Equinor (EQNR.OL), Aker BP (AKRBP.OL), Vår Energi (VAR.OL), Brent crude, and NOK/USD
- **Multi-source news** — pulls from NewsAPI (15 targeted queries) + 4 RSS feeds (OilPrice.com, Rigzone, Offshore Energy, Upstream Online)
- **Week-over-week comparison** — AI diff between this week and last week: sentiment shift, new themes, resolved themes, outlook
- **Trend charts** — 8-week history of market sentiment and article relevance
- **Company deep-dives** — dedicated pages for Equinor, Aker BP, Vår Energi, Petoro, Lundin, TotalEnergies with filtered articles and sentiment charts
- **Search** — full-text search across all saved reports and articles
- **Email digest** — scheduled HTML email with briefing highlights (supports Gmail App Password)
- **Alerts** — browser notifications + email alerts on negative sentiment or falling oil prices
- **PDF export** — print-optimised layout via the browser
- **Scheduled analysis** — daily auto-run via background scheduler

---

## Requirements

- Python 3.10 or newer — [python.org/downloads](https://www.python.org/downloads/)
- **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key
- **NewsAPI key** — [newsapi.org](https://newsapi.org) → Get API Key

Both have free tiers.

---

## Setup

**1. Clone or download the project**

```bash
git clone https://github.com/blackbananaman051/equinor-media-monitor.git
cd equinor-media-monitor
```

**2. Create and activate a virtual environment**

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Mac/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the app

**Windows** — double-click `run.bat`, or:

```bash
python app.py
```

The browser opens automatically at `http://localhost:5000`.

On first launch you will be taken to a setup screen to enter your API keys. Keys are stored locally in `config.json` and never leave your machine.

Click **Run Analysis** to fetch and analyze the latest news (takes 1–2 minutes on first run).

---

## Project structure

```
app.py          Flask server and all routes
analyzer.py     Claude AI article analysis and briefing synthesis
fetcher.py      NewsAPI + RSS news fetching
reporter.py     Report save/load and trend data
scheduler.py    Daily scheduled analysis
market.py       Live market data via yfinance
emailer.py      HTML email digest via SMTP
alerts.py       Alert threshold checking
config.py       API key and settings storage
templates/
  index.html    Main dashboard
  setup.html    First-run API key setup + email config
  company.html  Company deep-dive page
```

---

## Notes

- Reports are saved to `reports/` so you never need to re-run just to view past briefings.
- The NewsAPI free tier is for local/development use only — perfect for this setup.
- Typical API usage per run: ~15–20 NewsAPI requests + ~50 Claude API calls (one per article + synthesis).
