from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
from html import escape
import json
from typing import Any, Sequence

from openpyxl import Workbook


RAW_EVENTS_COLUMNS = [
    "runId",
    "collectedAt",
    "keyword",
    "matchedKeywords",
    "source",
    "sourceRecordId",
    "platform",
    "postId",
    "postUrl",
    "createTime",
    "date",
    "creatorId",
    "creatorHandle",
    "creatorName",
    "creatorUrl",
    "creatorFollowers",
    "description",
    "hashtags",
    "musicTitle",
    "region",
    "language",
    "views",
    "likes",
    "comments",
    "shares",
    "bookmarks",
    "engagements",
    "rawJson",
]


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_raw_jsonl(path: Path, events: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")


def write_raw_csv(path: Path, events: Sequence[dict[str, Any]]) -> None:
    rows = []
    for event in events:
        csv_row = {key: value for key, value in event.items() if key != "raw"}
        csv_row["rawJson"] = json.dumps(event.get("raw", {}), ensure_ascii=True)
        rows.append(csv_row)
    _write_csv(path, rows, RAW_EVENTS_COLUMNS)


def write_table_csv(
    path: Path,
    rows: Sequence[dict[str, Any]],
    fieldnames: Sequence[str] | None = None,
) -> None:
    if fieldnames is None:
        if rows:
            resolved_fieldnames = list(rows[0].keys())
        else:
            resolved_fieldnames = []
    else:
        resolved_fieldnames = list(fieldnames)
    _write_csv(path, rows, resolved_fieldnames)


def _append_sheet(workbook: Workbook, name: str, rows: Sequence[dict[str, Any]]) -> None:
    worksheet = workbook.create_sheet(title=name[:31])
    if not rows:
        worksheet.append(["no_data"])
        return
    headers = list(rows[0].keys())
    worksheet.append(headers)
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value, ensure_ascii=True))
            else:
                values.append(value)
        worksheet.append(values)


def write_workbook(
    path: Path,
    raw_sheet_name: str,
    raw_rows: Sequence[dict[str, Any]],
    daily_metrics: Sequence[dict[str, Any]],
    keyword_totals: Sequence[dict[str, Any]],
    creators: Sequence[dict[str, Any]],
) -> None:
    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    _append_sheet(workbook, raw_sheet_name, raw_rows)
    _append_sheet(workbook, "daily_metrics", daily_metrics)
    _append_sheet(workbook, "keyword_totals", keyword_totals)
    _append_sheet(workbook, "creators", creators)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _format_time_hhmm(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%H:%M")
    except ValueError:
        if "T" in text and len(text.split("T", 1)[1]) >= 5:
            return text.split("T", 1)[1][:5]
        return ""


def _render_table(rows: Sequence[dict[str, Any]], title: str, limit: int = 30) -> str:
    if not rows:
        return f"<section><h2>{escape(title)}</h2><p>No data</p></section>"

    headers = list(rows[0].keys())
    limited = rows[:limit]
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    row_html = []
    for row in limited:
        cells = "".join(f"<td>{escape(_format_number(row.get(header, '')))}</td>" for header in headers)
        row_html.append(f"<tr>{cells}</tr>")
    return (
        f"<section><h2>{escape(title)}</h2>"
        "<div class='table-wrap'><table>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table></div></section>"
    )


def _render_bar_chart(
    title: str,
    rows: Sequence[dict[str, Any]],
    label_key: str,
    value_key: str,
    limit: int = 12,
) -> str:
    if not rows:
        return f"<section><h2>{escape(title)}</h2><p>No data</p></section>"

    items = list(rows)[:limit]
    max_value = max(float(item.get(value_key, 0) or 0) for item in items) or 1
    bars = []
    for item in items:
        label = escape(str(item.get(label_key, "")))
        value = float(item.get(value_key, 0) or 0)
        width = round((value / max_value) * 100, 2)
        bars.append(
            "<div class='bar-row'>"
            f"<span class='bar-label'>{label}</span>"
            "<div class='bar-track'>"
            f"<div class='bar-fill' style='width:{width}%'></div>"
            "</div>"
            f"<span class='bar-value'>{escape(_format_number(value))}</span>"
            "</div>"
        )
    return f"<section><h2>{escape(title)}</h2><div class='bar-chart'>{''.join(bars)}</div></section>"


def write_report_html(
    path: Path,
    summary: dict[str, Any],
    keyword_totals: Sequence[dict[str, Any]],
    creators: Sequence[dict[str, Any]],
    daily_metrics: Sequence[dict[str, Any]],
) -> None:
    kpis = summary.get("counts", {})
    cards = [
        ("Run ID", summary.get("runId", "")),
        ("Keywords", ", ".join(summary.get("parameters", {}).get("keywords", []))),
        ("Days", summary.get("parameters", {}).get("days", "")),
        ("Raw events", kpis.get("rawEvents", 0)),
        ("Creators", kpis.get("creatorRows", 0)),
        ("Started", _format_time_hhmm(summary.get("startedAt", ""))),
        ("Finished", _format_time_hhmm(summary.get("finishedAt", ""))),
    ]
    card_html = "".join(
        "<div class='kpi-card'>"
        f"<div class='kpi-label'>{escape(str(label))}</div>"
        f"<div class='kpi-value'>{escape(_format_number(value))}</div>"
        "</div>"
        for label, value in cards
    )

    daily_chart_input = sorted(
        daily_metrics,
        key=lambda row: (row.get("date", ""), float(row.get("posts", 0) or 0)),
        reverse=False,
    )
    creators_top = sorted(creators, key=lambda row: float(row.get("total_views", 0) or 0), reverse=True)
    keywords_top = sorted(
        keyword_totals,
        key=lambda row: float(row.get("total_views", 0) or 0),
        reverse=True,
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Southpole TikTok Report {escape(summary.get("runId", ""))}</title>
  <style>
    :root {{
      --bg: #f5f4ee;
      --panel: #ffffff;
      --ink: #1f2a30;
      --muted: #5e6b70;
      --line: #d9dfdf;
      --accent: #0a7f8a;
      --accent-soft: #cdecee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at top left, #e6f4f1 0%, var(--bg) 45%, #f8f7f2 100%);
    }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .subtitle {{ color: var(--muted); margin-bottom: 18px; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
    }}
    .kpi-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .kpi-value {{ margin-top: 4px; font-size: 18px; font-weight: 700; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 16px;
    }}
    h2 {{ margin-top: 0; }}
    .bar-chart {{ display: grid; gap: 8px; }}
    .bar-row {{ display: grid; grid-template-columns: 190px 1fr 90px; gap: 8px; align-items: center; }}
    .bar-label {{ font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .bar-track {{
      height: 12px;
      border-radius: 8px;
      background: #edf2f2;
      overflow: hidden;
      border: 1px solid #dde5e5;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), #0b9e8c);
    }}
    .bar-value {{ text-align: right; font-variant-numeric: tabular-nums; font-size: 12px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; white-space: nowrap; }}
    th {{ background: var(--accent-soft); }}
    footer {{
      color: var(--muted);
      font-size: 12px;
      text-align: right;
      margin: 20px 0;
    }}
    @media (max-width: 700px) {{
      .bar-row {{ grid-template-columns: 110px 1fr 60px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Southpole TikTok Run Report</h1>
    <div class="subtitle">Human-readable run summary generated from local files only.</div>
    <section>
      <h2>Run Snapshot</h2>
      <div class="kpis">{card_html}</div>
    </section>
    {_render_bar_chart("Daily Metrics Chart (posts by day x keyword)", daily_chart_input, "date", "posts")}
    {_render_bar_chart("Keyword Totals Chart (total views)", keywords_top, "keyword", "total_views")}
    {_render_bar_chart("Creators Chart (top creator views)", creators_top, "creator_handle", "total_views")}
    {_render_table(keyword_totals, "keyword_totals.csv", 30)}
    {_render_table(creators, "creators.csv", 30)}
    {_render_table(daily_metrics, "daily_metrics.csv", 60)}
    <footer>Build tag: {escape(str(summary.get("buildTag", "")))}</footer>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
