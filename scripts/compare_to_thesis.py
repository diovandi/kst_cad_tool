#!/usr/bin/env python3
"""
Compare Python and Octave/MATLAB full results to thesis reference values (Ch 10/11).

DEPRECATED: Use scripts/deep_comparison.py instead. This script now forwards arguments
to deep_comparison.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path for imports if needed, and to find deep_comparison
if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))

from scripts.deep_comparison import main as deep_main


def main() -> int:
    print("WARNING: scripts/compare_to_thesis.py is deprecated. Use scripts/deep_comparison.py instead.", file=sys.stderr)
    return deep_main()


if __name__ == "__main__":
    sys.exit(main())
