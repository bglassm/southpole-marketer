from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re
from typing import Iterable


def parse_keywords(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    else:
        raw_items = [str(item).strip() for item in value]
    keywords = [item for item in raw_items if item]
    if not keywords:
        raise ValueError("At least one keyword is required.")
    return keywords


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "run"


def run_timestamp(now: datetime) -> str:
    return now.strftime("%Y-%m-%d_%H%M%S")


def compact_timestamp(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S")


def ensure_unique_run_dir(output_root: Path, base_name: str) -> Path:
    candidate = output_root / base_name
    if not candidate.exists():
        return candidate

    suffix = 1
    while True:
        with_suffix = output_root / f"{base_name}_{suffix:02d}"
        if not with_suffix.exists():
            return with_suffix
        suffix += 1


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
