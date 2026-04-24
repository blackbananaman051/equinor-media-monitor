import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_BASE = "https://newsapi.org/v2/everything"

SEARCH_QUERIES = [
    "Equinor",
    "oil price Brent crude",
    "North Sea energy",
    "Norway oil gas",
    "OPEC oil market",
    "offshore energy renewable",
    "carbon capture CCS energy",
    "energy transition oil company",
]


def fetch_articles():
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is not set. Please add it to your .env file.")

    seen_titles = set()
    articles = []
    from_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
            response.raise_for_status()
            data = response.json()

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
            print(f"Warning: Failed to fetch query '{query}': {e}")
            continue

    if not articles:
        raise RuntimeError(
            "No articles were fetched. Check your NEWS_API_KEY and internet connection."
        )

    return articles
