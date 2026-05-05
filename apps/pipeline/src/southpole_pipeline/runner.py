from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import csv
import json
from typing import Any

from .aggregate import (
    aggregate_creator_profiles,
    aggregate_creators,
    aggregate_daily_metrics,
    aggregate_keyword_totals,
    build_comment_targets,
)
from .collector import (
    collect_from_apify,
    collect_tiktok_comments_from_targets,
    load_mock_comment_records,
    load_mock_records,
)
from .comment_analysis import COMMENT_METRICS_FIELDS, COMMENT_TOPICS_FIELDS, analyze_comment_items
from .config import Settings, load_settings
from .models import (
    COMMENT_INSIGHT_FIELDS,
    COMMENT_ITEM_FIELDS,
    COMMENT_TARGET_FIELDS,
    CONTENT_ITEM_FIELDS,
    CREATOR_PROFILE_FIELDS,
    CREATOR_SCORE_FIELDS,
)
from .normalize import normalize_comment_records, normalize_content_records, normalize_records
from .outreach_state import OUTREACH_CANDIDATE_FIELDS, build_outreach_candidates, sync_outreach_state
from .scoring import build_creator_comment_signals, score_creator_rows
from .utils import compact_timestamp, ensure_unique_run_dir, parse_keywords, run_timestamp, slugify, write_json
from .writers import (
    write_raw_csv,
    write_raw_jsonl,
    write_report_html,
    write_table_csv,
    write_workbook,
)


def _relative_to_repo(path: Path) -> str:
    path_str = path.as_posix()
    marker = "/outputs/"
    if marker in path_str:
        return "outputs/" + path_str.split(marker, 1)[1]
    return path_str


def _latest_run_dir(output_root: Path) -> Path:
    if not output_root.exists():
        raise ValueError(f"Run output root does not exist: {output_root}")
    run_dirs = sorted([path for path in output_root.iterdir() if path.is_dir()], key=lambda p: p.name)
    if not run_dirs:
        raise ValueError(f"No run directories found under: {output_root}")
    return run_dirs[-1]


def _resolve_run_dir(run_ref: str | None, settings: Settings) -> Path:
    if not run_ref:
        return _latest_run_dir(settings.output_root)

    candidate = Path(run_ref).expanduser()
    if candidate.is_absolute() and candidate.exists():
        return candidate

    if not candidate.is_absolute() and candidate.exists():
        return candidate.resolve()

    if not candidate.is_absolute():
        candidate_str = candidate.as_posix().lstrip("/")
        if candidate_str.startswith("outputs/runs/"):
            mapped = settings.output_root / candidate_str[len("outputs/runs/") :]
            if mapped.exists():
                return mapped.resolve()
        joined = (settings.output_root / candidate).resolve()
        if joined.exists():
            return joined

    marker = "/outputs/runs/"
    candidate_str = candidate.as_posix()
    if marker in candidate_str:
        translated = settings.output_root / candidate_str.split(marker, 1)[1]
        if translated.exists():
            return translated

    raise ValueError(f"Run directory does not exist: {run_ref}")


def _read_table_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _summary_payload(
    *,
    run_id: str,
    run_dir: Path,
    started_at: datetime,
    finished_at: datetime,
    keywords: list[str],
    days: int,
    source: str,
    settings: Settings,
    source_meta: dict[str, Any],
    events: list[dict[str, Any]],
    keyword_totals: list[dict[str, Any]],
    creators: list[dict[str, Any]],
    daily_metrics: list[dict[str, Any]],
    content_items: list[dict[str, Any]],
    creator_profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    files = {
        "runDir": _relative_to_repo(run_dir),
        "rawEventsJsonl": _relative_to_repo(run_dir / "raw_events.jsonl"),
        "rawEventsCsv": _relative_to_repo(run_dir / "raw_events.csv"),
        "keywordTotalsCsv": _relative_to_repo(run_dir / "keyword_totals.csv"),
        "creatorsCsv": _relative_to_repo(run_dir / "creators.csv"),
        "dailyMetricsCsv": _relative_to_repo(run_dir / "daily_metrics.csv"),
        "reportHtml": _relative_to_repo(run_dir / "report.html"),
        "workbook": _relative_to_repo(next(run_dir.glob("southpole_run_*.xlsx"))),
        "sourceItemsJsonl": _relative_to_repo(run_dir / "raw/source_items.jsonl"),
        "contentItemsCsv": _relative_to_repo(run_dir / "normalized/content_items.csv"),
        "creatorProfilesCsv": _relative_to_repo(run_dir / "normalized/creator_profiles.csv"),
    }
    return {
        "runId": run_id,
        "buildTag": settings.build_tag,
        "status": "completed",
        "startedAt": started_at.isoformat(),
        "finishedAt": finished_at.isoformat(),
        "parameters": {
            "keywords": keywords,
            "days": days,
            "timezone": settings.timezone_name,
            "source": source,
        },
        "counts": {
            "rawEvents": len(events),
            "keywordRows": len(keyword_totals),
            "creatorRows": len(creators),
            "dailyMetricRows": len(daily_metrics),
            "contentItemRows": len(content_items),
            "creatorProfileRows": len(creator_profiles),
        },
        "source": source_meta,
        "files": files,
        "futureDmInput": {
            "creatorsCsv": files["creatorsCsv"],
            "summaryJson": _relative_to_repo(run_dir / "summary.json"),
        },
    }


def _extend_summary(
    *,
    run_dir: Path,
    file_updates: dict[str, str] | None = None,
    count_updates: dict[str, Any] | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {
            "runId": run_dir.name,
            "status": "completed",
            "files": {"runDir": _relative_to_repo(run_dir)},
            "counts": {},
        }

    summary.setdefault("files", {})
    summary.setdefault("counts", {})
    if file_updates:
        summary["files"].update(file_updates)
    if count_updates:
        summary["counts"].update(count_updates)
    if stage:
        summary.setdefault("stages", {})
        summary["stages"][stage] = {"updatedAt": datetime.utcnow().replace(microsecond=0).isoformat() + "Z"}

    summary["updatedAt"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    write_json(summary_path, summary)
    return summary


def _write_comment_report_html(
    *,
    path: Path,
    run_id: str,
    comment_metrics: list[dict[str, Any]],
    comment_topics: list[dict[str, Any]],
) -> None:
    metrics_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('canonical_content_id', '')))}</td>"
        f"<td>{escape(str(row.get('comments_analyzed', '')))}</td>"
        f"<td>{escape(str(row.get('positive_count', '')))}</td>"
        f"<td>{escape(str(row.get('neutral_count', '')))}</td>"
        f"<td>{escape(str(row.get('negative_count', '')))}</td>"
        f"<td>{escape(str(row.get('purchase_signal_count', '')))}</td>"
        "</tr>"
        for row in comment_metrics
    )
    topic_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('canonical_content_id', '')))}</td>"
        f"<td>{escape(str(row.get('topic_tag', '')))}</td>"
        f"<td>{escape(str(row.get('mentions', '')))}</td>"
        "</tr>"
        for row in comment_topics
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Southpole Comment Report {escape(run_id)}</title>
  <style>
    body {{ font-family: "IBM Plex Sans", "Segoe UI", sans-serif; margin: 0; background: #f5f7f8; color: #1d2529; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9e1e3; margin-bottom: 18px; }}
    th, td {{ border-bottom: 1px solid #e6ecee; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #edf4f4; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Southpole Comment Report</h1>
    <p>Run: {escape(run_id)}</p>
    <h2>Comment Metrics</h2>
    <table>
      <thead><tr><th>Content</th><th>Comments</th><th>Positive</th><th>Neutral</th><th>Negative</th><th>Purchase Signals</th></tr></thead>
      <tbody>{metrics_rows}</tbody>
    </table>
    <h2>Topic Summary</h2>
    <table>
      <thead><tr><th>Content</th><th>Topic</th><th>Mentions</th></tr></thead>
      <tbody>{topic_rows}</tbody>
    </table>
  </div>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def run_pipeline(
    *,
    keywords_input: str | list[str],
    days: int,
    slug: str | None = None,
    source: str = "cli",
    mock_file: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    keywords = parse_keywords(keywords_input)
    days = max(1, int(days))

    started_at = datetime.now(tz=app_settings.timezone)
    base_slug = slugify(slug or "-".join(keywords[:2]))
    timestamp = run_timestamp(started_at)
    run_dir = ensure_unique_run_dir(app_settings.output_root, f"{timestamp}_{base_slug}")
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.name

    if mock_file:
        records, source_meta = load_mock_records(mock_file)
    else:
        records, source_meta = collect_from_apify(keywords, app_settings)

    write_raw_jsonl(run_dir / "raw/source_items.jsonl", records)

    events = normalize_records(
        records=records,
        keywords=keywords,
        run_id=run_id,
        collected_at=started_at,
        days=days,
        local_tz=app_settings.timezone,
    )
    content_items = normalize_content_records(
        records=records,
        keywords=keywords,
        run_id=run_id,
        collected_at=started_at,
        days=days,
        local_tz=app_settings.timezone,
        raw_rel_path="raw/source_items.jsonl",
    )
    creator_profiles = aggregate_creator_profiles(content_items, run_id)
    keyword_totals = aggregate_keyword_totals(events, run_id)
    creators = aggregate_creators(events, run_id)
    daily_metrics = aggregate_daily_metrics(events, run_id)

    write_raw_jsonl(run_dir / "raw_events.jsonl", events)
    write_raw_csv(run_dir / "raw_events.csv", events)
    write_table_csv(run_dir / "keyword_totals.csv", keyword_totals)
    write_table_csv(run_dir / "creators.csv", creators)
    write_table_csv(run_dir / "daily_metrics.csv", daily_metrics)
    write_table_csv(run_dir / "normalized/content_items.csv", content_items, CONTENT_ITEM_FIELDS)
    write_table_csv(run_dir / "normalized/creator_profiles.csv", creator_profiles, CREATOR_PROFILE_FIELDS)

    compact = compact_timestamp(started_at)
    workbook_name = f"southpole_run_{timestamp}.xlsx"
    write_workbook(
        path=run_dir / workbook_name,
        raw_sheet_name=f"raw_{compact}",
        raw_rows=events,
        daily_metrics=daily_metrics,
        keyword_totals=keyword_totals,
        creators=creators,
    )

    finished_at = datetime.now(tz=app_settings.timezone)
    summary = _summary_payload(
        run_id=run_id,
        run_dir=run_dir,
        started_at=started_at,
        finished_at=finished_at,
        keywords=keywords,
        days=days,
        source=source,
        settings=app_settings,
        source_meta=source_meta,
        events=events,
        keyword_totals=keyword_totals,
        creators=creators,
        daily_metrics=daily_metrics,
        content_items=content_items,
        creator_profiles=creator_profiles,
    )

    write_json(run_dir / "summary.json", summary)
    write_report_html(
        path=run_dir / "report.html",
        summary=summary,
        keyword_totals=keyword_totals,
        creators=creators,
        daily_metrics=daily_metrics,
    )

    return summary


def build_comment_targets_for_run(
    *,
    run_dir: str | None = None,
    max_targets: int = 20,
    requested_comment_limit: int = 50,
    selection_mode: str = "top_by_views",
    selected_by: str = "operator",
    selection_note: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    resolved_run_dir = _resolve_run_dir(run_dir, app_settings)
    run_id = resolved_run_dir.name

    content_items = _read_table_csv(resolved_run_dir / "normalized/content_items.csv")
    if not content_items:
        raise ValueError(f"No canonical content items found in {resolved_run_dir / 'normalized/content_items.csv'}")

    targets = build_comment_targets(
        run_id=run_id,
        content_items=content_items,
        selected_from_run_id=run_id,
        selection_mode=selection_mode,
        selected_by=selected_by,
        selection_note=selection_note,
        requested_comment_limit=requested_comment_limit,
        max_targets=max_targets,
    )
    targets_path = resolved_run_dir / "comments/comment_targets.csv"
    write_table_csv(targets_path, targets, COMMENT_TARGET_FIELDS)

    _extend_summary(
        run_dir=resolved_run_dir,
        file_updates={"commentTargetsCsv": _relative_to_repo(targets_path)},
        count_updates={"commentTargetRows": len(targets)},
        stage="commentTargets",
    )

    return {
        "runId": run_id,
        "runDir": _relative_to_repo(resolved_run_dir),
        "generatedCount": len(targets),
        "files": {"commentTargetsCsv": _relative_to_repo(targets_path)},
    }


def collect_comments_for_run(
    *,
    run_dir: str | None = None,
    targets_file: str | None = None,
    mock_file: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    resolved_run_dir = _resolve_run_dir(run_dir, app_settings)
    run_id = resolved_run_dir.name

    targets_path = resolved_run_dir / "comments/comment_targets.csv"
    if targets_file:
        candidate = Path(targets_file).expanduser()
        if candidate.is_absolute():
            targets_path = candidate
        else:
            candidate_str = candidate.as_posix().lstrip("/")
            if candidate.exists():
                targets_path = candidate.resolve()
            elif candidate_str.startswith("outputs/runs/"):
                mapped = app_settings.output_root / candidate_str[len("outputs/runs/") :]
                if mapped.exists():
                    targets_path = mapped.resolve()
                else:
                    targets_path = mapped
            else:
                run_relative = (resolved_run_dir / candidate).resolve()
                if run_relative.exists():
                    targets_path = run_relative
                else:
                    output_relative = (app_settings.output_root / candidate).resolve()
                    if output_relative.exists():
                        targets_path = output_relative
                    else:
                        targets_path = run_relative
    comment_targets = _read_table_csv(targets_path)
    if not comment_targets:
        raise ValueError(f"No comment targets found: {targets_path}")

    if mock_file:
        comment_records, source_meta = load_mock_comment_records(mock_file)
    else:
        comment_records, source_meta = collect_tiktok_comments_from_targets(
            comment_targets=comment_targets,
            settings=app_settings,
        )

    raw_comments_path = resolved_run_dir / "comments/raw_comments.jsonl"
    write_raw_jsonl(raw_comments_path, comment_records)

    collected_at = datetime.now(tz=app_settings.timezone)
    comment_items = normalize_comment_records(
        records=comment_records,
        run_id=run_id,
        collected_at=collected_at,
        local_tz=app_settings.timezone,
        raw_rel_path="comments/raw_comments.jsonl",
    )
    comment_items_path = resolved_run_dir / "comments/comment_items.csv"
    write_table_csv(comment_items_path, comment_items, COMMENT_ITEM_FIELDS)
    write_json(resolved_run_dir / "comments/comment_collection_meta.json", source_meta)

    _extend_summary(
        run_dir=resolved_run_dir,
        file_updates={
            "rawCommentsJsonl": _relative_to_repo(raw_comments_path),
            "commentItemsCsv": _relative_to_repo(comment_items_path),
            "commentCollectionMetaJson": _relative_to_repo(resolved_run_dir / "comments/comment_collection_meta.json"),
        },
        count_updates={"commentItemRows": len(comment_items)},
        stage="commentCollection",
    )

    return {
        "runId": run_id,
        "runDir": _relative_to_repo(resolved_run_dir),
        "generatedCount": len(comment_items),
        "files": {
            "rawCommentsJsonl": _relative_to_repo(raw_comments_path),
            "commentItemsCsv": _relative_to_repo(comment_items_path),
        },
    }


def analyze_comments_for_run(
    *,
    run_dir: str | None = None,
    limit: int | None = None,
    analysis_model: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    resolved_run_dir = _resolve_run_dir(run_dir, app_settings)
    run_id = resolved_run_dir.name

    comment_items = _read_table_csv(resolved_run_dir / "comments/comment_items.csv")
    if not comment_items:
        raise ValueError("No comment items found. Run comment collection first.")

    insights, metrics, topics = analyze_comment_items(
        comment_items=comment_items,
        settings=app_settings,
        analysis_model=analysis_model,
        limit=limit,
    )

    insights_path = resolved_run_dir / "comments/comment_insights.csv"
    metrics_path = resolved_run_dir / "comments/comment_metrics.csv"
    topics_path = resolved_run_dir / "comments/comment_topics.csv"
    report_path = resolved_run_dir / "comments/comment_report.html"
    write_table_csv(insights_path, insights, COMMENT_INSIGHT_FIELDS)
    write_table_csv(metrics_path, metrics, COMMENT_METRICS_FIELDS)
    write_table_csv(topics_path, topics, COMMENT_TOPICS_FIELDS)
    _write_comment_report_html(path=report_path, run_id=run_id, comment_metrics=metrics, comment_topics=topics)

    _extend_summary(
        run_dir=resolved_run_dir,
        file_updates={
            "commentInsightsCsv": _relative_to_repo(insights_path),
            "commentMetricsCsv": _relative_to_repo(metrics_path),
            "commentTopicsCsv": _relative_to_repo(topics_path),
            "commentReportHtml": _relative_to_repo(report_path),
        },
        count_updates={
            "commentInsightRows": len(insights),
            "commentMetricsRows": len(metrics),
            "commentTopicRows": len(topics),
        },
        stage="commentAnalysis",
    )

    return {
        "runId": run_id,
        "runDir": _relative_to_repo(resolved_run_dir),
        "generatedCount": len(insights),
        "files": {
            "commentInsightsCsv": _relative_to_repo(insights_path),
            "commentMetricsCsv": _relative_to_repo(metrics_path),
            "commentTopicsCsv": _relative_to_repo(topics_path),
            "commentReportHtml": _relative_to_repo(report_path),
        },
    }


def score_creators_for_run(
    *,
    run_dir: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    resolved_run_dir = _resolve_run_dir(run_dir, app_settings)
    run_id = resolved_run_dir.name

    creator_profiles = _read_table_csv(resolved_run_dir / "normalized/creator_profiles.csv")
    content_items = _read_table_csv(resolved_run_dir / "normalized/content_items.csv")
    if not creator_profiles:
        raise ValueError("No canonical creator profiles found. Run /run first.")

    comment_insights = _read_table_csv(resolved_run_dir / "comments/comment_insights.csv")
    creator_comment_signals = build_creator_comment_signals(
        content_items=content_items,
        comment_insights=comment_insights,
    )
    scores = score_creator_rows(
        run_id=run_id,
        creator_profiles=creator_profiles,
        creator_comment_signals=creator_comment_signals,
    )
    score_path = resolved_run_dir / "scoring/creator_scores.csv"
    write_table_csv(score_path, scores, CREATOR_SCORE_FIELDS)

    _extend_summary(
        run_dir=resolved_run_dir,
        file_updates={"creatorScoresCsv": _relative_to_repo(score_path)},
        count_updates={"creatorScoreRows": len(scores)},
        stage="creatorScoring",
    )

    return {
        "runId": run_id,
        "runDir": _relative_to_repo(resolved_run_dir),
        "generatedCount": len(scores),
        "files": {"creatorScoresCsv": _relative_to_repo(score_path)},
    }


def sync_outreach_state_for_run(
    *,
    run_dir: str | None = None,
    campaign_id: str = "default-campaign",
    owner: str = "operator",
    status: str = "pending_review",
    notes: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    resolved_run_dir = _resolve_run_dir(run_dir, app_settings)
    run_id = resolved_run_dir.name

    creator_scores = _read_table_csv(resolved_run_dir / "scoring/creator_scores.csv")
    if not creator_scores:
        raise ValueError("No creator scores found. Run creator scoring first.")

    candidates = build_outreach_candidates(
        run_id=run_id,
        creator_scores=creator_scores,
        campaign_id=campaign_id,
        owner=owner,
        default_status=status,
        notes=notes,
    )
    candidates_path = resolved_run_dir / "outreach/outreach_candidates.csv"
    write_table_csv(candidates_path, candidates, OUTREACH_CANDIDATE_FIELDS)

    sync_result = sync_outreach_state(
        operator_state_root=app_settings.operator_state_root,
        outreach_candidates=candidates,
        run_id=run_id,
        campaign_id=campaign_id,
    )

    _extend_summary(
        run_dir=resolved_run_dir,
        file_updates={
            "outreachCandidatesCsv": _relative_to_repo(candidates_path),
            "outreachRegistryCsv": _relative_to_repo(Path(sync_result["registryPath"])),
            "outreachHistoryJsonl": _relative_to_repo(Path(sync_result["historyPath"])),
        },
        count_updates={
            "outreachCandidateRows": len(candidates),
            "outreachRegistryRows": sync_result["registryCount"],
        },
        stage="outreachState",
    )

    return {
        "runId": run_id,
        "runDir": _relative_to_repo(resolved_run_dir),
        "generatedCount": len(candidates),
        "files": {
            "outreachCandidatesCsv": _relative_to_repo(candidates_path),
            "outreachRegistryCsv": _relative_to_repo(Path(sync_result["registryPath"])),
            "outreachHistoryJsonl": _relative_to_repo(Path(sync_result["historyPath"])),
        },
        "sync": sync_result,
    }
