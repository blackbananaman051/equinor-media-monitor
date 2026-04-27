import os
import json
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-5"

SYSTEM_PROMPT = (
    "You are a senior intelligence analyst working directly for Equinor ASA, the Norwegian state-owned energy company. "
    "Your sole focus is protecting and advancing Equinor's strategic interests. "
    "You monitor global energy, geopolitical, and financial news and assess every development through a single lens: "
    "what does this mean for Equinor specifically — its share price, production assets on the Norwegian Continental Shelf, "
    "international upstream portfolio (US, Brazil, UK, Tanzania, Argentina), offshore wind projects (Empire Wind, Hywind, Dogger Bank), "
    "LNG exports, hydrogen strategy, carbon capture projects, and its relationship with the Norwegian government and Petroleum Directorate. "
    "Risks and opportunities must be framed in terms of direct Equinor exposure. "
    "Respond only with valid JSON."
)


def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")
    return anthropic.Anthropic(api_key=api_key)


def analyze_article(client, article, _retry=True):
    prompt = f"""Analyze this news article from Equinor's perspective and return a JSON object with these fields:
- summary: 2-3 sentence summary in Norwegian focusing on the Equinor angle
- sentiment: "positive", "negative", or "neutral" — for Equinor specifically
- norway_relevance: "high", "medium", or "low" — how directly this affects Equinor's business, assets, or strategy
- relevance_reason: one sentence explaining the specific Equinor exposure (mention affected assets, business units, or financials if relevant)
- tags: list of 3 relevant tags (e.g. "NCS production", "offshore wind", "oil price", "Equinor shares", "LNG exports")

Article title: {article['title']}
Source: {article['source']}
Published: {article['publishedAt']}
Description: {article['description']}
Content: {article['content']}

Return only valid JSON, no other text."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        if "norway_relevance" in result and "equinor_relevance" not in result:
            result["equinor_relevance"] = result["norway_relevance"]
        return result
    except json.JSONDecodeError:
        if _retry:
            import time as _t; _t.sleep(2)
            return analyze_article(client, article, _retry=False)
        return {
            "summary": article.get("description", "No summary available."),
            "sentiment": "neutral",
            "norway_relevance": "low",
            "equinor_relevance": "low",
            "relevance_reason": "JSON parse failed after retry.",
            "tags": [],
        }
    except anthropic.APIError as e:
        return {
            "summary": article.get("description", "No summary available."),
            "sentiment": "neutral",
            "norway_relevance": "low",
            "equinor_relevance": "low",
            "relevance_reason": f"API error: {str(e)}",
            "tags": [],
        }


def synthesize_briefing(client, analyzed_articles):
    summaries_text = "\n\n".join(
        f"[{i+1}] {a['title']}\nSentiment: {a.get('sentiment','neutral')}\n"
        f"Relevance: {a.get('equinor_relevance','low')}\n"
        f"Summary: {a.get('summary','')}\n"
        f"Reason: {a.get('relevance_reason','')}"
        for i, a in enumerate(analyzed_articles)
    )

    prompt = f"""Based on these {len(analyzed_articles)} analyzed news articles, produce a weekly Equinor intelligence briefing.
Return a JSON object with these fields:
- date: today's date in YYYY-MM-DD format
- headline: one sentence — the single most important development for Equinor this week
- situation_summary: 3-4 sentences covering global energy market conditions and their direct relevance to Equinor's operations and strategy
- equinor_impact: 2-3 sentences specifically about the impact on Equinor — reference actual Equinor assets, business lines, or financials where possible (NCS fields, Empire Wind, Hywind, LNG, EQNR share price, oil fund exposure)
- top_risk: the single biggest near-term risk for Equinor specifically (not the industry in general)
- top_opportunity: the single biggest strategic opportunity Equinor should capitalize on
- market_sentiment: "positive", "negative", or "neutral" — for Equinor's outlook
- oil_price_trend: "rising", "falling", or "stable"
- key_themes: list of 3-5 key themes directly relevant to Equinor this week
- recommended_actions: list of 2-4 concrete strategic observations or action points for Equinor leadership

Articles analyzed:
{summaries_text}

Return only valid JSON, no other text."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "headline": "Analysis synthesis failed.",
            "situation_summary": str(e),
            "equinor_impact": "Unable to generate impact assessment.",
            "top_risk": "Unknown",
            "top_opportunity": "Unknown",
            "market_sentiment": "neutral",
            "oil_price_trend": "stable",
            "key_themes": [],
            "recommended_actions": [],
        }


def compare_reports(client, current, previous):
    prompt = f"""Compare these two weekly Norwegian oil industry intelligence reports and identify what changed.

CURRENT ({current['date']}):
- Headline: {current.get('headline','')}
- Sentiment: {current.get('market_sentiment','')}
- Oil trend: {current.get('oil_price_trend','')}
- Top risk: {current.get('top_risk','')}
- Top opportunity: {current.get('top_opportunity','')}
- Key themes: {', '.join(current.get('key_themes',[]))}

PREVIOUS ({previous['date']}):
- Headline: {previous.get('headline','')}
- Sentiment: {previous.get('market_sentiment','')}
- Oil trend: {previous.get('oil_price_trend','')}
- Top risk: {previous.get('top_risk','')}
- Top opportunity: {previous.get('top_opportunity','')}
- Key themes: {', '.join(previous.get('key_themes',[]))}

Return a JSON object with:
- sentiment_shift: e.g. "Neutral → Negative" or "Stable — no change"
- key_changes: list of 3-4 most important changes since last week
- new_themes: list of themes that are new this week
- resolved_themes: list of themes from last week that disappeared
- outlook: one forward-looking sentence based on the change

Return only valid JSON."""

    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=600, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return None


def run_full_analysis(articles):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client   = get_client()
    total    = len(articles)
    analyzed = [None] * total

    def _do(i):
        return i, {**articles[i], **analyze_article(client, articles[i])}

    print(f"  Analyzing {total} articles in parallel...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed({pool.submit(_do, i): i for i in range(total)}):
            i, merged = future.result()
            analyzed[i] = merged
            print(f"    [{sum(a is not None for a in analyzed)}/{total}] {articles[i]['title'][:55]}...")

    print("  Synthesizing weekly briefing...")
    briefing = synthesize_briefing(client, analyzed)
    briefing["date"]           = datetime.utcnow().strftime("%Y-%m-%d")
    briefing["articles"]       = analyzed
    briefing["articles_count"] = total
    briefing["relevant_count"] = sum(
        1 for a in analyzed if a.get("equinor_relevance") in ("high", "medium")
    )

    return briefing
