from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_run_wizard_analysis_subprocess_json_fixture(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_analysis.py"
    fixture = repo_root / "test_inputs" / "endcap_circular_plane.json"
    if not script.is_file() or not fixture.is_file():
        return

    out_txt = tmp_path / "results_wizard.txt"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            str(fixture),
            str(out_txt),
            "--skip-geometry-check",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    txt = out_txt.read_text(encoding="utf-8")
    assert "WTR\tMRR\tMTR\tTOR" in txt
    assert "0.0\t0.0\t0.0\t0.0" not in txt

    html_path = tmp_path / "Result - endcap_circular_plane.html"
    assert html_path.is_file()
    html = html_path.read_text(encoding="utf-8")
    assert "Weakest Total Resistance rating (WTR)" in html
