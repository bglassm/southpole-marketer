from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import CREATOR_SCORE_FIELDS


SCORING_VERSION = "v0.1"


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(score: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, score))


def build_creator_comment_signals(
    *,
    content_items: list[dict[str, Any]],
    comment_insights: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    content_to_creator: dict[str, str] = {}
    for item in content_items:
        content_id = _coerce_text(item.get("canonical_content_id"))
        creator_id = _coerce_text(item.get("canonical_creator_id"))
        if content_id and creator_id:
            content_to_creator[content_id] = creator_id

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "comments_analyzed": 0,
            "positive_count": 0,
            "negative_count": 0,
            "purchase_signal_count": 0,
            "sentiment_sum": 0.0,
        }
    )
    for insight in comment_insights:
        content_id = _coerce_text(insight.get("canonical_content_id"))
        creator_id = content_to_creator.get(content_id, "")
        if not creator_id:
            continue
        row = grouped[creator_id]
        row["comments_analyzed"] += 1
        sentiment = _coerce_text(insight.get("sentiment_label"))
        if sentiment == "positive":
            row["positive_count"] += 1
        elif sentiment == "negative":
            row["negative_count"] += 1
        if str(insight.get("purchase_signal", "")).lower() in {"true", "1", "yes"}:
            row["purchase_signal_count"] += 1
        row["sentiment_sum"] += _coerce_float(insight.get("sentiment_score"), 0.0)
    return grouped


def score_creator_rows(
    *,
    run_id: str,
    creator_profiles: list[dict[str, Any]],
    creator_comment_signals: dict[str, dict[str, Any]] | None = None,
    scoring_version: str = SCORING_VERSION,
) -> list[dict[str, Any]]:
    creator_comment_signals = creator_comment_signals or {}
    scored_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    rows: list[dict[str, Any]] = []

    for profile in creator_profiles:
        canonical_creator_id = _coerce_text(profile.get("canonical_creator_id"))
        comments = creator_comment_signals.get(canonical_creator_id, {})

        posts = max(1.0, _coerce_float(profile.get("posts"), 1.0))
        avg_views = _coerce_float(profile.get("avg_views"), 0.0)
        engagement_rate = _coerce_float(profile.get("engagement_rate_by_views"), 0.0)
        keyword_count = len([k for k in _coerce_text(profile.get("keywords")).split("|") if k])

        comments_analyzed = int(comments.get("comments_analyzed", 0) or 0)
        positive_count = int(comments.get("positive_count", 0) or 0)
        negative_count = int(comments.get("negative_count", 0) or 0)
        purchase_signal_count = int(comments.get("purchase_signal_count", 0) or 0)
        if comments_analyzed > 0:
            positive_ratio = positive_count / comments_analyzed
            negative_ratio = negative_count / comments_analyzed
            purchase_ratio = purchase_signal_count / comments_analyzed
        else:
            positive_ratio = 0.5
            negative_ratio = 0.1
            purchase_ratio = 0.0

        score_content_fit = _clamp(55 + (keyword_count * 8))
        score_engagement = _clamp((engagement_rate * 450) + min(35.0, avg_views / 4000))
        score_consistency = _clamp(min(70.0, posts * 12.0) + min(30.0, avg_views / 6000))
        score_comment_quality = _clamp((positive_ratio * 100) - (negative_ratio * 40))
        score_purchase_signal = _clamp((purchase_ratio * 100) + min(20.0, purchase_signal_count * 5.0))
        score_risk = _clamp((negative_ratio * 100) + (15.0 if comments_analyzed == 0 else 0.0))

        total = _clamp(
            (0.23 * score_content_fit)
            + (0.2 * score_comment_quality)
            + (0.18 * score_purchase_signal)
            + (0.22 * score_engagement)
            + (0.17 * score_consistency)
            - (0.1 * score_risk)
        )

        if total >= 75:
            action = "prioritize_outreach"
        elif total >= 55:
            action = "review_manually"
        else:
            action = "hold"

        reason_summary = (
            f"fit={round(score_content_fit,1)}, engagement={round(score_engagement,1)}, "
            f"comment_quality={round(score_comment_quality,1)}, purchase={round(score_purchase_signal,1)}, "
            f"risk={round(score_risk,1)}"
        )

        scored = {
            "run_id": run_id,
            "platform": _coerce_text(profile.get("platform")) or "tiktok",
            "canonical_creator_id": canonical_creator_id,
            "creator_handle": _coerce_text(profile.get("creator_handle")),
            "creator_name": _coerce_text(profile.get("creator_name")),
            "score_total": round(total, 2),
            "score_content_fit": round(score_content_fit, 2),
            "score_comment_quality": round(score_comment_quality, 2),
            "score_purchase_signal": round(score_purchase_signal, 2),
            "score_engagement": round(score_engagement, 2),
            "score_consistency": round(score_consistency, 2),
            "score_risk": round(score_risk, 2),
            "reason_summary": reason_summary,
            "recommended_action": action,
            "scoring_version": scoring_version,
            "scored_at": scored_at,
        }
        rows.append({field: scored.get(field, "") for field in CREATOR_SCORE_FIELDS})

    return sorted(rows, key=lambda row: float(row.get("score_total", 0) or 0), reverse=True)
