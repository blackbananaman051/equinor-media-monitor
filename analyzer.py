import os
import json
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-5"

SYSTEM_PROMPT = (
    "You are an intelligence analyst covering the Norwegian oil and gas industry. "
    "Your job is to monitor global energy news weekly and produce a clear, concise briefing "
    "about what matters for Norway's oil and gas sector. This includes companies like Equinor, "
    "Aker BP, Vår Energi, TotalEnergies Norway, and the Norwegian government's petroleum policy. "
    "Consider how news affects oil prices, production on the Norwegian continental shelf, "
    "the Norwegian Oil Fund (Government Pension Fund), energy transition strategy, and "
    "regulatory developments from the Norwegian Petroleum Directorate. "
    "Respond only with valid JSON."
)


def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")
    return anthropic.Anthropic(api_key=api_key)


def analyze_article(client, article, _retry=True):
    prompt = f"""Analyze this news article and return a JSON object with these fields:
- summary: 2-3 sentence summary in Norwegian
- sentiment: "positive", "negative", or "neutral"
- norway_relevance: "high", "medium", or "low" (how relevant is this to the Norwegian oil industry)
- relevance_reason: why this matters to Norway's oil and gas sector specifically
- tags: list of 3 relevant tags

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

    prompt = f"""Based on these {len(analyzed_articles)} analyzed news articles about the Norwegian oil and gas industry,
produce a comprehensive weekly intelligence briefing. Return a JSON object with these fields:
- date: today's date in YYYY-MM-DD format
- headline: one-sentence summary of the most important development for Norwegian oil today
- situation_summary: 3-4 sentence overview of what happened in Norwegian and global oil & energy markets
- equinor_impact: 2-3 sentences about what today's news means for Norway's oil sector (Equinor, Aker BP, Vår Energi, oil fund)
- top_risk: the single biggest risk for the Norwegian oil industry today
- top_opportunity: the single biggest opportunity for the Norwegian oil industry today
- market_sentiment: "positive", "negative", or "neutral"
- oil_price_trend: "rising", "falling", or "stable"
- key_themes: list of 3-5 key themes from today's news
- recommended_actions: list of 2-4 strategic observations or actions relevant to Norwegian oil stakeholders

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
