from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
from typing import Any

import requests

from .config import Settings
from .models import COMMENT_INSIGHT_FIELDS


COMMENT_METRICS_FIELDS = [
    "run_id",
    "platform",
    "canonical_content_id",
    "comments_analyzed",
    "positive_count",
    "neutral_count",
    "negative_count",
    "purchase_signal_count",
    "avg_sentiment_score",
    "top_intent_label",
    "top_pain_point_label",
    "analyzed_at",
]

COMMENT_TOPICS_FIELDS = [
    "run_id",
    "platform",
    "canonical_content_id",
    "topic_tag",
    "mentions",
    "analyzed_at",
]


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_json_from_response(text: str) -> dict[str, Any] | None:
    raw = _coerce_text(text)
    if not raw:
        return None
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1).strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _heuristic_comment_analysis(comment_text: str) -> dict[str, Any]:
    text = _coerce_text(comment_text).lower()
    positive_words = ["good", "love", "great", "좋", "추천", "최고", "짱"]
    negative_words = ["bad", "hate", "expensive", "문제", "별로", "비싸", "싫"]
    purchase_words = ["buy", "price", "where", "구매", "가격", "링크", "어디서", "사고"]

    pos_hits = sum(1 for w in positive_words if w in text)
    neg_hits = sum(1 for w in negative_words if w in text)
    purchase_hit = any(w in text for w in purchase_words)

    sentiment_label = "neutral"
    sentiment_score = 0.0
    if pos_hits > neg_hits:
        sentiment_label = "positive"
        sentiment_score = min(1.0, 0.2 + (pos_hits * 0.2))
    elif neg_hits > pos_hits:
        sentiment_label = "negative"
        sentiment_score = max(-1.0, -0.2 - (neg_hits * 0.2))

    intent_label = "general_feedback"
    if "?" in text or purchase_hit:
        intent_label = "purchase_inquiry"
    elif "how" in text or "어떻게" in text:
        intent_label = "usage_question"

    pain_point_label = "none"
    pain_point_detail = ""
    if neg_hits > 0:
        pain_point_label = "negative_experience"
        pain_point_detail = "Negative tone or complaint in comment."

    product_interest_label = "high" if purchase_hit else "medium" if "추천" in text else "low"
    topic_tags = ["purchase"] if purchase_hit else ["general"]

    return {
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "intent_label": intent_label,
        "pain_point_label": pain_point_label,
        "pain_point_detail": pain_point_detail,
        "product_interest_label": product_interest_label,
        "topic_tags": topic_tags,
        "purchase_signal": bool(purchase_hit),
        "confidence": 0.45,
    }


def _analyze_with_openai(
    *,
    settings: Settings,
    analysis_model: str,
    comment_text: str,
    content_context: str,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for comment analysis.")

    system_prompt = (
        "Classify creator-market comments for outreach intelligence.\n"
        "Return strict JSON with keys:\n"
        "sentiment_label, sentiment_score, intent_label, pain_point_label, pain_point_detail, "
        "product_interest_label, topic_tags, purchase_signal, confidence\n"
        "Rules:\n"
        "- sentiment_label one of: positive, neutral, negative\n"
        "- sentiment_score between -1 and 1\n"
        "- topic_tags is an array of short snake_case tags\n"
        "- purchase_signal is true/false\n"
        "- confidence between 0 and 1\n"
        "- If unclear, choose neutral with lower confidence"
    )
    user_prompt = f"Content context: {content_context}\nComment: {comment_text}"

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": analysis_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "reasoning_effort": "minimal",
            "max_completion_tokens": 220,
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"OpenAI analysis failed ({response.status_code}): {response.text[:500]}")

    payload = response.json()
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI analysis response did not include choices.")
    content = _coerce_text(choices[0].get("message", {}).get("content"))
    parsed = _extract_json_from_response(content)
    if not parsed:
        raise RuntimeError("OpenAI analysis response was not valid JSON.")
    return parsed


def analyze_comment_items(
    *,
    comment_items: list[dict[str, Any]],
    settings: Settings,
    analysis_model: str | None = None,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    model_name = _coerce_text(analysis_model) or settings.openai_analysis_model or settings.openai_model
    rows = comment_items[: max(1, int(limit))] if limit else comment_items

    analyzed_at = datetime.now(tz=settings.timezone).isoformat()
    insights: list[dict[str, Any]] = []
    for row in rows:
        comment_text = _coerce_text(row.get("text"))
        content_context = _coerce_text(row.get("canonical_content_id"))
        try:
            analysis = _analyze_with_openai(
                settings=settings,
                analysis_model=model_name,
                comment_text=comment_text,
                content_context=content_context,
            )
        except Exception:
            analysis = _heuristic_comment_analysis(comment_text)

        topic_tags_value = analysis.get("topic_tags", [])
        if isinstance(topic_tags_value, list):
            topic_tags_text = "|".join(_coerce_text(tag) for tag in topic_tags_value if _coerce_text(tag))
        else:
            topic_tags_text = _coerce_text(topic_tags_value)

        insight = {
            "run_id": _coerce_text(row.get("run_id")),
            "platform": _coerce_text(row.get("platform")) or "tiktok",
            "canonical_content_id": _coerce_text(row.get("canonical_content_id")),
            "canonical_comment_id": _coerce_text(row.get("canonical_comment_id")),
            "sentiment_label": _coerce_text(analysis.get("sentiment_label")) or "neutral",
            "sentiment_score": float(analysis.get("sentiment_score", 0) or 0),
            "intent_label": _coerce_text(analysis.get("intent_label")) or "general_feedback",
            "pain_point_label": _coerce_text(analysis.get("pain_point_label")) or "none",
            "pain_point_detail": _coerce_text(analysis.get("pain_point_detail")),
            "product_interest_label": _coerce_text(analysis.get("product_interest_label")) or "unknown",
            "topic_tags": topic_tags_text,
            "purchase_signal": bool(analysis.get("purchase_signal", False)),
            "confidence": float(analysis.get("confidence", 0.5) or 0.5),
            "analysis_model": model_name,
            "analyzed_at": analyzed_at,
        }
        insights.append({field: insight.get(field, "") for field in COMMENT_INSIGHT_FIELDS})

    metrics_group: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "comments_analyzed": 0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "purchase_signal_count": 0,
            "sentiment_sum": 0.0,
            "intent_counter": Counter(),
            "pain_counter": Counter(),
        }
    )
    topics_group: dict[tuple[str, str, str, str], int] = defaultdict(int)

    for insight in insights:
        key = (
            _coerce_text(insight.get("run_id")),
            _coerce_text(insight.get("platform")) or "tiktok",
            _coerce_text(insight.get("canonical_content_id")),
        )
        metric = metrics_group[key]
        metric["comments_analyzed"] += 1
        sentiment_label = _coerce_text(insight.get("sentiment_label"))
        if sentiment_label == "positive":
            metric["positive_count"] += 1
        elif sentiment_label == "negative":
            metric["negative_count"] += 1
        else:
            metric["neutral_count"] += 1
        metric["sentiment_sum"] += float(insight.get("sentiment_score", 0) or 0)
        if bool(insight.get("purchase_signal")):
            metric["purchase_signal_count"] += 1
        metric["intent_counter"][_coerce_text(insight.get("intent_label")) or "unknown"] += 1
        metric["pain_counter"][_coerce_text(insight.get("pain_point_label")) or "none"] += 1

        tags = [tag for tag in _coerce_text(insight.get("topic_tags")).split("|") if tag]
        for tag in tags:
            topics_group[(key[0], key[1], key[2], tag)] += 1

    comment_metrics: list[dict[str, Any]] = []
    for (run_id, platform, canonical_content_id), metric in metrics_group.items():
        count = max(1, int(metric["comments_analyzed"]))
        intent = metric["intent_counter"].most_common(1)[0][0] if metric["intent_counter"] else "unknown"
        pain = metric["pain_counter"].most_common(1)[0][0] if metric["pain_counter"] else "none"
        row = {
            "run_id": run_id,
            "platform": platform,
            "canonical_content_id": canonical_content_id,
            "comments_analyzed": metric["comments_analyzed"],
            "positive_count": metric["positive_count"],
            "neutral_count": metric["neutral_count"],
            "negative_count": metric["negative_count"],
            "purchase_signal_count": metric["purchase_signal_count"],
            "avg_sentiment_score": round(metric["sentiment_sum"] / count, 4),
            "top_intent_label": intent,
            "top_pain_point_label": pain,
            "analyzed_at": analyzed_at,
        }
        comment_metrics.append({field: row.get(field, "") for field in COMMENT_METRICS_FIELDS})

    comment_topics: list[dict[str, Any]] = []
    for (run_id, platform, canonical_content_id, topic_tag), mentions in sorted(topics_group.items()):
        row = {
            "run_id": run_id,
            "platform": platform,
            "canonical_content_id": canonical_content_id,
            "topic_tag": topic_tag,
            "mentions": mentions,
            "analyzed_at": analyzed_at,
        }
        comment_topics.append({field: row.get(field, "") for field in COMMENT_TOPICS_FIELDS})

    return insights, comment_metrics, comment_topics
