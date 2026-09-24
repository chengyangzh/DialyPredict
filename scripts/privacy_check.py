"""Fail closed when files unsafe for the public code repository are detected.

This is a lightweight pre-commit guardrail. It does not de-identify data and it
does not replace a manual review or institutional disclosure process.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BLOCKED_SUFFIXES = {
    ".bak",
    ".bin",
    ".cbm",
    ".csv",
    ".db",
    ".feather",
    ".joblib",
    ".m4a",
    ".model",
    ".mp3",
    ".onnx",
    ".parquet",
    ".pickle",
    ".pkl",
    ".sqlite",
    ".sqlite3",
    ".tsv",
    ".wav",
    ".xls",
    ".xlsx",
}
BLOCKED_DIRECTORY_NAMES = {"artifacts", "data", "datasets", "models", "outputs"}
SKIP_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

# Split literals prevent this scanner from finding its own test patterns.
SENSITIVE_PATTERNS = {
    "absolute macOS user path": re.compile("/" + "Users/"),
    "WeChat container path": re.compile("Library/" + "Containers/"),
    "WeChat account identifier": re.compile("wx" + r"id_[A-Za-z0-9_-]+"),
    "GitHub classic token": re.compile("gh" + r"p_[A-Za-z0-9]{20,}"),
    "GitHub fine-grained token": re.compile("github" + r"_pat_[A-Za-z0-9_]{20,}"),
    "private key": re.compile("BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "possible Chinese resident ID": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "possible mainland mobile number": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
}


def should_skip(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in SKIP_DIRECTORY_NAMES for part in relative_parts)


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if should_skip(path, root) or path.is_dir():
            continue
        relative = path.relative_to(root)
        parent_names = set(relative.parts[:-1])
        if parent_names & BLOCKED_DIRECTORY_NAMES:
            findings.append(f"blocked directory: {relative}")
            continue
        if path.suffix.lower() in BLOCKED_SUFFIXES:
            findings.append(f"blocked file type: {relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            findings.append(f"unreviewed file type: {relative}")
            continue
        if relative.as_posix() == "scripts/privacy_check.py":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"non-text content in text file: {relative}")
            continue
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{label}: {relative}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a repository for unsafe files or strings.")
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    findings = scan(root)
    if findings:
        print("PRIVACY CHECK FAILED", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Privacy check passed: no blocked files or sensitive-string patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
