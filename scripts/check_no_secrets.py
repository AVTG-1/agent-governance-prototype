"""Fail if anything that looks like a live credential is in the repository.

Usage:  python scripts/check_no_secrets.py [path ...]
Exit code 0 = clean, 1 = suspected secret found (file and line printed, value masked).

Placeholders such as <YOUR_FOUNDRY_TOKEN> are allowed. Real tokens are pasted into the
running app's connection screen and live only in memory; they never belong in files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".pytest_cache"}
SKIP_SUFFIXES = {".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".sqlite", ".db"}

PATTERNS = [
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("OpenRouter key", re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}")),
    ("Bearer value", re.compile(r"Bearer\s+(?!<|\{|\$)[A-Za-z0-9._\-]{24,}")),
    (
        "Assigned secret",
        re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*[\"'](?![<{$])[^\"'\s]{16,}[\"']"),
    ),
]


def iter_files(paths: list[Path]):
    for base in paths:
        if base.is_file():
            yield base
            continue
        for p in base.rglob("*"):
            if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in SKIP_SUFFIXES:
                continue
            yield p


def mask(value: str) -> str:
    return value[:4] + "…" + value[-4:] if len(value) > 12 else "…"


def main(argv: list[str]) -> int:
    targets = [Path(a).resolve() for a in argv] or [ROOT]
    findings = 0
    for path in iter_files(targets):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, rx in PATTERNS:
                for m in rx.finditer(line):
                    findings += 1
                    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                    print(f"{rel}:{lineno}: possible {label}: {mask(m.group(0))}")
    if findings:
        print(f"\n{findings} suspected secret(s). Remove them; tokens must only be pasted into the running app.")
        return 1
    print("No secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
