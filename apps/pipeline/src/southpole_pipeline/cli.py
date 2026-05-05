from __future__ import annotations

import argparse
import json
import sys

from .collector import CollectorError
from .dm_generator import generate_dm_drafts
from .runner import (
    analyze_comments_for_run,
    build_comment_targets_for_run,
    collect_comments_for_run,
    run_pipeline,
    score_creators_for_run,
    sync_outreach_state_for_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Southpole TikTok pipeline runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run collect + aggregate flow")
    run_parser.add_argument("--keywords", required=True, help="Comma-separated keywords")
    run_parser.add_argument("--days", required=True, type=int, help="Lookback days")
    run_parser.add_argument("--slug", default="", help="Optional run slug for folder naming")
    run_parser.add_argument("--source", default="cli", help="Source label for metadata")
    run_parser.add_argument(
        "--mock-file",
        default="",
        help="Optional mock JSON file path to bypass Apify collection",
    )

    dm_parser = subparsers.add_parser("dm", help="Generate DM drafts from creators.csv")
    dm_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )
    dm_parser.add_argument(
        "--language-mode",
        default="ko",
        choices=["auto", "ko", "en"],
        help="Language mode for draft output.",
    )
    dm_parser.add_argument(
        "--brand-context",
        default="",
        help="Optional brand context text used as the DM voice guide.",
    )
    dm_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of creators to process from creators.csv (default: 10).",
    )

    comments_targets_parser = subparsers.add_parser(
        "comments-targets",
        help="Build comment_targets.csv from canonical content items in a run",
    )
    comments_targets_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )
    comments_targets_parser.add_argument("--max-targets", type=int, default=20, help="Maximum targets to select.")
    comments_targets_parser.add_argument(
        "--requested-comment-limit",
        type=int,
        default=50,
        help="Requested comment limit per selected content.",
    )
    comments_targets_parser.add_argument("--selection-mode", default="top_by_views", help="Selection mode label.")
    comments_targets_parser.add_argument("--selected-by", default="operator", help="Selector identity.")
    comments_targets_parser.add_argument("--selection-note", default="", help="Freeform selection note.")

    comments_collect_parser = subparsers.add_parser(
        "comments-collect",
        help="Collect comments for selected targets and write canonical comment items",
    )
    comments_collect_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )
    comments_collect_parser.add_argument(
        "--targets-file",
        default="",
        help="Optional explicit path to comment_targets.csv.",
    )
    comments_collect_parser.add_argument(
        "--mock-file",
        default="",
        help="Optional mock JSON file path to bypass live comment collection.",
    )

    comments_analyze_parser = subparsers.add_parser(
        "comments-analyze",
        help="Analyze comment items into insights/metrics/topics",
    )
    comments_analyze_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )
    comments_analyze_parser.add_argument("--limit", type=int, default=0, help="Optional maximum comments to analyze.")
    comments_analyze_parser.add_argument("--analysis-model", default="", help="Optional analysis model override.")

    score_creators_parser = subparsers.add_parser(
        "score-creators",
        help="Generate scoring/creator_scores.csv from creator profiles and comment signals",
    )
    score_creators_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )

    outreach_sync_parser = subparsers.add_parser(
        "outreach-sync",
        help="Sync run-local outreach candidates into operator_state registry/history",
    )
    outreach_sync_parser.add_argument(
        "--run-dir",
        default="",
        help="Run directory path. Omit to use latest run under outputs/runs.",
    )
    outreach_sync_parser.add_argument("--campaign-id", default="default-campaign", help="Campaign identifier.")
    outreach_sync_parser.add_argument("--owner", default="operator", help="Owner for registry records.")
    outreach_sync_parser.add_argument("--status", default="pending_review", help="Initial status value.")
    outreach_sync_parser.add_argument("--notes", default="", help="Optional notes for new/updated records.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            summary = run_pipeline(
                keywords_input=args.keywords,
                days=args.days,
                slug=args.slug or None,
                source=args.source,
                mock_file=args.mock_file or None,
            )
        except (CollectorError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "dm":
        try:
            summary = generate_dm_drafts(
                run_dir=args.run_dir or None,
                language_mode=args.language_mode,
                brand_context=args.brand_context or None,
                limit=args.limit,
            )
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "comments-targets":
        try:
            summary = build_comment_targets_for_run(
                run_dir=args.run_dir or None,
                max_targets=args.max_targets,
                requested_comment_limit=args.requested_comment_limit,
                selection_mode=args.selection_mode,
                selected_by=args.selected_by,
                selection_note=args.selection_note,
            )
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "comments-collect":
        try:
            summary = collect_comments_for_run(
                run_dir=args.run_dir or None,
                targets_file=args.targets_file or None,
                mock_file=args.mock_file or None,
            )
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "comments-analyze":
        try:
            summary = analyze_comments_for_run(
                run_dir=args.run_dir or None,
                limit=(args.limit or None),
                analysis_model=args.analysis_model or None,
            )
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "score-creators":
        try:
            summary = score_creators_for_run(run_dir=args.run_dir or None)
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command == "outreach-sync":
        try:
            summary = sync_outreach_state_for_run(
                run_dir=args.run_dir or None,
                campaign_id=args.campaign_id,
                owner=args.owner,
                status=args.status,
                notes=args.notes,
            )
        except (CollectorError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    if args.command not in {"run", "dm", "comments-targets", "comments-collect", "comments-analyze", "score-creators", "outreach-sync"}:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
