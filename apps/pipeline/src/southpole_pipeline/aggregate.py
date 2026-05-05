from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import COMMENT_TARGET_FIELDS, CREATOR_PROFILE_FIELDS


def aggregate_keyword_totals(events: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for event in events:
        keyword = event["keyword"]
        row = grouped.setdefault(
            keyword,
            {
                "run_id": run_id,
                "keyword": keyword,
                "posts": 0,
                "creator_handles": set(),
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "first_post_at": None,
                "last_post_at": None,
                "top_creator_handle": "",
                "top_post_url": "",
                "top_post_views": 0,
            },
        )
        row["posts"] += 1
        row["creator_handles"].add(event["creatorHandle"])
        row["total_views"] += int(event["views"])
        row["total_likes"] += int(event["likes"])
        row["total_comments"] += int(event["comments"])
        row["total_shares"] += int(event["shares"])

        create_time = event["createTime"]
        row["first_post_at"] = min(filter(None, [row["first_post_at"], create_time]))
        row["last_post_at"] = max(filter(None, [row["last_post_at"], create_time]))

        if int(event["views"]) >= int(row["top_post_views"]):
            row["top_post_views"] = int(event["views"])
            row["top_post_url"] = event["postUrl"]
            row["top_creator_handle"] = event["creatorHandle"]

    result: list[dict[str, Any]] = []
    for row in grouped.values():
        posts = row["posts"] or 1
        engagements = row["total_likes"] + row["total_comments"] + row["total_shares"]
        total_views = row["total_views"]
        result.append(
            {
                "run_id": row["run_id"],
                "keyword": row["keyword"],
                "posts": row["posts"],
                "unique_creators": len(row["creator_handles"]),
                "total_views": row["total_views"],
                "total_likes": row["total_likes"],
                "total_comments": row["total_comments"],
                "total_shares": row["total_shares"],
                "avg_views": round(total_views / posts, 2),
                "avg_likes": round(row["total_likes"] / posts, 2),
                "avg_comments": round(row["total_comments"] / posts, 2),
                "avg_shares": round(row["total_shares"] / posts, 2),
                "engagements": engagements,
                "engagement_rate_by_views": round(engagements / total_views, 6) if total_views else 0,
                "first_post_at": row["first_post_at"] or "",
                "last_post_at": row["last_post_at"] or "",
                "top_creator_handle": row["top_creator_handle"],
                "top_post_url": row["top_post_url"],
                "top_post_views": row["top_post_views"],
            }
        )

    return sorted(result, key=lambda row: row["total_views"], reverse=True)


def aggregate_creators(events: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for event in events:
        key = event["creatorHandle"] or "unknown"
        row = grouped.setdefault(
            key,
            {
                "run_id": run_id,
                "creator_handle": key,
                "creator_id": event["creatorId"],
                "creator_name": event["creatorName"],
                "creator_url": event["creatorUrl"],
                "author_followers": 0,
                "posts": 0,
                "keywords": set(),
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "first_post_at": None,
                "last_post_at": None,
                "top_post_url": "",
                "top_post_description": "",
                "top_post_views": 0,
            },
        )

        row["posts"] += 1
        row["keywords"].add(event["keyword"])
        row["total_views"] += int(event["views"])
        row["total_likes"] += int(event["likes"])
        row["total_comments"] += int(event["comments"])
        row["total_shares"] += int(event["shares"])
        row["author_followers"] = max(row["author_followers"], int(event.get("creatorFollowers", 0) or 0))

        create_time = event["createTime"]
        row["first_post_at"] = min(filter(None, [row["first_post_at"], create_time]))
        row["last_post_at"] = max(filter(None, [row["last_post_at"], create_time]))

        if int(event["views"]) >= int(row["top_post_views"]):
            row["top_post_views"] = int(event["views"])
            row["top_post_url"] = event["postUrl"]
            row["top_post_description"] = event["description"]

    result: list[dict[str, Any]] = []
    for row in grouped.values():
        posts = row["posts"] or 1
        engagements = row["total_likes"] + row["total_comments"] + row["total_shares"]
        primary_keyword = sorted(row["keywords"])[0] if row["keywords"] else ""
        result.append(
            {
                "run_id": row["run_id"],
                "creator_handle": row["creator_handle"],
                "creator_id": row["creator_id"],
                "creator_name": row["creator_name"],
                "creator_url": row["creator_url"],
                "authorFollowers": row["author_followers"],
                "posts": row["posts"],
                "keywords": "|".join(sorted(row["keywords"])),
                "primary_keyword": primary_keyword,
                "total_views": row["total_views"],
                "total_likes": row["total_likes"],
                "total_comments": row["total_comments"],
                "total_shares": row["total_shares"],
                "avg_views": round(row["total_views"] / posts, 2),
                "avg_engagements": round(engagements / posts, 2),
                "engagement_rate_by_views": round(engagements / row["total_views"], 6)
                if row["total_views"]
                else 0,
                "first_post_at": row["first_post_at"] or "",
                "last_post_at": row["last_post_at"] or "",
                "top_post_url": row["top_post_url"],
                "top_post_description": row["top_post_description"],
                "top_post_views": row["top_post_views"],
                "contact_status": "",
                "notes": "",
            }
        )

    return sorted(result, key=lambda row: row["total_views"], reverse=True)


def aggregate_daily_metrics(events: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "posts": 0,
            "creator_handles": set(),
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
        }
    )

    for event in events:
        key = (event["date"], event["keyword"])
        row = grouped[key]
        row["posts"] += 1
        row["creator_handles"].add(event["creatorHandle"])
        row["total_views"] += int(event["views"])
        row["total_likes"] += int(event["likes"])
        row["total_comments"] += int(event["comments"])
        row["total_shares"] += int(event["shares"])

    result: list[dict[str, Any]] = []
    for (date, keyword), row in grouped.items():
        posts = row["posts"] or 1
        engagements = row["total_likes"] + row["total_comments"] + row["total_shares"]
        result.append(
            {
                "run_id": run_id,
                "date": date,
                "keyword": keyword,
                "posts": row["posts"],
                "unique_creators": len(row["creator_handles"]),
                "total_views": row["total_views"],
                "total_likes": row["total_likes"],
                "total_comments": row["total_comments"],
                "total_shares": row["total_shares"],
                "engagements": engagements,
                "avg_views": round(row["total_views"] / posts, 2),
                "avg_engagements": round(engagements / posts, 2),
            }
        )

    return sorted(result, key=lambda row: (row["date"], row["keyword"]))


def aggregate_creator_profiles(content_items: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for item in content_items:
        key = str(item.get("canonical_creator_id") or "")
        row = grouped.setdefault(
            key,
            {
                "run_id": run_id,
                "platform": item.get("platform", "tiktok"),
                "platform_creator_id": item.get("platform_creator_id", ""),
                "canonical_creator_id": item.get("canonical_creator_id", ""),
                "creator_handle": item.get("creator_handle", ""),
                "creator_name": item.get("creator_name", ""),
                "creator_profile_url": item.get("creator_profile_url", ""),
                "creator_followers": int(item.get("creator_followers", 0) or 0),
                "keywords": set(),
                "posts": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "first_seen_at": None,
                "last_seen_at": None,
                "top_platform_content_id": "",
                "top_canonical_content_id": "",
                "top_content_url": "",
                "top_content_views": 0,
            },
        )
        row["posts"] += 1
        row["keywords"].add(str(item.get("keyword", "")))
        row["total_views"] += int(item.get("views", 0) or 0)
        row["total_likes"] += int(item.get("likes", 0) or 0)
        row["total_comments"] += int(item.get("comments_count", 0) or 0)
        row["total_shares"] += int(item.get("shares", 0) or 0)
        row["creator_followers"] = max(row["creator_followers"], int(item.get("creator_followers", 0) or 0))

        published_at = str(item.get("published_at", "") or "")
        if published_at:
            row["first_seen_at"] = min(filter(None, [row["first_seen_at"], published_at]))
            row["last_seen_at"] = max(filter(None, [row["last_seen_at"], published_at]))

        views = int(item.get("views", 0) or 0)
        if views >= row["top_content_views"]:
            row["top_content_views"] = views
            row["top_platform_content_id"] = str(item.get("platform_content_id", ""))
            row["top_canonical_content_id"] = str(item.get("canonical_content_id", ""))
            row["top_content_url"] = str(item.get("content_url", ""))

    profiles: list[dict[str, Any]] = []
    for row in grouped.values():
        posts = row["posts"] or 1
        engagements = row["total_likes"] + row["total_comments"] + row["total_shares"]
        keyword_values = sorted(k for k in row["keywords"] if k)
        profile = {
            "run_id": row["run_id"],
            "platform": row["platform"],
            "platform_creator_id": row["platform_creator_id"],
            "canonical_creator_id": row["canonical_creator_id"],
            "creator_handle": row["creator_handle"],
            "creator_name": row["creator_name"],
            "creator_profile_url": row["creator_profile_url"],
            "creator_followers": row["creator_followers"],
            "keywords": "|".join(keyword_values),
            "primary_keyword": keyword_values[0] if keyword_values else "",
            "posts": row["posts"],
            "total_views": row["total_views"],
            "total_likes": row["total_likes"],
            "total_comments": row["total_comments"],
            "total_shares": row["total_shares"],
            "avg_views": round(row["total_views"] / posts, 2),
            "avg_engagements": round(engagements / posts, 2),
            "engagement_rate_by_views": round(engagements / row["total_views"], 6)
            if row["total_views"]
            else 0,
            "first_seen_at": row["first_seen_at"] or "",
            "last_seen_at": row["last_seen_at"] or "",
            "top_platform_content_id": row["top_platform_content_id"],
            "top_canonical_content_id": row["top_canonical_content_id"],
            "top_content_url": row["top_content_url"],
        }
        profiles.append({field: profile.get(field, "") for field in CREATOR_PROFILE_FIELDS})

    return sorted(profiles, key=lambda row: row["total_views"], reverse=True)


def build_comment_targets(
    *,
    run_id: str,
    content_items: list[dict[str, Any]],
    selected_from_run_id: str,
    selection_mode: str,
    selected_by: str,
    selection_note: str,
    requested_comment_limit: int,
    max_targets: int,
) -> list[dict[str, Any]]:
    sorted_items = sorted(content_items, key=lambda row: int(row.get("views", 0) or 0), reverse=True)
    selected_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    targets: list[dict[str, Any]] = []
    for index, item in enumerate(sorted_items[: max(1, int(max_targets))], start=1):
        reason = (
            f"Ranked #{index} by views ({item.get('views', 0)}) in run {selected_from_run_id}"
            if selection_mode == "top_by_views"
            else f"Selected by mode={selection_mode}"
        )
        target_row = {
            "run_id": run_id,
            "selected_from_run_id": selected_from_run_id,
            "platform": item.get("platform", "tiktok"),
            "content_type": item.get("content_type", "video"),
            "platform_content_id": item.get("platform_content_id", ""),
            "canonical_content_id": item.get("canonical_content_id", ""),
            "platform_creator_id": item.get("platform_creator_id", ""),
            "canonical_creator_id": item.get("canonical_creator_id", ""),
            "creator_handle": item.get("creator_handle", ""),
            "content_url": item.get("content_url", ""),
            "keyword": item.get("keyword", ""),
            "selection_mode": selection_mode,
            "selection_reason": reason,
            "selected_by": selected_by,
            "selection_note": selection_note,
            "requested_comment_limit": max(1, int(requested_comment_limit)),
            "selected_at": selected_at,
        }
        targets.append({field: target_row.get(field, "") for field in COMMENT_TARGET_FIELDS})

    return targets
