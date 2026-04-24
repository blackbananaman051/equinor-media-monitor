# Equinor AI Media Monitor

A local web app that fetches daily oil & energy news and generates an AI-powered intelligence briefing tailored to Equinor. Runs on your own computer in your browser.

---

## What you need before starting

- **Python 3.10 or newer** — download at https://www.python.org/downloads/
- **An Anthropic API key** — sign up free at https://console.anthropic.com → go to **API Keys** → **Create Key**
- **A NewsAPI key** — sign up free at https://newsapi.org → click **Get API Key**

Both are free to get.

---

## Setup (do this once)

**1. Download the project**

Click the green **Code** button on this page → **Download ZIP** → unzip it somewhere on your computer.

Or if you have git:
```
git clone https://github.com/blackbananaman051/equinor-media-monitor.git
cd equinor-media-monitor
```

**2. Open a terminal in the project folder**

On Windows: open the folder in File Explorer, then right-click → **Open in Terminal**

**3. Create a virtual environment**

```
python -m venv venv
```

**4. Activate it**

Windows:
```
venv\Scripts\activate
```

Mac/Linux:
```
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal line.

**5. Install dependencies**

```
pip install -r requirements.txt
```

**6. Add your API keys**

Create a file called `.env` in the project folder (copy from the example):

Windows:
```
copy .env.example .env
```

Mac/Linux:
```
cp .env.example .env
```

Open `.env` in any text editor and fill in your keys:

```
ANTHROPIC_API_KEY=paste_your_anthropic_key_here
NEWS_API_KEY=paste_your_newsapi_key_here
```

---

## Running the app

```
python app.py
```

Then open your browser and go to:

```
http://localhost:5000
```

Click **Run Today's Analysis** — it will fetch the latest energy news and generate a briefing (takes about 1–2 minutes).

---

## Notes

- The app runs entirely on your own computer. Your API keys never leave your machine.
- Reports are saved to the `reports/` folder so you don't need to re-run every time you open the app.
- The NewsAPI free tier only works when running locally (not on a deployed server), which is perfect for this setup.
- Daily API usage: ~40 NewsAPI requests + ~20 Claude API calls per analysis run — well within free tier limits.
