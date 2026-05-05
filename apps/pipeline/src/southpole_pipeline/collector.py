from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import requests

from .config import Settings


class CollectorError(RuntimeError):
    pass


def _actor_path(actor_id: str) -> str:
    return actor_id.replace("/", "~")


def _build_actor_input(keywords: list[str], settings: Settings) -> dict[str, Any]:
    hashtag_keywords = [
        keyword.lstrip("#").replace(" ", "")
        for keyword in keywords
        if keyword.strip()
    ]

    payload: dict[str, Any] = {
        "excludePinnedPosts": True,
        "resultsPerPage": settings.apify_results_per_page,
        "proxyCountryCode": settings.apify_proxy_country_code,
    }

    if hashtag_keywords:
        payload["hashtags"] = hashtag_keywords
    payload["searchQueries"] = keywords
    return payload


def _parse_items(response: requests.Response) -> list[dict[str, Any]]:
    payload = response.json()
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    raise CollectorError("Apify response did not contain a list of records.")


def collect_from_apify(
    keywords: list[str],
    settings: Settings,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not settings.apify_token:
        raise CollectorError("APIFY_TOKEN is not set.")

    actor_path = _actor_path(settings.apify_actor_id)
    url = f"{settings.apify_base_url}/acts/{actor_path}/run-sync-get-dataset-items"

    params = {
        "token": settings.apify_token,
        "timeout": settings.apify_timeout_seconds,
        "clean": "true",
    }

    base_input = _build_actor_input(keywords, settings)
    fallback_inputs = [
        base_input,
        {k: v for k, v in base_input.items() if k != "searchQueries"},
        {
            "hashtags": base_input.get("hashtags", []),
            "resultsPerPage": settings.apify_results_per_page,
            "proxyCountryCode": settings.apify_proxy_country_code,
        },
    ]

    last_error = ""
    for actor_input in fallback_inputs:
        response = requests.post(
            url,
            params=params,
            json=actor_input,
            timeout=settings.apify_timeout_seconds + 20,
        )
        if response.ok:
            items = _parse_items(response)
            source_meta = {
                "provider": "apify",
                "actorId": settings.apify_actor_id,
                "actorInput": actor_input,
                "actorRunId": response.headers.get("x-apify-actor-run-id"),
                "datasetId": response.headers.get("x-apify-dataset-id"),
            }
            return items, source_meta

        last_error = f"Apify request failed ({response.status_code}): {response.text[:500]}"
        if response.status_code in (401, 403):
            break

    raise CollectorError(last_error)


def load_mock_records(mock_file: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    file_path = Path(mock_file)
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CollectorError("Mock file must contain a JSON array.")
    records = [item for item in raw if isinstance(item, dict)]
    return records, {
        "provider": "mock",
        "mockFile": str(file_path),
    }


def _build_comment_actor_inputs(content_url: str, requested_limit: int) -> list[dict[str, Any]]:
    safe_limit = max(1, int(requested_limit or 0))
    return [
        {
            "postURLs": [content_url],
            "resultsLimit": safe_limit,
        },
        {
            "startUrls": [{"url": content_url}],
            "maxComments": safe_limit,
        },
        {
            "url": content_url,
            "maxItems": safe_limit,
        },
    ]


def collect_tiktok_comments_from_targets(
    *,
    comment_targets: list[dict[str, Any]],
    settings: Settings,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    actor_id = settings.apify_tiktok_comments_actor_id.strip()
    if not actor_id:
        raise CollectorError(
            "APIFY_TIKTOK_COMMENTS_ACTOR_ID is not set. Configure it before running comment collection."
        )
    if not settings.apify_token:
        raise CollectorError("APIFY_TOKEN is not set.")

    actor_path = _actor_path(actor_id)
    url = f"{settings.apify_base_url}/acts/{actor_path}/run-sync-get-dataset-items"
    params = {
        "token": settings.apify_token,
        "timeout": settings.apify_timeout_seconds,
        "clean": "true",
    }

    all_records: list[dict[str, Any]] = []
    attempts_meta: list[dict[str, Any]] = []

    for target in comment_targets:
        content_url = str(target.get("content_url") or "").strip()
        if not content_url:
            continue
        requested_limit = int(target.get("requested_comment_limit", 20) or 20)
        target_payload = {
            "platform_content_id": str(target.get("platform_content_id", "")),
            "canonical_content_id": str(target.get("canonical_content_id", "")),
            "platform_creator_id": str(target.get("platform_creator_id", "")),
            "canonical_creator_id": str(target.get("canonical_creator_id", "")),
            "creator_handle": str(target.get("creator_handle", "")),
            "content_url": content_url,
            "content_type": str(target.get("content_type", "video")),
            "platform": str(target.get("platform", "tiktok")),
            "keyword": str(target.get("keyword", "")),
        }

        last_error = ""
        for actor_input in _build_comment_actor_inputs(content_url, requested_limit):
            response = requests.post(
                url,
                params=params,
                json=actor_input,
                timeout=settings.apify_timeout_seconds + 20,
            )
            if response.ok:
                items = _parse_items(response)
                for item in items:
                    item["__target"] = target_payload
                    item["__source"] = f"apify:{actor_id}"
                all_records.extend(items)
                attempts_meta.append(
                    {
                        "contentUrl": content_url,
                        "actorInput": actor_input,
                        "recordCount": len(items),
                        "actorRunId": response.headers.get("x-apify-actor-run-id"),
                        "datasetId": response.headers.get("x-apify-dataset-id"),
                    }
                )
                break

            last_error = f"Apify comment request failed ({response.status_code}): {response.text[:500]}"
            if response.status_code in (401, 403):
                raise CollectorError(last_error)
        else:
            raise CollectorError(
                f"Failed to collect comments for target {content_url}. "
                f"Last error: {last_error or 'unknown'}"
            )

    source_meta = {
        "provider": "apify",
        "actorId": actor_id,
        "targetCount": len(comment_targets),
        "collectedRecordCount": len(all_records),
        "attempts": attempts_meta,
    }
    return all_records, source_meta


def load_mock_comment_records(mock_file: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    file_path = Path(mock_file)
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise CollectorError("Comment mock file must contain a JSON array.")
    records = [item for item in raw if isinstance(item, dict)]
    return records, {
        "provider": "mock",
        "mockFile": str(file_path),
        "mockType": "comments",
    }
