#!/usr/bin/env python3
"""Validate local relative links inside markdown files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def _is_external(target: str) -> bool:
    lower = target.lower()
    return (
        lower.startswith("http://")
        or lower.startswith("https://")
        or lower.startswith("mailto:")
        or lower.startswith("tel:")
        or lower.startswith("#")
    )


def _check_file(md_path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = md_path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in LINK_RE.finditer(line):
            raw = match.group(1).strip()
            if not raw or _is_external(raw):
                continue
            target = unquote(raw.split("#", 1)[0].strip())
            if not target:
                continue
            resolved = (md_path.parent / target).resolve()
            if not resolved.exists():
                rel_md = md_path.relative_to(repo_root).as_posix()
                errors.append(f"{rel_md}:{line_no} -> missing target: {raw}")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    for md in repo_root.rglob("*.md"):
        parts = set(md.parts)
        if ".git" in parts or ".cursor" in parts or "node_modules" in parts:
            continue
        errors.extend(_check_file(md, repo_root))

    if errors:
        print("Broken markdown links found:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
