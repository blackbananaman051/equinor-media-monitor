# Equinor AI Media Monitor

A web application that fetches daily oil & energy news and produces an AI-powered intelligence briefing tailored to Equinor. Anyone with the URL can read the report; only the admin can trigger a new analysis.

## Live deployment (Render — recommended)

Render has a free tier that runs Python/Flask with a persistent disk for report storage.

**Step 1 — Push to GitHub**

Create a new GitHub repo, push this project to it.

**Step 2 — Create a Render account**

Sign up at https://render.com (free).

**Step 3 — New Web Service**

- Click **New → Web Service**
- Connect your GitHub repo
- Render auto-detects the `render.yaml` config — click **Deploy**

**Step 4 — Set environment variables**

In the Render dashboard → your service → **Environment**, add:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | Your key from https://console.anthropic.com |
| `NEWS_API_KEY` | Your key from https://newsapi.org |
| `ADMIN_PASSWORD` | A strong password only you know |

**Step 5 — Deploy**

Click **Manual Deploy → Deploy latest commit**. Your site will be live at `https://your-service-name.onrender.com`.

**Step 6 — Run the first analysis**

Open the URL, click **Run Today's Analysis**, enter your admin password. From then on, the scheduler generates a new report automatically every weekday at 08:00.

---

## How it works for visitors

- **Anyone** can open the URL and read the daily briefing — no login needed.
- The **"Run Today's Analysis"** button is only visible when `ADMIN_PASSWORD` is set on the server.
- Clicking it opens a password prompt. Only someone with the admin password can trigger a new analysis (which costs API credits).
- The scheduler automatically runs analysis each weekday morning, so the report is usually ready when visitors arrive.

---

## Local development

```bash
# 1. Create venv
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure keys
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY, NEWS_API_KEY, and ADMIN_PASSWORD

# 4. Run
python app.py

# 5. Open
# http://localhost:5000
```

---

## Alternative deployment platforms

**Railway** (https://railway.app) — $5/month hobby plan, persistent storage:
```bash
railway login
railway init
railway up
# Set env vars in the Railway dashboard
```

**Fly.io** (https://fly.io) — free tier with volumes:
```bash
fly launch
fly secrets set ANTHROPIC_API_KEY=... NEWS_API_KEY=... ADMIN_PASSWORD=...
fly deploy
```

Both platforms pick up the `Procfile` automatically.

---

## Project structure

```
equinor-media-monitor/
├── app.py          # Flask server & routes
├── fetcher.py      # NewsAPI article fetcher
├── analyzer.py     # Claude AI analysis
├── reporter.py     # Report save/load
├── scheduler.py    # Weekday auto-run at 08:00
├── Procfile        # Production server command
├── render.yaml     # Render deployment config
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html  # Dashboard UI
└── reports/        # Generated reports (git-ignored)
```

## Notes

- The `reports/` directory is git-ignored. On Render, it's stored on a persistent 1 GB disk.
- The free NewsAPI tier allows 100 requests/day. The app uses at most 8 queries × 5 articles = 40 requests per run.
- Claude model: `claude-opus-4-5`.
- Analysis takes approximately 1–2 minutes per run.
