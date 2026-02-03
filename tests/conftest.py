"""Pytest configuration: ensure src is on path when running tests from repo root."""
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parent.parent
src = repo_root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
