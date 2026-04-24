import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NEWS_API_BASE = "https://newsapi.org/v2/everything"

SEARCH_QUERIES = [
    "Norway oil gas industry",
    "Equinor",
    "Norwegian petroleum",
    "North Sea oil",
    "Brent crude oil price",
    "Statoil Norway energy",
    "Norwegian continental shelf",
    "Aker BP offshore",
    "OPEC oil production",
    "Norway energy transition",
    "offshore drilling Norway",
    "oil gas exploration Norway",
]


def fetch_articles():
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is not set. Please add it via the setup screen.")

    seen_titles = set()
    articles = []
    last_api_error = None
    from_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for query in SEARCH_QUERIES:
        if len(articles) >= 20:
            break
        try:
            response = requests.get(
                NEWS_API_BASE,
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 5,
                    "from": from_date,
                    "apiKey": NEWS_API_KEY,
                },
                timeout=10,
            )
            data = response.json()

            # Capture any API-level error message on first failure
            if data.get("status") == "error" and not last_api_error:
                last_api_error = data.get("message", f"HTTP {response.status_code}")
                continue

            for item in data.get("articles", []):
                title = item.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                if not item.get("description") and not item.get("content"):
                    continue

                seen_titles.add(title)
                articles.append(
                    {
                        "title": title,
                        "description": item.get("description", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", {}).get("name", "Unknown"),
                        "publishedAt": item.get("publishedAt", ""),
                        "content": (item.get("content") or item.get("description") or "")[:500],
                    }
                )

                if len(articles) >= 20:
                    break

        except requests.RequestException as e:
            last_api_error = str(e)
            continue

    if not articles:
        if last_api_error:
            raise RuntimeError(f"NewsAPI error: {last_api_error}")
        raise RuntimeError(
            "No articles were fetched. Check your NEWS_API_KEY and internet connection."
        )

    return articles
