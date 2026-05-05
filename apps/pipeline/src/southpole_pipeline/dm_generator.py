from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import csv
from html import escape
from pathlib import Path
import re
from typing import Any

import requests

from .config import Settings, load_settings
from .utils import slugify, write_json


HANGUL_RE = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]")

DM_FIELDS = [
    "creatorRank",
    "authorHandle",
    "authorName",
    "authorProfileUrl",
    "topPostUrl",
    "language",
    "personalizationBasis",
    "draftMessage",
    "reviewStatus",
    "openDmUrl",
    "copyReadyText",
    "messageFile",
]

STYLE_VARIANTS = [
    "warm and concise",
    "professional and compact",
    "friendly and insight-led",
    "curious and respectful",
]

DEFAULT_LANGUAGE_MODE = "ko"
DEFAULT_LIMIT = 10
DEFAULT_BRAND_CONTEXT = (
    "Southpole is a Seoul-based creator collaboration brand focused on practical beauty and lifestyle content. "
    "Voice should be warm, respectful, concise, and partnership-oriented."
)


@dataclass(frozen=True)
class DmGenerateResult:
    run_dir: Path
    dm_dir: Path
    generated_count: int
    files: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runDir": self.run_dir.as_posix(),
            "dmDir": self.dm_dir.as_posix(),
            "generatedCount": self.generated_count,
            "files": self.files,
        }


def _relative_to_repo(path: Path) -> str:
    path_str = path.as_posix()
    marker = "/outputs/runs/"
    if marker in path_str:
        return "outputs/runs/" + path_str.split(marker, 1)[1]
    return path_str


def _latest_run_dir(output_root: Path) -> Path:
    if not output_root.exists():
        raise ValueError(f"Run output root does not exist: {output_root}")
    run_dirs = sorted([path for path in output_root.iterdir() if path.is_dir()], key=lambda p: p.name)
    if not run_dirs:
        raise ValueError(f"No run directories found under: {output_root}")
    return run_dirs[-1]


def _resolve_run_dir(run_dir: str, output_root: Path) -> Path:
    candidate = Path(run_dir).expanduser()

    if candidate.is_absolute() and candidate.exists():
        return candidate

    if not candidate.is_absolute() and candidate.exists():
        return candidate.resolve()

    if not candidate.is_absolute():
        candidate_str = candidate.as_posix().lstrip("/")
        if candidate_str.startswith("outputs/runs/"):
            mapped = output_root / candidate_str[len("outputs/runs/") :]
            if mapped.exists():
                return mapped.resolve()
        joined = (output_root / candidate).resolve()
        if joined.exists():
            return joined

    # Allow host absolute path translation when calling the API from the host.
    run_marker = "/outputs/runs/"
    candidate_str = candidate.as_posix()
    if run_marker in candidate_str:
        translated = output_root / candidate_str.split(run_marker, 1)[1]
        if translated.exists():
            return translated

    return candidate


def _read_creators_csv(creators_csv_path: Path) -> list[dict[str, str]]:
    if not creators_csv_path.exists():
        raise ValueError(f"creators.csv not found: {creators_csv_path}")
    with creators_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_message_text(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return " ".join(lines)


def _infer_language(row: dict[str, str], language_mode: str) -> str:
    mode = (language_mode or DEFAULT_LANGUAGE_MODE).lower()
    if mode in {"ko", "en"}:
        return mode

    candidate = " ".join(
        [
            _coerce_text(row.get("creator_name")),
            _coerce_text(row.get("keywords")),
            _coerce_text(row.get("primary_keyword")),
            _coerce_text(row.get("top_post_description")),
        ]
    )
    if HANGUL_RE.search(candidate):
        return "ko"
    return "en"


def _build_personalization_basis(row: dict[str, str]) -> str:
    basis_parts = []
    primary_keyword = _coerce_text(row.get("primary_keyword"))
    if primary_keyword:
        basis_parts.append(f"Primary keyword: {primary_keyword}")
    top_post_url = _coerce_text(row.get("top_post_url"))
    if top_post_url:
        basis_parts.append(f"Top post: {top_post_url}")
    total_views = _coerce_text(row.get("total_views"))
    if total_views:
        basis_parts.append(f"Run views: {total_views}")
    return " | ".join(basis_parts) if basis_parts else "Creator metrics from latest run output"


def _default_profile_url(row: dict[str, str]) -> str:
    profile_url = _coerce_text(row.get("creator_url"))
    if profile_url:
        return profile_url
    handle = _coerce_text(row.get("creator_handle")).lstrip("@")
    if handle:
        return f"https://www.tiktok.com/@{handle}"
    return ""


def _safe_creator_slug(row: dict[str, str]) -> str:
    handle = _coerce_text(row.get("creator_handle")).lstrip("@")
    name = _coerce_text(row.get("creator_name"))
    return slugify(handle or name or "creator")


def _write_message_file(
    *,
    path: Path,
    rank: int,
    author_handle: str,
    author_name: str,
    author_profile_url: str,
    top_post_url: str,
    language: str,
    personalization_basis: str,
    draft_message: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_content = (
        f"Creator Rank: {rank}\n"
        f"Author Handle: {author_handle}\n"
        f"Author Name: {author_name}\n"
        f"Author Profile URL: {author_profile_url}\n"
        f"Top Post URL: {top_post_url}\n"
        f"Language: {language}\n"
        f"Personalization Basis: {personalization_basis}\n"
        "\n"
        "DM Draft:\n"
        f"{draft_message}\n"
    )
    path.write_text(file_content, encoding="utf-8")


def _generate_message_with_openai(
    *,
    settings: Settings,
    language: str,
    style_hint: str,
    creator_row: dict[str, str],
    personalization_basis: str,
    brand_context: str,
) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for DM draft generation.")

    author_handle = _coerce_text(creator_row.get("creator_handle"))
    author_name = _coerce_text(creator_row.get("creator_name"))
    top_post = _coerce_text(creator_row.get("top_post_url"))
    keywords = _coerce_text(creator_row.get("keywords"))

    system_prompt = (
        "You write outreach DMs for creator collaboration inquiries.\n"
        f"Brand context:\n{brand_context}\n"
        "Rules:\n"
        "- Be polite and concise.\n"
        "- Avoid spammy repetition.\n"
        "- Avoid fake personalization.\n"
        "- Keep wording varied across creators while keeping a consistent brand voice.\n"
        "- Never claim facts not present in the provided context.\n"
        "- Output only the DM body text, no bullet points, no labels."
    )

    target_language = "Korean" if language == "ko" else "English"
    user_prompt = (
        f"Write one DM in {target_language}.\n"
        f"Style hint: {style_hint}.\n"
        f"Creator handle: {author_handle}\n"
        f"Creator name: {author_name}\n"
        f"Top post URL: {top_post}\n"
        f"Keyword context: {keywords}\n"
        f"Personalization basis: {personalization_basis}\n"
        "Constraints:\n"
        "- Collaboration inquiry tone\n"
        "- 2 to 5 sentences\n"
        "- No hashtags\n"
        "- No emojis\n"
        "- No mention of being AI-generated\n"
        "- End with a soft call-to-action"
    )

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "reasoning_effort": "minimal",
            "max_completion_tokens": 220,
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"OpenAI request failed ({response.status_code}): {response.text[:500]}")

    response_payload = response.json()
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI response did not include choices.")
    message = _normalize_message_text(_coerce_text(choices[0].get("message", {}).get("content")))
    if not message:
        raise RuntimeError("OpenAI returned an empty DM message.")
    return message


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DM_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in DM_FIELDS})


def _render_review_html(run_dir: Path, rows: list[dict[str, Any]], generated_at: datetime) -> str:
    table_rows = []
    for row in rows:
        open_url = escape(_coerce_text(row["openDmUrl"]), quote=True)
        copy_text = escape(_coerce_text(row["copyReadyText"]), quote=True)
        message_file = escape(_coerce_text(row.get("messageFile")), quote=True)
        profile_button = ""
        if open_url:
            profile_button = f"<a class='btn' href='{open_url}' target='_blank' rel='noopener'>Open Profile</a>"

        file_button = ""
        if message_file:
            file_button = f"<a class='btn' href='{message_file}' target='_blank' rel='noopener'>Open File</a>"

        table_rows.append(
            "<tr>"
            f"<td>{escape(_coerce_text(row['creatorRank']))}</td>"
            f"<td>{escape(_coerce_text(row['authorHandle']))}</td>"
            f"<td>{escape(_coerce_text(row['language']))}</td>"
            f"<td>{escape(_coerce_text(row['personalizationBasis']))}</td>"
            f"<td class='draft'><div class='preview'>{escape(_coerce_text(row['draftMessage']))}</div></td>"
            f"<td>{escape(_coerce_text(row.get('messageFile')))}</td>"
            "<td class='actions'>"
            f"{profile_button}"
            f"{file_button}"
            f"<button class='btn' data-copy='{copy_text}' onclick='copyDraft(this)'>Copy</button>"
            "</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Southpole DM Review</title>
  <style>
    body {{ font-family: "IBM Plex Sans", "Segoe UI", sans-serif; margin: 0; background: #f8f8f6; color: #1d2529; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; }}
    .meta {{ margin: 0 0 20px; color: #5d6970; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dfdf; }}
    th, td {{ border-bottom: 1px solid #e3e8e8; padding: 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #eef4f4; }}
    td.draft {{ min-width: 360px; line-height: 1.5; }}
    .preview {{ max-width: 440px; white-space: normal; }}
    .actions {{ display: flex; gap: 6px; flex-wrap: wrap; min-width: 230px; }}
    .btn {{ border: 1px solid #89a2a9; background: #fff; border-radius: 8px; padding: 6px 10px; cursor: pointer; color: #1d2529; text-decoration: none; }}
    .btn.strong {{ border-color: #0f7c86; background: #0f7c86; color: #fff; }}
    .toast {{ position: fixed; right: 20px; bottom: 20px; background: #1d2529; color: #fff; padding: 8px 12px; border-radius: 8px; opacity: 0; transition: opacity 0.2s ease; }}
    .toast.show {{ opacity: 1; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Southpole DM Review</h1>
    <p class="meta">Run: {escape(run_dir.name)} | Generated: {escape(generated_at.isoformat())}</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Handle</th>
          <th>Lang</th>
          <th>Personalization Basis</th>
          <th>Message Preview</th>
          <th>Message File</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
  <div id="toast" class="toast">Copied</div>
  <script>
    async function copyText(text) {{
      try {{
        await navigator.clipboard.writeText(text);
        const toast = document.getElementById('toast');
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 1200);
      }} catch (err) {{
        console.error(err);
      }}
    }}

    function copyDraft(button) {{
      const text = button.dataset.copy || '';
      copyText(text);
    }}
  </script>
</body>
</html>"""


def generate_dm_drafts(
    *,
    run_dir: str | None = None,
    language_mode: str = DEFAULT_LANGUAGE_MODE,
    brand_context: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or load_settings()
    language_mode = _coerce_text(language_mode).lower() or DEFAULT_LANGUAGE_MODE
    if language_mode not in {"ko", "en", "auto"}:
        raise ValueError("language_mode must be one of: ko, en, auto")

    effective_brand_context = _coerce_text(brand_context) or DEFAULT_BRAND_CONTEXT
    effective_limit = DEFAULT_LIMIT if limit is None else max(1, int(limit))

    if run_dir:
        resolved_run_dir = _resolve_run_dir(run_dir, app_settings.output_root)
    else:
        resolved_run_dir = _latest_run_dir(app_settings.output_root)

    if not resolved_run_dir.exists():
        raise ValueError(f"Run directory does not exist: {resolved_run_dir}")

    creators_csv = resolved_run_dir / "creators.csv"
    creator_rows = _read_creators_csv(creators_csv)
    if not creator_rows:
        raise ValueError(f"No creators found in {creators_csv}")

    creator_rows = creator_rows[:effective_limit]

    dm_dir = resolved_run_dir / "dm"
    messages_dir = dm_dir / "messages"
    messages_dir.mkdir(parents=True, exist_ok=True)

    drafts: list[dict[str, Any]] = []
    for index, creator in enumerate(creator_rows, start=1):
        language = _infer_language(creator, language_mode)
        personalization_basis = _build_personalization_basis(creator)
        style_hint = STYLE_VARIANTS[(index - 1) % len(STYLE_VARIANTS)]
        draft_message = _generate_message_with_openai(
            settings=app_settings,
            language=language,
            style_hint=style_hint,
            creator_row=creator,
            personalization_basis=personalization_basis,
            brand_context=effective_brand_context,
        )

        author_handle = _coerce_text(creator.get("creator_handle"))
        author_name = _coerce_text(creator.get("creator_name"))
        author_profile_url = _default_profile_url(creator)
        top_post_url = _coerce_text(creator.get("top_post_url"))
        file_slug = _safe_creator_slug(creator)
        message_filename = f"{index}_{file_slug}.txt"
        message_file_path = messages_dir / message_filename

        _write_message_file(
            path=message_file_path,
            rank=index,
            author_handle=author_handle,
            author_name=author_name,
            author_profile_url=author_profile_url,
            top_post_url=top_post_url,
            language=language,
            personalization_basis=personalization_basis,
            draft_message=draft_message,
        )

        drafts.append(
            {
                "creatorRank": index,
                "authorHandle": author_handle,
                "authorName": author_name,
                "authorProfileUrl": author_profile_url,
                "topPostUrl": top_post_url,
                "language": language,
                "personalizationBasis": personalization_basis,
                "draftMessage": draft_message,
                "reviewStatus": "pending",
                "openDmUrl": author_profile_url,
                "copyReadyText": draft_message,
                "messageFile": f"messages/{message_filename}",
            }
        )

    drafts_csv = dm_dir / "dm_drafts.csv"
    drafts_json = dm_dir / "dm_drafts.json"
    review_html = dm_dir / "dm_review.html"

    _write_csv(drafts_csv, drafts)
    write_json(drafts_json, drafts)
    review_html.write_text(
        _render_review_html(resolved_run_dir, drafts, datetime.now(tz=app_settings.timezone)),
        encoding="utf-8",
    )

    result = DmGenerateResult(
        run_dir=resolved_run_dir,
        dm_dir=dm_dir,
        generated_count=len(drafts),
        files={
            "dmDraftsCsv": _relative_to_repo(drafts_csv),
            "dmDraftsJson": _relative_to_repo(drafts_json),
            "dmReviewHtml": _relative_to_repo(review_html),
            "dmMessagesDir": _relative_to_repo(messages_dir),
        },
    )
    return result.as_dict()
