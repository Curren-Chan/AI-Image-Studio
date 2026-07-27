"""Fail CI when high-confidence secrets or private runtime files are present."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}
ALLOWED_FILES = {".env.example"}
FORBIDDEN_NAMES = {
    ".env",
    "database.db",
    "settings.json",
}
BINARY_SUFFIXES = {
    ".db",
    ".dll",
    ".dylib",
    ".exe",
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".zip",
}

PATTERNS = {
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "Google API key": re.compile(r"\bAIza[A-Za-z0-9_-]{16,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Windows user path": re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\/\s]+"),
    "macOS user path": re.compile(r"/Users/[^/\s]+"),
    "Linux user path": re.compile(r"/home/[^/\s]+"),
}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        relative = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES and path.name not in ALLOWED_FILES:
            findings.append(f"forbidden runtime file: {relative}")
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in PATTERNS.items():
            if relative == Path("scripts/security_check.py") and label.endswith("user path"):
                # The scanner necessarily contains these path signatures.
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{label}: {relative}:{line}")

    if findings:
        print("Security check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Security check passed: no high-confidence secrets or runtime files found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
