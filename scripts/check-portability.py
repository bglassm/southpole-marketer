#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".command",
    ".bat",
    ".ps1",
    ".ini",
    ".env",
    ".example",
    ".toml",
    ".cfg",
    ".conf",
    ".csv",
    ".html",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".xml",
    ".sql",
}

SKIP_DIRS = {
    ".git",
    "outputs",
    "state",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
}

ALLOWLIST_PATH_SNIPPETS = {
    "/home/node/.n8n",  # n8n internal container path
}


@dataclass
class Finding:
    file_path: Path
    line_no: int
    pattern_name: str
    match_text: str
    line_text: str


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("mac_users_path", re.compile(r"(?<![A-Za-z0-9+.-]://)/Users/[^\s\"'`]+")),
    ("legacy_project_path", re.compile(r"(?<![A-Za-z0-9+.-]://)/project/[^\s\"'`]+")),
    ("windows_abs_path", re.compile(r"(?<![A-Za-z0-9+.-]://)\b[A-Za-z]:[\\/][^\s\"'`]+")),
    ("home_abs_path", re.compile(r"(?<![A-Za-z0-9+.-]://)/home/[^\s\"'`]+")),
]


def should_scan_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if path.name in {".env", ".env.example", "Dockerfile"}:
        return True
    return False


def is_allowed_match(match_text: str) -> bool:
    return any(snippet in match_text for snippet in ALLOWLIST_PATH_SNIPPETS)


def scan_file(path: Path, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for line_no, line in enumerate(content.splitlines(), start=1):
        for pattern_name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                match_text = match.group(0)
                if is_allowed_match(match_text):
                    continue
                findings.append(
                    Finding(
                        file_path=path.relative_to(repo_root),
                        line_no=line_no,
                        pattern_name=pattern_name,
                        match_text=match_text,
                        line_text=line.strip(),
                    )
                )
    return findings


def collect_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if path.is_dir():
            continue
        if path.name == "check-portability.py":
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if should_scan_file(path):
            files.append(path)
    return files


def run(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in collect_files(repo_root):
        findings.extend(scan_file(path, repo_root))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo for portability risks from hardcoded absolute paths.")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to scan (default: repo root).",
    )
    parser.add_argument(
        "--allow-findings",
        action="store_true",
        help="Always exit 0 even if findings are detected.",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    findings = run(repo_root)

    print(f"Portability scan root: {repo_root}")
    if not findings:
        print("No suspicious absolute paths found.")
        return 0

    print(f"Found {len(findings)} potential portability issue(s):")
    for finding in findings:
        print(
            f"- {finding.file_path}:{finding.line_no} [{finding.pattern_name}] "
            f"{finding.match_text}\n  {finding.line_text}"
        )

    if args.allow_findings:
        print("Findings allowed by flag (--allow-findings).")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
