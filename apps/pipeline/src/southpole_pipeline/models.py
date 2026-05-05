from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import re
from typing import Iterable


CONTENT_ITEM_FIELDS = [
    "run_id",
    "platform",
    "content_type",
    "keyword",
    "matched_keywords",
    "source",
    "source_record_id",
    "raw_ref",
    "platform_content_id",
    "canonical_content_id",
    "platform_creator_id",
    "canonical_creator_id",
    "creator_handle",
    "creator_name",
    "creator_profile_url",
    "creator_followers",
    "content_url",
    "published_at",
    "local_date",
    "text",
    "hashtags",
    "music_title",
    "region",
    "language",
    "views",
    "likes",
    "comments_count",
    "shares",
    "saves",
    "engagements",
    "collected_at",
]

CREATOR_PROFILE_FIELDS = [
    "run_id",
    "platform",
    "platform_creator_id",
    "canonical_creator_id",
    "creator_handle",
    "creator_name",
    "creator_profile_url",
    "creator_followers",
    "keywords",
    "primary_keyword",
    "posts",
    "total_views",
    "total_likes",
    "total_comments",
    "total_shares",
    "avg_views",
    "avg_engagements",
    "engagement_rate_by_views",
    "first_seen_at",
    "last_seen_at",
    "top_platform_content_id",
    "top_canonical_content_id",
    "top_content_url",
]

COMMENT_TARGET_FIELDS = [
    "run_id",
    "selected_from_run_id",
    "platform",
    "content_type",
    "platform_content_id",
    "canonical_content_id",
    "platform_creator_id",
    "canonical_creator_id",
    "creator_handle",
    "content_url",
    "keyword",
    "selection_mode",
    "selection_reason",
    "selected_by",
    "selection_note",
    "requested_comment_limit",
    "selected_at",
]

COMMENT_ITEM_FIELDS = [
    "run_id",
    "platform",
    "content_type",
    "source",
    "source_record_id",
    "raw_ref",
    "platform_content_id",
    "canonical_content_id",
    "platform_comment_id",
    "canonical_comment_id",
    "content_owner_platform_creator_id",
    "content_owner_canonical_creator_id",
    "comment_author_platform_creator_id",
    "comment_author_canonical_creator_id",
    "comment_author_handle",
    "comment_author_name",
    "parent_platform_comment_id",
    "parent_canonical_comment_id",
    "published_at",
    "text",
    "language",
    "likes",
    "reply_count",
    "collected_at",
]

COMMENT_INSIGHT_FIELDS = [
    "run_id",
    "platform",
    "canonical_content_id",
    "canonical_comment_id",
    "sentiment_label",
    "sentiment_score",
    "intent_label",
    "pain_point_label",
    "pain_point_detail",
    "product_interest_label",
    "topic_tags",
    "purchase_signal",
    "confidence",
    "analysis_model",
    "analyzed_at",
]

CREATOR_SCORE_FIELDS = [
    "run_id",
    "platform",
    "canonical_creator_id",
    "creator_handle",
    "creator_name",
    "score_total",
    "score_content_fit",
    "score_comment_quality",
    "score_purchase_signal",
    "score_engagement",
    "score_consistency",
    "score_risk",
    "reason_summary",
    "recommended_action",
    "scoring_version",
    "scored_at",
]

OUTREACH_RECORD_FIELDS = [
    "platform",
    "canonical_creator_id",
    "campaign_id",
    "creator_handle",
    "creator_name",
    "owner",
    "status",
    "draft_path",
    "notes",
    "latest_run_id",
    "latest_score_total",
    "created_at",
    "updated_at",
    "first_seen_at",
    "last_contacted_at",
    "last_replied_at",
    "closed_at",
    "outcome_code",
    "outcome_note",
]


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _coerce_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_suffix(value: str, *, fallback_prefix: str = "id") -> str:
    text = _coerce_text(value).lower()
    if not text:
        return fallback_prefix
    suffix = _NON_ALNUM_RE.sub("-", text).strip("-")
    if not suffix:
        return fallback_prefix
    if len(suffix) > 72:
        suffix = suffix[:72].rstrip("-")
    return suffix


def stable_hash(parts: Iterable[object], length: int = 16) -> str:
    joined = "|".join(_coerce_text(part) for part in parts)
    return sha1(joined.encode("utf-8")).hexdigest()[:length]


def canonical_content_id(
    *,
    platform: str,
    platform_content_id: object | None,
    content_url: object | None = None,
    creator_handle: object | None = None,
    published_at: object | None = None,
    text: object | None = None,
) -> str:
    platform_name = _normalize_suffix(platform, fallback_prefix="platform")
    native = _coerce_text(platform_content_id)
    if native:
        suffix = _normalize_suffix(native, fallback_prefix=stable_hash([platform_name, native]))
        return f"{platform_name}:content:{suffix}"
    derived = stable_hash([platform_name, content_url, creator_handle, published_at, text])
    return f"{platform_name}:content:{derived}"


def canonical_creator_id(
    *,
    platform: str,
    platform_creator_id: object | None,
    creator_handle: object | None = None,
    creator_profile_url: object | None = None,
    creator_name: object | None = None,
) -> str:
    platform_name = _normalize_suffix(platform, fallback_prefix="platform")
    native = _coerce_text(platform_creator_id)
    if native:
        suffix = _normalize_suffix(native, fallback_prefix=stable_hash([platform_name, native]))
        return f"{platform_name}:creator:{suffix}"
    derived = stable_hash([platform_name, creator_handle, creator_profile_url, creator_name])
    return f"{platform_name}:creator:{derived}"


def canonical_comment_id(
    *,
    platform: str,
    platform_comment_id: object | None,
    platform_content_id: object | None = None,
    comment_author_handle: object | None = None,
    published_at: object | None = None,
    parent_platform_comment_id: object | None = None,
    text: object | None = None,
) -> str:
    platform_name = _normalize_suffix(platform, fallback_prefix="platform")
    native = _coerce_text(platform_comment_id)
    if native:
        suffix = _normalize_suffix(native, fallback_prefix=stable_hash([platform_name, native]))
        return f"{platform_name}:comment:{suffix}"
    derived = stable_hash(
        [
            platform_name,
            platform_content_id,
            comment_author_handle,
            published_at,
            parent_platform_comment_id,
            text,
        ]
    )
    return f"{platform_name}:comment:{derived}"


def build_raw_ref(relative_jsonl_path: str | Path, line_no: int) -> str:
    rel = Path(relative_jsonl_path).as_posix().lstrip("/")
    safe_line = max(1, int(line_no))
    return f"{rel}#L{safe_line}"
