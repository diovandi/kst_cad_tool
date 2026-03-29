"""
Build and verify the Fusion 360 add-in bundle.

Run from repo root:
  python fusion360_addin/build_bundle.py
  python fusion360_addin/build_bundle.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDIN_SRC = REPO_ROOT / "fusion360_addin" / "KstAnalysis"
SRC_PKG = REPO_ROOT / "src" / "kst_rating_tool"
BUNDLE_DIR = REPO_ROOT / "fusion360_addin" / "KstAnalysis.bundle"

# Top-level add-in modules required by commands (analysis_command imports visualizer).
REQUIRED_ADDIN_FILES = ("KstAnalysis.py", "visualizer.py")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _python_files(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*.py")}


def _validate_inputs() -> None:
    if not ADDIN_SRC.is_dir():
        raise SystemExit("Add-in source not found: " + str(ADDIN_SRC))
    if not SRC_PKG.is_dir():
        raise SystemExit("kst_rating_tool not found: " + str(SRC_PKG))
    for name in REQUIRED_ADDIN_FILES:
        path = ADDIN_SRC / name
        if not path.is_file():
            raise SystemExit(
                "Add-in source missing required file: {} (analysis_command imports visualizer)".format(name)
            )


def _build_bundle() -> None:
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    for name in os.listdir(ADDIN_SRC):
        src = ADDIN_SRC / name
        dst = BUNDLE_DIR / name
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
        else:
            shutil.copy2(src, dst)

    dst_pkg = BUNDLE_DIR / "kst_rating_tool"
    shutil.copytree(
        SRC_PKG,
        dst_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
    )
    print("Created:", str(BUNDLE_DIR))
    print("Copy KstAnalysis.bundle to:")
    print("  Windows: %APPDATA%\\Autodesk\\ApplicationPlugins\\")
    print("Then restart Fusion 360.")


def _verify_bundle_sync() -> None:
    bundle_pkg = BUNDLE_DIR / "kst_rating_tool"
    if not bundle_pkg.is_dir():
        raise SystemExit("Bundle package missing; run build first: " + str(bundle_pkg))

    src_files = _python_files(SRC_PKG)
    bundle_files = _python_files(bundle_pkg)
    missing = sorted(set(src_files) - set(bundle_files))
    extra = sorted(set(bundle_files) - set(src_files))

    mismatched: list[str] = []
    for rel, src_path in src_files.items():
        bundle_path = bundle_files.get(rel)
        if bundle_path is None:
            continue
        if _sha256(src_path) != _sha256(bundle_path):
            mismatched.append(rel)

    if missing or extra or mismatched:
        print("Fusion bundle is out of sync with src/kst_rating_tool.")
        if missing:
            print("  Missing in bundle:")
            for rel in missing:
                print(f"    - {rel}")
        if extra:
            print("  Extra in bundle:")
            for rel in extra:
                print(f"    - {rel}")
        if mismatched:
            print("  Different file content:")
            for rel in mismatched:
                print(f"    - {rel}")
        raise SystemExit(1)

    print("Bundle sync verified: fusion360_addin/KstAnalysis.bundle/kst_rating_tool matches src/kst_rating_tool.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or verify Fusion 360 add-in bundle sync.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the bundled kst_rating_tool copy matches src/kst_rating_tool.",
    )
    args = parser.parse_args()

    _validate_inputs()
    if args.verify:
        _verify_bundle_sync()
        return

    _build_bundle()
    _verify_bundle_sync()


if __name__ == "__main__":
    main()
