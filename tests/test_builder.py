#!/usr/bin/env python3
"""Smoke tests for the Literature Reader HTML builder."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_html.py"
EXAMPLE = ROOT / "examples" / "paper_template.json"
IMAGE = ROOT / "examples" / "figures" / "placeholder.svg"

def run_build(data_path, output_path, expect_success=True):
    result = subprocess.run(
        [sys.executable, str(BUILDER), str(data_path), str(output_path)],
        capture_output=True, text=True
    )
    if expect_success and result.returncode != 0:
        raise AssertionError(result.stderr)
    if not expect_success and result.returncode == 0:
        raise AssertionError("Invalid panel data unexpectedly passed validation.")
    return result

def main():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        base = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        base["figures"]["1"]["image"] = str(IMAGE)

        # Standard whole-figure case: no artificial subfigure hotspots.
        whole = tmp / "whole.json"
        whole.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
        output = tmp / "whole.html"
        result = run_build(whole, output)
        html = output.read_text(encoding="utf-8")
        assert "__PAPER_DATA__" not in html
        assert "reviewer-view" in html
        assert "term-popover" in html
        assert "figure-modal" in html
        assert "figure-index" not in html.lower()
        assert "sidebar-foot" not in html
        assert "explicit panels=0" in result.stdout

        # Only explicitly confirmed lettered panels are accepted.
        panel_data = json.loads(json.dumps(base))
        panel_data["figures"]["1"].update({
            "has_explicit_panels": True,
            "panel_label_evidence": "Original image visibly labels panels (a) and (b).",
            "panels": [{
                "letter": "a", "rect": [0.05, 0.05, 0.48, 0.48],
                "title": "Panel a", "purpose": "", "how": "",
                "result": "", "significance": "", "limit": "", "source": "Fig. 1a"
            }]
        })
        panel_json = tmp / "panel.json"
        panel_json.write_text(json.dumps(panel_data, ensure_ascii=False), encoding="utf-8")
        panel_html = tmp / "panel.html"
        result = run_build(panel_json, panel_html)
        assert "explicit panels=1" in result.stdout

        # Artificial panels without original panel-label confirmation must fail.
        panel_data["figures"]["1"]["has_explicit_panels"] = False
        invalid_json = tmp / "invalid.json"
        invalid_json.write_text(json.dumps(panel_data, ensure_ascii=False), encoding="utf-8")
        run_build(invalid_json, tmp / "invalid.html", expect_success=False)

    print("PASS: whole figures, explicitly labeled panels, and invalid-panel rejection.")

if __name__ == "__main__":
    main()
