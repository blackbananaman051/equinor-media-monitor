import os
import requests
from dotenv import load_dotenv

load_dotenv()

GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
GNEWS_BASE = "https://gnews.io/api/v4/search"

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
    if not GNEWS_API_KEY:
        raise ValueError("GNEWS_API_KEY is not set. Please add it to your environment variables.")

    seen_titles = set()
    articles = []

    for query in SEARCH_QUERIES:
        if len(articles) >= 20:
            break
        try:
            response = requests.get(
                GNEWS_BASE,
                params={
                    "q": query,
                    "lang": "en",
                    "max": 3,
                    "sortby": "publishedAt",
                    "apikey": GNEWS_API_KEY,
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
            "No articles were fetched. Check your GNEWS_API_KEY and internet connection."
        )

    return articles
