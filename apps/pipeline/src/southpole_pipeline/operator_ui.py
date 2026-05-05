from __future__ import annotations

import csv
import json
from pathlib import Path
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import load_settings


router = APIRouter()
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _artifact_href(relative_path: str) -> str:
    cleaned = (relative_path or "").strip().lstrip("/")
    if cleaned.startswith("outputs/"):
        cleaned = cleaned.removeprefix("outputs/")
    if not cleaned:
        return ""
    return f"/artifacts/{cleaned}"


def _read_summary(run_dir: Path) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _list_run_dirs() -> list[Path]:
    settings = load_settings()
    if not settings.output_root.exists():
        return []
    return sorted(
        [path for path in settings.output_root.iterdir() if path.is_dir()],
        key=lambda item: item.name,
        reverse=True,
    )


def _resolve_run_dir(run_id: str) -> Path:
    candidate = (run_id or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="run_id is required")

    if not RUN_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    settings = load_settings()
    run_dir = settings.output_root / candidate
    if not run_dir.exists() or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {candidate}")
    return run_dir


@router.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def ui_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Southpole Operator UI</title>
  <style>
    :root {
      --bg: #f3f5f6;
      --panel: #ffffff;
      --line: #d7dee2;
      --ink: #1c252b;
      --muted: #5b6972;
      --primary: #0a7f8a;
      --primary-soft: #d8eef0;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #eef5f6 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .shell { max-width: 1200px; margin: 0 auto; padding: 20px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    .subtitle { margin: 0 0 18px; color: var(--muted); }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 14px;
    }
    .panel h2 { margin: 0 0 12px; font-size: 18px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
      background: #fff;
      color: var(--ink);
    }
    textarea { min-height: 88px; resize: vertical; }
    .row { margin-bottom: 10px; }
    .actions { margin-top: 8px; }
    button {
      border: 1px solid var(--primary);
      background: var(--primary);
      color: #fff;
      border-radius: 8px;
      padding: 9px 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button:disabled { opacity: 0.55; cursor: default; }
    .status { margin-top: 8px; font-size: 12px; color: var(--muted); }
    .result { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 10px; }
    .meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
    .meta .item { background: var(--primary-soft); border-radius: 8px; padding: 8px; }
    .meta .label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
    .meta .value { font-size: 13px; margin-top: 2px; font-weight: 600; }
    .links { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .links a {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 6px 10px;
      background: #fff;
      text-decoration: none;
      color: var(--ink);
      font-size: 13px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--line); padding: 7px; text-align: left; }
    th { background: #eff6f7; }
    .muted { color: var(--muted); font-size: 12px; }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .meta { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <h1>Southpole Operator UI</h1>
    <p class="subtitle">Run the two core actions locally and review output artifacts from this machine.</p>

    <section class="panel">
      <h2>1) Run Collect + Aggregate</h2>
      <div class="row">
        <label for="run-keywords">Keywords (comma or newline separated)</label>
        <textarea id="run-keywords" placeholder="kbeauty, oliveyoung"></textarea>
      </div>
      <div class="grid">
        <div class="row">
          <label for="run-days">Days</label>
          <input id="run-days" type="number" min="1" max="365" value="7" />
        </div>
        <div class="row">
          <label for="run-slug">Run label (optional)</label>
          <input id="run-slug" type="text" placeholder="manual" />
        </div>
      </div>
      <div class="row">
        <label for="run-source">Source label (optional)</label>
        <input id="run-source" type="text" value="ui" />
      </div>
      <div class="actions">
        <button id="run-button" type="button">Run Collect + Aggregate</button>
      </div>
      <div id="run-status" class="status"></div>
      <div id="run-result" class="result"></div>
    </section>

    <section class="panel">
      <h2>2) Generate DM Drafts</h2>
      <div class="grid">
        <div class="row">
          <label for="dm-run-id">Run folder</label>
          <select id="dm-run-id">
            <option value="">Latest run (default)</option>
          </select>
        </div>
        <div class="row">
          <label for="dm-language-mode">Language mode</label>
          <select id="dm-language-mode">
            <option value="ko" selected>ko</option>
            <option value="en">en</option>
            <option value="auto">auto</option>
          </select>
        </div>
      </div>
      <div class="grid">
        <div class="row">
          <label for="dm-limit">Limit</label>
          <input id="dm-limit" type="number" min="1" max="1000" value="10" />
        </div>
        <div class="row"></div>
      </div>
      <div class="row">
        <label for="dm-brand-context">Brand context (optional)</label>
        <textarea id="dm-brand-context" placeholder="Southpole brand voice and collaboration context"></textarea>
      </div>
      <div class="actions">
        <button id="dm-button" type="button">Generate DM Drafts</button>
      </div>
      <div id="dm-status" class="status"></div>
      <div id="dm-result" class="result"></div>
    </section>

    <section class="panel">
      <h2>Latest Creators Preview</h2>
      <p class="muted">Follower count is shown as <code>authorFollowers</code> for quick operator triage.</p>
      <div id="creators-preview"></div>
    </section>
  </div>

  <script>
    function splitKeywords(raw) {
      return (raw || "")
        .split(/[\\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .join(",");
    }

    function parseTimestamp(raw) {
      if (!raw) return null;
      const date = new Date(raw);
      if (Number.isNaN(date.getTime())) return null;
      return date;
    }

    function formatCardTime(raw) {
      const date = parseTimestamp(raw);
      if (!date) return "-";
      const hh = String(date.getHours()).padStart(2, "0");
      const mi = String(date.getMinutes()).padStart(2, "0");
      return `${hh}:${mi}`;
    }

    function formatTimestamp(raw) {
      const date = parseTimestamp(raw);
      if (!date) return "-";
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, "0");
      const dd = String(date.getDate()).padStart(2, "0");
      const hh = String(date.getHours()).padStart(2, "0");
      const mi = String(date.getMinutes()).padStart(2, "0");
      return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
    }

    function artifactHref(rel) {
      if (!rel) return "";
      return `/artifacts/${String(rel).replace(/^\\/+/, "").replace(/^outputs\\//, "")}`;
    }

    function runIdFromPath(pathValue) {
      const text = String(pathValue || "");
      const parts = text.split("/").filter(Boolean);
      return parts.length ? parts[parts.length - 1] : "";
    }

    function renderLinks(links) {
      const items = links.filter((item) => item.href);
      if (!items.length) return "";
      return `<div class="links">${items.map((item) => `<a href="${item.href}" target="_blank" rel="noopener">${item.label}</a>`).join("")}</div>`;
    }

    function renderSummary(targetId, payload) {
      const target = document.getElementById(targetId);
      const runId = payload.runId || runIdFromPath(payload.runDir);
      const runMeta = (window.__southpoleRuns || []).find((item) => item.runId === runId) || {};
      const files = { ...(runMeta.files || {}), ...(payload.files || {}) };
      const counts = Object.keys(payload.counts || {}).length ? payload.counts : (runMeta.counts || {});
      const buildTag = payload.buildTag || runMeta.buildTag || "-";
      const runDirDisplay = files.runDir || runMeta.runDir || payload.runDir || "-";
      const startedAt = payload.startedAt || runMeta.startedAt || "";
      const finishedAt = payload.finishedAt || runMeta.finishedAt || "";
      const linksHtml = renderLinks([
        { label: "report.html", href: artifactHref(files.reportHtml || `outputs/runs/${runId}/report.html`) },
        { label: "creators.csv", href: artifactHref(files.creatorsCsv || `outputs/runs/${runId}/creators.csv`) },
        { label: "dm_review.html", href: artifactHref(files.dmReviewHtml || `outputs/runs/${runId}/dm/dm_review.html`) }
      ]);

      target.innerHTML = `
        <div class="meta">
          <div class="item"><div class="label">Run ID</div><div class="value">${runId || "-"}</div></div>
          <div class="item"><div class="label">Run Dir</div><div class="value">${runDirDisplay}</div></div>
          <div class="item"><div class="label">Build Tag</div><div class="value">${buildTag}</div></div>
          <div class="item"><div class="label">Generated</div><div class="value">${payload.generatedCount ?? "-"}</div></div>
        </div>
        <div class="meta">
          <div class="item"><div class="label">Raw Events</div><div class="value">${counts.rawEvents ?? "-"}</div></div>
          <div class="item"><div class="label">Creators</div><div class="value">${counts.creatorRows ?? "-"}</div></div>
          <div class="item"><div class="label">Started</div><div class="value">${formatCardTime(startedAt)}</div></div>
          <div class="item"><div class="label">Finished</div><div class="value">${formatCardTime(finishedAt)}</div></div>
        </div>
        ${linksHtml}
      `;
      if (runId) {
        loadCreatorsPreview(runId);
      }
    }

    async function fetchJson(path, options = {}) {
      const response = await fetch(path, options);
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed: ${response.status}`);
      }
      return response.json();
    }

    async function loadRuns() {
      const data = await fetchJson("/runs");
      const runs = data.runs || [];
      window.__southpoleRuns = runs;
      const select = document.getElementById("dm-run-id");
      select.innerHTML = `<option value="">Latest run (default)</option>`;
      runs.forEach((run) => {
        const option = document.createElement("option");
        option.value = run.runId;
        option.textContent = `${run.runId} | ${formatTimestamp(run.startedAt)}`;
        select.appendChild(option);
      });

      if (runs.length > 0) {
        await loadCreatorsPreview(runs[0].runId);
      }
      return runs;
    }

    async function loadCreatorsPreview(runId) {
      const container = document.getElementById("creators-preview");
      if (!runId) {
        container.innerHTML = "<p class='muted'>No run selected.</p>";
        return;
      }
      try {
        const data = await fetchJson(`/runs/${encodeURIComponent(runId)}/creators?limit=12`);
        const rows = data.rows || [];
        if (!rows.length) {
          container.innerHTML = "<p class='muted'>No creators data available for this run.</p>";
          return;
        }
        container.innerHTML = `
          <table>
            <thead>
              <tr>
                <th>creator_handle</th>
                <th>creator_name</th>
                <th>authorFollowers</th>
                <th>total_views</th>
                <th>posts</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((row) => `
                <tr>
                  <td>${row.creator_handle || ""}</td>
                  <td>${row.creator_name || ""}</td>
                  <td>${row.authorFollowers ?? ""}</td>
                  <td>${row.total_views ?? ""}</td>
                  <td>${row.posts ?? ""}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        `;
      } catch (error) {
        container.innerHTML = `<p class='muted'>Failed to load creators preview: ${error.message}</p>`;
      }
    }

    async function onRunClick() {
      const status = document.getElementById("run-status");
      const button = document.getElementById("run-button");
      const keywords = splitKeywords(document.getElementById("run-keywords").value);
      const days = Number(document.getElementById("run-days").value || 7);
      const slug = document.getElementById("run-slug").value.trim();
      const source = document.getElementById("run-source").value.trim() || "ui";

      if (!keywords) {
        status.textContent = "Please enter at least one keyword.";
        return;
      }

      button.disabled = true;
      status.textContent = "Running collect + aggregate...";
      try {
        const payload = { keywords, days, source };
        if (slug) payload.slug = slug;
        const result = await fetchJson("/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        status.textContent = "Run completed.";
        renderSummary("run-result", result);
        await loadRuns();
      } catch (error) {
        status.textContent = `Run failed: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    }

    async function onDmClick() {
      const status = document.getElementById("dm-status");
      const button = document.getElementById("dm-button");
      const runId = document.getElementById("dm-run-id").value.trim();
      const languageMode = document.getElementById("dm-language-mode").value;
      const brandContext = document.getElementById("dm-brand-context").value.trim();
      const limit = Number(document.getElementById("dm-limit").value || 10);

      button.disabled = true;
      status.textContent = "Generating DM drafts...";
      try {
        const payload = { language_mode: languageMode, limit };
        if (runId) payload.run_dir = runId;
        if (brandContext) payload.brand_context = brandContext;
        const result = await fetchJson("/dm/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        await loadRuns();
        status.textContent = "DM generation completed.";
        renderSummary("dm-result", result);
      } catch (error) {
        status.textContent = `DM generation failed: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    }

    document.getElementById("run-button").addEventListener("click", onRunClick);
    document.getElementById("dm-button").addEventListener("click", onDmClick);
    loadRuns();
  </script>
</body>
</html>"""


@router.get("/runs")
def list_runs() -> dict[str, Any]:
    runs = []
    for run_dir in _list_run_dirs():
        summary = _read_summary(run_dir)
        files = summary.get("files", {}) if isinstance(summary, dict) else {}
        runs.append(
            {
                "runId": run_dir.name,
                "runDir": f"outputs/runs/{run_dir.name}",
                "startedAt": summary.get("startedAt", "") if isinstance(summary, dict) else "",
                "finishedAt": summary.get("finishedAt", "") if isinstance(summary, dict) else "",
                "buildTag": summary.get("buildTag", "") if isinstance(summary, dict) else "",
                "counts": summary.get("counts", {}) if isinstance(summary, dict) else {},
                "files": files,
                "links": {
                    "reportHtml": _artifact_href(files.get("reportHtml", f"outputs/runs/{run_dir.name}/report.html")),
                    "creatorsCsv": _artifact_href(files.get("creatorsCsv", f"outputs/runs/{run_dir.name}/creators.csv")),
                    "dmReviewHtml": _artifact_href(f"outputs/runs/{run_dir.name}/dm/dm_review.html"),
                },
            }
        )
    return {"runs": runs}


@router.get("/runs/{run_id}/creators")
def creators_preview(run_id: str, limit: int = Query(default=12, ge=1, le=200)) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    creators_path = run_dir / "creators.csv"
    if not creators_path.exists():
        raise HTTPException(status_code=404, detail=f"creators.csv not found for run: {run_id}")

    rows = []
    with creators_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(
                {
                    "creator_handle": row.get("creator_handle", ""),
                    "creator_name": row.get("creator_name", ""),
                    "authorFollowers": row.get("authorFollowers", ""),
                    "total_views": row.get("total_views", ""),
                    "posts": row.get("posts", ""),
                }
            )

    return {"runId": run_id, "rows": rows}
