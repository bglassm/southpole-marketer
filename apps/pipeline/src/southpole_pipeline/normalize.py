from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any
from zoneinfo import ZoneInfo

from .models import (
    build_raw_ref,
    COMMENT_ITEM_FIELDS,
    CONTENT_ITEM_FIELDS,
    canonical_comment_id,
    canonical_content_id,
    canonical_creator_id,
)


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        if isinstance(value, bool):
            return int(value)
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _from_unix(value: int | float) -> datetime:
    if value > 10_000_000_000:
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        return _from_unix(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return _from_unix(int(text))
        text = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


def _extract_hashtags(record: dict[str, Any]) -> list[str]:
    raw_hashtags = record.get("hashtags") or []
    tags: list[str] = []
    if isinstance(raw_hashtags, list):
        for item in raw_hashtags:
            if isinstance(item, str):
                tags.append(item.lstrip("#"))
            elif isinstance(item, dict):
                maybe_name = item.get("name") or item.get("hashtagName")
                if maybe_name:
                    tags.append(str(maybe_name).lstrip("#"))
    return [tag for tag in tags if tag]


def _pick_keyword(
    keywords: list[str],
    text: str,
    hashtags: list[str],
    fallback_index: int,
) -> tuple[str, list[str]]:
    haystack = f"{text.lower()} {' '.join(hashtags).lower()}"
    matched = [keyword for keyword in keywords if keyword.lower() in haystack]
    if matched:
        return matched[0], matched
    fallback = keywords[min(fallback_index, len(keywords) - 1)]
    return fallback, []


def _candidate(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _music_title(record: dict[str, Any]) -> str:
    if isinstance(record.get("musicMeta"), str):
        return str(record["musicMeta"])
    if isinstance(record.get("musicMeta"), dict):
        return str(record.get("musicMeta", {}).get("musicName") or "")
    return ""


def normalize_records(
    records: list[dict[str, Any]],
    keywords: list[str],
    run_id: str,
    collected_at: datetime,
    days: int,
    local_tz: ZoneInfo,
) -> list[dict[str, Any]]:
    cutoff = collected_at - timedelta(days=days)
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for idx, record in enumerate(records):
        text = str(_candidate(record, "text", "desc", "description", "caption") or "")
        hashtags = _extract_hashtags(record)
        keyword, matched_keywords = _pick_keyword(keywords, text, hashtags, idx)

        created_at = _parse_datetime(
            _candidate(record, "createTimeISO", "createTime", "createdAt", "timestamp")
        )
        if created_at and created_at < cutoff:
            continue

        post_id = str(
            _candidate(record, "id", "postId", "awemeId", "videoId")
            or hashlib.sha1(
                f"{text}|{_candidate(record, 'webVideoUrl', 'url', 'videoUrl')}".encode("utf-8")
            ).hexdigest()[:16]
        )
        post_url = str(_candidate(record, "webVideoUrl", "url", "videoUrl", "postUrl") or "")

        author_meta = record.get("authorMeta") if isinstance(record.get("authorMeta"), dict) else {}
        creator_handle = str(
            _candidate(
                author_meta,
                "name",
                "nickName",
                "uniqueId",
                "id",
            )
            or _candidate(record, "authorUsername", "authorName", "username")
            or "unknown"
        )
        creator_id = str(_candidate(author_meta, "id", "secUid") or "")
        creator_name = str(_candidate(author_meta, "nickName", "name") or "")
        creator_url = str(_candidate(author_meta, "profileUrl", "url") or "")
        creator_followers = _coerce_int(
            _candidate(
                author_meta,
                "fans",
                "fansCount",
                "followerCount",
                "followers",
                "followersCount",
            )
            or _candidate(
                record,
                "authorFollowers",
                "authorFollowerCount",
                "followerCount",
                "followers",
                "followersCount",
            )
        )

        views = _coerce_int(
            _candidate(record, "playCount", "views")
            or (record.get("stats", {}).get("playCount") if isinstance(record.get("stats"), dict) else None)
        )
        likes = _coerce_int(
            _candidate(record, "diggCount", "likes")
            or (record.get("stats", {}).get("diggCount") if isinstance(record.get("stats"), dict) else None)
        )
        comments = _coerce_int(
            _candidate(record, "commentCount", "comments")
            or (record.get("stats", {}).get("commentCount") if isinstance(record.get("stats"), dict) else None)
        )
        shares = _coerce_int(
            _candidate(record, "shareCount", "shares")
            or (record.get("stats", {}).get("shareCount") if isinstance(record.get("stats"), dict) else None)
        )
        bookmarks = _coerce_int(_candidate(record, "collectCount", "bookmarks"))

        if created_at is None:
            created_at = collected_at

        local_date = created_at.astimezone(local_tz).date().isoformat()
        key = (keyword, post_id)
        if key in seen:
            continue
        seen.add(key)

        normalized.append(
            {
                "runId": run_id,
                "collectedAt": collected_at.isoformat(),
                "keyword": keyword,
                "matchedKeywords": "|".join(matched_keywords),
                "source": "apify:clockworks/tiktok-scraper",
                "sourceRecordId": str(_candidate(record, "id", "itemId") or post_id),
                "platform": "tiktok",
                "postId": post_id,
                "postUrl": post_url,
                "createTime": created_at.isoformat(),
                "date": local_date,
                "creatorId": creator_id,
                "creatorHandle": creator_handle,
                "creatorName": creator_name,
                "creatorUrl": creator_url,
                "creatorFollowers": creator_followers,
                "description": text,
                "hashtags": "|".join(hashtags),
                "musicTitle": _music_title(record),
                "region": str(_candidate(record, "region", "locationCreated", "countryCode") or ""),
                "language": str(_candidate(record, "language") or ""),
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "bookmarks": bookmarks,
                "engagements": likes + comments + shares,
                "raw": record,
            }
        )

    return normalized


def normalize_content_records(
    *,
    records: list[dict[str, Any]],
    keywords: list[str],
    run_id: str,
    collected_at: datetime,
    days: int,
    local_tz: ZoneInfo,
    raw_rel_path: str = "raw/source_items.jsonl",
) -> list[dict[str, Any]]:
    cutoff = collected_at - timedelta(days=days)
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for idx, record in enumerate(records, start=1):
        text = str(_candidate(record, "text", "desc", "description", "caption") or "")
        hashtags = _extract_hashtags(record)
        keyword, matched_keywords = _pick_keyword(keywords, text, hashtags, idx - 1)

        published_dt = _parse_datetime(
            _candidate(record, "createTimeISO", "createTime", "createdAt", "timestamp")
        )
        if published_dt and published_dt < cutoff:
            continue
        if published_dt is None:
            published_dt = collected_at

        platform = str(_candidate(record, "platform") or "tiktok")
        content_type = str(_candidate(record, "contentType", "type") or "video")
        platform_content_id = str(
            _candidate(record, "id", "postId", "awemeId", "videoId")
            or hashlib.sha1(
                f"{text}|{_candidate(record, 'webVideoUrl', 'url', 'videoUrl')}".encode("utf-8")
            ).hexdigest()[:16]
        )
        content_url = str(_candidate(record, "webVideoUrl", "url", "videoUrl", "postUrl") or "")

        author_meta = record.get("authorMeta") if isinstance(record.get("authorMeta"), dict) else {}
        creator_handle = str(
            _candidate(author_meta, "name", "nickName", "uniqueId", "id")
            or _candidate(record, "authorUsername", "authorName", "username")
            or "unknown"
        )
        platform_creator_id = str(_candidate(author_meta, "id", "secUid") or "")
        creator_name = str(_candidate(author_meta, "nickName", "name") or "")
        creator_profile_url = str(_candidate(author_meta, "profileUrl", "url") or "")
        creator_followers = _coerce_int(
            _candidate(author_meta, "fans", "fansCount", "followerCount", "followers", "followersCount")
            or _candidate(
                record,
                "authorFollowers",
                "authorFollowerCount",
                "followerCount",
                "followers",
                "followersCount",
            )
        )

        views = _coerce_int(
            _candidate(record, "playCount", "views")
            or (record.get("stats", {}).get("playCount") if isinstance(record.get("stats"), dict) else None)
        )
        likes = _coerce_int(
            _candidate(record, "diggCount", "likes")
            or (record.get("stats", {}).get("diggCount") if isinstance(record.get("stats"), dict) else None)
        )
        comments_count = _coerce_int(
            _candidate(record, "commentCount", "comments")
            or (record.get("stats", {}).get("commentCount") if isinstance(record.get("stats"), dict) else None)
        )
        shares = _coerce_int(
            _candidate(record, "shareCount", "shares")
            or (record.get("stats", {}).get("shareCount") if isinstance(record.get("stats"), dict) else None)
        )
        saves = _coerce_int(_candidate(record, "collectCount", "bookmarks", "saves"))

        canonical_creator = canonical_creator_id(
            platform=platform,
            platform_creator_id=platform_creator_id,
            creator_handle=creator_handle,
            creator_profile_url=creator_profile_url,
            creator_name=creator_name,
        )
        canonical_content = canonical_content_id(
            platform=platform,
            platform_content_id=platform_content_id,
            content_url=content_url,
            creator_handle=creator_handle,
            published_at=published_dt.isoformat(),
            text=text,
        )

        dedupe_key = (keyword, canonical_content)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        row = {
            "run_id": run_id,
            "platform": platform,
            "content_type": content_type,
            "keyword": keyword,
            "matched_keywords": "|".join(matched_keywords),
            "source": "apify:clockworks/tiktok-scraper",
            "source_record_id": str(_candidate(record, "id", "itemId") or platform_content_id),
            "raw_ref": build_raw_ref(raw_rel_path, idx),
            "platform_content_id": platform_content_id,
            "canonical_content_id": canonical_content,
            "platform_creator_id": platform_creator_id,
            "canonical_creator_id": canonical_creator,
            "creator_handle": creator_handle,
            "creator_name": creator_name,
            "creator_profile_url": creator_profile_url,
            "creator_followers": creator_followers,
            "content_url": content_url,
            "published_at": published_dt.isoformat(),
            "local_date": published_dt.astimezone(local_tz).date().isoformat(),
            "text": text,
            "hashtags": "|".join(hashtags),
            "music_title": _music_title(record),
            "region": str(_candidate(record, "region", "locationCreated", "countryCode") or ""),
            "language": str(_candidate(record, "language") or ""),
            "views": views,
            "likes": likes,
            "comments_count": comments_count,
            "shares": shares,
            "saves": saves,
            "engagements": likes + comments_count + shares,
            "collected_at": collected_at.isoformat(),
        }
        normalized.append({field: row.get(field, "") for field in CONTENT_ITEM_FIELDS})

    return normalized


def normalize_comment_records(
    *,
    records: list[dict[str, Any]],
    run_id: str,
    collected_at: datetime,
    local_tz: ZoneInfo,
    raw_rel_path: str = "comments/raw_comments.jsonl",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for idx, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            continue
        target = record.get("__target") if isinstance(record.get("__target"), dict) else {}

        platform = str(_candidate(record, "platform") or target.get("platform") or "tiktok")
        content_type = str(_candidate(record, "contentType", "type") or target.get("content_type") or "video")

        platform_content_id = str(
            _candidate(record, "awemeId", "postId", "videoId", "contentId")
            or target.get("platform_content_id")
            or ""
        )
        canonical_content = str(target.get("canonical_content_id") or "")
        if not canonical_content:
            canonical_content = canonical_content_id(
                platform=platform,
                platform_content_id=platform_content_id,
                content_url=_candidate(record, "contentUrl", "postUrl", "url") or target.get("content_url"),
                creator_handle=target.get("creator_handle"),
                published_at=_candidate(record, "createTimeISO", "createTime", "publishedAt"),
                text=_candidate(record, "text", "comment", "content"),
            )

        platform_comment_id = str(_candidate(record, "id", "commentId", "cid") or "")
        author_meta = record.get("authorMeta") if isinstance(record.get("authorMeta"), dict) else {}
        author_handle = str(
            _candidate(author_meta, "name", "nickName", "uniqueId", "id")
            or _candidate(record, "authorUsername", "authorName", "username")
            or "unknown"
        )
        author_name = str(_candidate(author_meta, "nickName", "name") or "")
        author_platform_id = str(_candidate(author_meta, "id", "secUid", "uid") or "")
        author_canonical_id = canonical_creator_id(
            platform=platform,
            platform_creator_id=author_platform_id,
            creator_handle=author_handle,
            creator_name=author_name,
            creator_profile_url=_candidate(author_meta, "profileUrl", "url"),
        )

        owner_platform_id = str(
            target.get("platform_creator_id")
            or _candidate(record, "ownerAuthorId", "contentOwnerId")
            or ""
        )
        owner_canonical_id = str(target.get("canonical_creator_id") or "")
        if not owner_canonical_id:
            owner_canonical_id = canonical_creator_id(
                platform=platform,
                platform_creator_id=owner_platform_id,
                creator_handle=target.get("creator_handle"),
                creator_name=target.get("creator_name"),
                creator_profile_url=target.get("creator_profile_url"),
            )

        parent_platform_comment_id = str(_candidate(record, "parentCommentId", "replyToCommentId") or "")
        parent_canonical_comment_id = ""
        if parent_platform_comment_id:
            parent_canonical_comment_id = canonical_comment_id(
                platform=platform,
                platform_comment_id=parent_platform_comment_id,
                platform_content_id=platform_content_id,
                comment_author_handle=author_handle,
                published_at=_candidate(record, "createTimeISO", "createTime", "publishedAt"),
                text="",
            )

        published_dt = _parse_datetime(
            _candidate(record, "createTimeISO", "createTime", "publishedAt", "timestamp")
        )
        if published_dt is None:
            published_dt = collected_at.astimezone(local_tz)

        text = str(_candidate(record, "text", "comment", "content") or "")
        canonical_comment = canonical_comment_id(
            platform=platform,
            platform_comment_id=platform_comment_id,
            platform_content_id=platform_content_id,
            comment_author_handle=author_handle,
            published_at=published_dt.isoformat(),
            parent_platform_comment_id=parent_platform_comment_id,
            text=text,
        )
        if canonical_comment in seen:
            continue
        seen.add(canonical_comment)

        row = {
            "run_id": run_id,
            "platform": platform,
            "content_type": content_type,
            "source": str(record.get("__source") or "apify:tiktok-comments"),
            "source_record_id": str(_candidate(record, "id", "commentId", "cid") or canonical_comment),
            "raw_ref": build_raw_ref(raw_rel_path, idx),
            "platform_content_id": platform_content_id,
            "canonical_content_id": canonical_content,
            "platform_comment_id": platform_comment_id,
            "canonical_comment_id": canonical_comment,
            "content_owner_platform_creator_id": owner_platform_id,
            "content_owner_canonical_creator_id": owner_canonical_id,
            "comment_author_platform_creator_id": author_platform_id,
            "comment_author_canonical_creator_id": author_canonical_id,
            "comment_author_handle": author_handle,
            "comment_author_name": author_name,
            "parent_platform_comment_id": parent_platform_comment_id,
            "parent_canonical_comment_id": parent_canonical_comment_id,
            "published_at": published_dt.isoformat(),
            "text": text,
            "language": str(_candidate(record, "language", "textLanguage") or ""),
            "likes": _coerce_int(_candidate(record, "diggCount", "likes", "likeCount")),
            "reply_count": _coerce_int(_candidate(record, "replyCommentTotal", "replyCount", "replies")),
            "collected_at": collected_at.isoformat(),
        }
        normalized.append({field: row.get(field, "") for field in COMMENT_ITEM_FIELDS})

    return normalized
