import os
import requests
import feedparser
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NEWS_API_BASE = "https://newsapi.org/v2/everything"
MAX_ARTICLES  = 50
PAGE_SIZE     = 15

RSS_FEEDS = [
    "https://oilprice.com/rss/main",
    "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
    "https://www.offshore-energy.biz/feed/",
    "https://www.upstreamonline.com/rss",
]

OIL_KEYWORDS = [
    "oil", "gas", "energy", "petroleum", "offshore", "equinor",
    "brent", "opec", "lng", "drilling", "norway", "norwegian",
]


def fetch_rss_articles(cutoff_dt):
    seen_titles = set()
    articles    = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = (entry.get("title") or "").strip()
                if not title or title in seen_titles:
                    continue
                summary = entry.get("summary") or entry.get("description") or ""
                text    = (title + " " + summary).lower()
                if not any(kw in text for kw in OIL_KEYWORDS):
                    continue
                # Date filter — skip entries older than cutoff
                published = entry.get("published_parsed")
                if published:
                    from calendar import timegm
                    pub_dt = datetime.utcfromtimestamp(timegm(published))
                    if pub_dt < cutoff_dt:
                        continue
                seen_titles.add(title)
                articles.append({
                    "title":       title,
                    "description": summary[:300],
                    "url":         entry.get("link", ""),
                    "source":      feed.feed.get("title", url),
                    "publishedAt": entry.get("published", ""),
                    "content":     summary[:500],
                })
        except Exception:
            continue
    return articles

SEARCH_QUERIES = [
    "Norway oil gas industry",
    "Equinor",
    "Norwegian petroleum",
    "North Sea oil",
    "Brent crude oil price",
    "Norwegian continental shelf",
    "Aker BP offshore",
    "OPEC oil production",
    "Norway energy transition",
    "offshore drilling Norway",
    "oil gas exploration Norway",
    "LNG Norway export",
    "Norwegian energy policy",
    "oil price forecast 2025",
    "Norway carbon emissions energy",
]


def fetch_articles():
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY is not set. Please add it via the setup screen.")

    cutoff    = datetime.utcnow() - timedelta(days=7)
    seen_urls = set()
    seen_titles = set()
    articles    = []
    last_api_error = None
    from_date = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Pull RSS articles first (free, no rate-limit)
    rss_articles = fetch_rss_articles(cutoff)
    for a in rss_articles:
        if a["title"] not in seen_titles and (not a["url"] or a["url"] not in seen_urls):
            seen_titles.add(a["title"])
            if a["url"]:
                seen_urls.add(a["url"])
            articles.append(a)

    for query in SEARCH_QUERIES:
        if len(articles) >= MAX_ARTICLES:
            break
        try:
            response = requests.get(
                NEWS_API_BASE,
                params={
                    "q":        query,
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": PAGE_SIZE,
                    "from":     from_date,
                    "apiKey":   NEWS_API_KEY,
                },
                timeout=10,
            )
            data = response.json()

            if data.get("status") == "error" and not last_api_error:
                last_api_error = data.get("message", f"HTTP {response.status_code}")
                continue

            for item in data.get("articles", []):
                title = item.get("title", "").strip()
                url   = item.get("url",   "").strip()

                if not title or title in seen_titles:
                    continue
                if url and url in seen_urls:
                    continue
                if not item.get("description") and not item.get("content"):
                    continue

                seen_titles.add(title)
                if url:
                    seen_urls.add(url)

                articles.append({
                    "title":       title,
                    "description": item.get("description", ""),
                    "url":         url,
                    "source":      item.get("source", {}).get("name", "Unknown"),
                    "publishedAt": item.get("publishedAt", ""),
                    "content":     (item.get("content") or item.get("description") or "")[:500],
                })

                if len(articles) >= MAX_ARTICLES:
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
