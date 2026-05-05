from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
import json
from typing import Any

from .models import OUTREACH_RECORD_FIELDS


OUTREACH_CANDIDATE_FIELDS = [
    "run_id",
    "platform",
    "canonical_creator_id",
    "creator_handle",
    "creator_name",
    "score_total",
    "recommended_action",
    "campaign_id",
    "owner",
    "status",
    "draft_path",
    "notes",
    "created_at",
]


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def build_outreach_candidates(
    *,
    run_id: str,
    creator_scores: list[dict[str, Any]],
    campaign_id: str,
    owner: str,
    default_status: str = "pending_review",
    notes: str = "",
) -> list[dict[str, Any]]:
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    candidates: list[dict[str, Any]] = []
    for score in creator_scores:
        row = {
            "run_id": run_id,
            "platform": _coerce_text(score.get("platform")) or "tiktok",
            "canonical_creator_id": _coerce_text(score.get("canonical_creator_id")),
            "creator_handle": _coerce_text(score.get("creator_handle")),
            "creator_name": _coerce_text(score.get("creator_name")),
            "score_total": score.get("score_total", 0),
            "recommended_action": _coerce_text(score.get("recommended_action")),
            "campaign_id": campaign_id,
            "owner": owner,
            "status": default_status,
            "draft_path": "",
            "notes": notes,
            "created_at": created_at,
        }
        candidates.append({field: row.get(field, "") for field in OUTREACH_CANDIDATE_FIELDS})
    return candidates


def sync_outreach_state(
    *,
    operator_state_root: Path,
    outreach_candidates: list[dict[str, Any]],
    run_id: str,
    campaign_id: str,
) -> dict[str, Any]:
    registry_path = operator_state_root / "outreach_registry.csv"
    history_path = operator_state_root / "outreach_history.jsonl"
    operator_state_root.mkdir(parents=True, exist_ok=True)

    existing_rows = _read_csv_rows(registry_path)
    existing_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in existing_rows:
        key = (
            _coerce_text(row.get("platform")),
            _coerce_text(row.get("canonical_creator_id")),
            _coerce_text(row.get("campaign_id")),
        )
        existing_map[key] = row

    now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    updates = 0
    inserts = 0
    history_events: list[dict[str, Any]] = []

    for candidate in outreach_candidates:
        key = (
            _coerce_text(candidate.get("platform")),
            _coerce_text(candidate.get("canonical_creator_id")),
            _coerce_text(candidate.get("campaign_id")) or campaign_id,
        )
        existing = existing_map.get(key)

        if existing:
            existing["creator_handle"] = _coerce_text(candidate.get("creator_handle")) or existing.get("creator_handle", "")
            existing["creator_name"] = _coerce_text(candidate.get("creator_name")) or existing.get("creator_name", "")
            existing["owner"] = _coerce_text(candidate.get("owner")) or existing.get("owner", "")
            existing["status"] = _coerce_text(candidate.get("status")) or existing.get("status", "")
            existing["draft_path"] = _coerce_text(candidate.get("draft_path")) or existing.get("draft_path", "")
            existing["notes"] = _coerce_text(candidate.get("notes")) or existing.get("notes", "")
            existing["latest_run_id"] = run_id
            existing["latest_score_total"] = candidate.get("score_total", existing.get("latest_score_total", ""))
            existing["updated_at"] = now_iso
            existing["first_seen_at"] = existing.get("first_seen_at") or now_iso
            updates += 1
            operation = "updated"
        else:
            new_row = {
                "platform": key[0],
                "canonical_creator_id": key[1],
                "campaign_id": key[2],
                "creator_handle": _coerce_text(candidate.get("creator_handle")),
                "creator_name": _coerce_text(candidate.get("creator_name")),
                "owner": _coerce_text(candidate.get("owner")),
                "status": _coerce_text(candidate.get("status")),
                "draft_path": _coerce_text(candidate.get("draft_path")),
                "notes": _coerce_text(candidate.get("notes")),
                "latest_run_id": run_id,
                "latest_score_total": candidate.get("score_total", ""),
                "created_at": now_iso,
                "updated_at": now_iso,
                "first_seen_at": now_iso,
                "last_contacted_at": "",
                "last_replied_at": "",
                "closed_at": "",
                "outcome_code": "",
                "outcome_note": "",
            }
            existing_map[key] = new_row
            inserts += 1
            operation = "inserted"

        history_events.append(
            {
                "timestamp": now_iso,
                "operation": operation,
                "run_id": run_id,
                "campaign_id": key[2],
                "platform": key[0],
                "canonical_creator_id": key[1],
                "creator_handle": _coerce_text(candidate.get("creator_handle")),
                "status": _coerce_text(candidate.get("status")),
                "score_total": candidate.get("score_total", ""),
            }
        )

    final_rows = sorted(
        (
            {field: row.get(field, "") for field in OUTREACH_RECORD_FIELDS}
            for row in existing_map.values()
        ),
        key=lambda row: (row["campaign_id"], row["platform"], row["canonical_creator_id"]),
    )
    _write_csv_rows(registry_path, final_rows, OUTREACH_RECORD_FIELDS)

    with history_path.open("a", encoding="utf-8") as handle:
        for event in history_events:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    return {
        "registryPath": registry_path.as_posix(),
        "historyPath": history_path.as_posix(),
        "registryCount": len(final_rows),
        "inserts": inserts,
        "updates": updates,
        "historyEvents": len(history_events),
    }
