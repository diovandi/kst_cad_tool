"""
Build a Fusion 360 add-in bundle that includes kst_rating_tool so it runs
when installed in ApplicationPlugins (no repo path needed).

Run from repo root:  python fusion360_addin/build_bundle.py
Creates: fusion360_addin/KstAnalysis.bundle/
"""
import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDIN_SRC = os.path.join(REPO_ROOT, "fusion360_addin", "KstAnalysis")
SRC_PKG = os.path.join(REPO_ROOT, "src", "kst_rating_tool")
BUNDLE_DIR = os.path.join(REPO_ROOT, "fusion360_addin", "KstAnalysis.bundle")

# Top-level add-in modules required by commands (analysis_command imports visualizer)
REQUIRED_ADDIN_FILES = ("KstAnalysis.py", "visualizer.py")


def main():
    if not os.path.isdir(ADDIN_SRC):
        raise SystemExit("Add-in source not found: " + ADDIN_SRC)
    if not os.path.isdir(SRC_PKG):
        raise SystemExit("kst_rating_tool not found: " + SRC_PKG)
    for name in REQUIRED_ADDIN_FILES:
        path = os.path.join(ADDIN_SRC, name)
        if not os.path.isfile(path):
            raise SystemExit(
                "Add-in source missing required file: {} (analysis_command imports visualizer)".format(name)
            )

    if os.path.exists(BUNDLE_DIR):
        shutil.rmtree(BUNDLE_DIR)
    os.makedirs(BUNDLE_DIR)

    for name in os.listdir(ADDIN_SRC):
        src = os.path.join(ADDIN_SRC, name)
        dst = os.path.join(BUNDLE_DIR, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)

    # Copy kst_rating_tool into bundle so it works without repo
    dst_pkg = os.path.join(BUNDLE_DIR, "kst_rating_tool")
    shutil.copytree(
        SRC_PKG,
        dst_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
    )
    print("Created:", BUNDLE_DIR)
    print("Copy KstAnalysis.bundle to:")
    print("  Windows: %APPDATA%\\Autodesk\\ApplicationPlugins\\")
    print("Then restart Fusion 360.")


if __name__ == "__main__":
    main()
