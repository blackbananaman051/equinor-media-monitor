import os
import json
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-4-5"

SYSTEM_PROMPT = (
    "You are an intelligence analyst for Equinor's communications team. "
    "Your job is to monitor global oil & energy news daily and produce a clear, concise briefing "
    "about what matters for Equinor specifically. Equinor is a Norwegian state-majority-owned energy "
    "company focused on oil, gas, and renewable energy. Consider how news affects Equinor's stock, "
    "operations, reputation, regulatory environment, and energy transition strategy. "
    "Respond only with valid JSON."
)


def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please add it to your .env file.")
    return anthropic.Anthropic(api_key=api_key)


def analyze_article(client, article):
    prompt = f"""Analyze this news article and return a JSON object with these fields:
- summary: 2-3 sentence summary in Norwegian
- sentiment: "positive", "negative", or "neutral"
- equinor_relevance: "high", "medium", or "low"
- relevance_reason: why this matters to Equinor specifically
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
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        return {
            "summary": article.get("description", "No summary available."),
            "sentiment": "neutral",
            "equinor_relevance": "low",
            "relevance_reason": f"Analysis failed: {str(e)}",
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

    prompt = f"""Based on these {len(analyzed_articles)} analyzed news articles about oil, energy, and Equinor,
produce a comprehensive daily intelligence briefing. Return a JSON object with these fields:
- date: today's date in YYYY-MM-DD format
- headline: one-sentence summary of the day in oil & energy
- situation_summary: 3-4 sentence overview of what happened globally in oil and energy markets today
- equinor_impact: 2-3 sentences specifically about what today's news means for Equinor
- top_risk: the single biggest risk for Equinor today based on the news
- top_opportunity: the single biggest opportunity for Equinor today
- market_sentiment: "positive", "negative", or "neutral"
- oil_price_trend: "rising", "falling", or "stable"
- key_themes: list of 3-5 key themes from today's news
- recommended_actions: list of 2-4 actions the Equinor comms team should consider today

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


def run_full_analysis(articles):
    client = get_client()

    analyzed = []
    for i, article in enumerate(articles):
        print(f"  Analyzing article {i+1}/{len(articles)}: {article['title'][:60]}...")
        result = analyze_article(client, article)
        merged = {**article, **result}
        analyzed.append(merged)

    print("  Synthesizing daily briefing...")
    briefing = synthesize_briefing(client, analyzed)
    briefing["articles"] = analyzed
    briefing["articles_count"] = len(analyzed)
    briefing["relevant_count"] = sum(
        1 for a in analyzed if a.get("equinor_relevance") in ("high", "medium")
    )

    return briefing
