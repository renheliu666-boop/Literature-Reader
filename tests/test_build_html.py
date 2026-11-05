import json
import base64
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_html


class BuildHtmlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.data_path = self.work / "paper.json"
        self.out_path = self.work / "paper.html"

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, data):
        self.data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def minimal_data(self):
        return {
            "paper_metadata": {"title": "A test paper", "authors": ["A. Author"], "journal": "Test Journal", "year": 2025},
            "reading_guide": {
                "research_question": {"object": "River network", "problem": "Test problem", "why_important": "Test importance", "expected_value": "Test value"},
                "prior_work": [{"research_route": "Baseline methods", "typical_approach": "Previous approach", "what_it_solves": "Basic task", "limitations": "Limited generalization", "paper_entry_point": "This paper adds a test"}],
                "core_intuition": {"plain_language": "A simple intuition", "key_observation": "Observation", "why_method_fits": "Fit"}
            },
            "key_findings": [{"id": "f1", "title": "Finding one", "finding": "A supported finding", "evidence_refs": ["Fig. 1"]}],
            "method_tree": {"root": "Research goal", "nodes": [{"id": "m1", "parent_id": None, "name": "Method one", "sibling_color_group": "root"}]},
            "glossary": [{"term": "GNN", "full_name": "Graph Neural Network", "chinese_translation": "图神经网络", "meaning_in_this_paper": "A graph model"}],
            "figures": []
        }

    def test_new_schema_builds_offline_html(self):
        self.write_json(self.minimal_data())
        warnings = build_html.build(self.data_path, self.out_path)
        html = self.out_path.read_text(encoding="utf-8")
        self.assertEqual(warnings, [])
        self.assertIn("A test paper", html)
        self.assertIn("研究问题", html)
        self.assertIn("前人工作", html)
        self.assertIn("核心直觉", html)
        self.assertIn("Graph Neural Network", html)
        self.assertNotIn("<!-- CONTENT -->", html)
        self.assertNotIn("<!-- DATA -->", html)

    def test_guide_cards_are_immediately_after_title_before_metadata(self):
        self.write_json(self.minimal_data())
        build_html.build(self.data_path, self.out_path)
        html = self.out_path.read_text(encoding="utf-8")
        title_pos = html.index("<h1>")
        guide_pos = html.index('id="reading-guide"')
        metadata_pos = html.index('class="metadata"')
        self.assertLess(title_pos, guide_pos)
        self.assertLess(guide_pos, metadata_pos)

    def test_legacy_json_conversion_preserves_legacy_fields(self):
        legacy = {
            "heading": ["中文标题", "English title"],
            "citation": "Example citation",
            "nodes": [{
                "title": "Finding title", "desc": "Finding description", "page": "p. 2",
                "branches": [{
                    "title": "Branch", "label": "Parallel route", "level": 1,
                    "items": [{
                        "name": "Method", "core": "Core", "input": "Input",
                        "steps": "Steps", "effect": "Output", "difference": "Difference",
                        "limit": "Limitation", "source": "p. 3"
                    }]
                }]
            }],
            "terms": {"GNN": ["Graph Neural Network", "图神经网络", "Context", "Role"]},
            "figures": {}
        }
        converted = build_html.normalize_legacy_data(legacy)
        self.assertEqual(converted["paper_metadata"]["title"], "English title")
        self.assertEqual(converted["method_tree"]["nodes"][0]["legacy_label"], "Parallel route")
        method = converted["method_tree"]["nodes"][1]
        self.assertEqual(method["legacy_difference"], "Difference")
        self.assertEqual(method["legacy_limit"], "Limitation")
        self.assertEqual(method["legacy_details"]["steps"], "Steps")

    def test_missing_image_warns_and_does_not_create_broken_img(self):
        data = self.minimal_data()
        data["figures"] = [{"id": "fig1", "figure_number": "1", "image_asset": "missing.png", "panels": []}]
        self.write_json(data)
        warnings = build_html.build(self.data_path, self.out_path)
        html = self.out_path.read_text(encoding="utf-8")
        self.assertTrue(any("图片不存在" in x for x in warnings))
        self.assertIn("未显示原图", html)
        self.assertNotIn('src="missing.png"', html)

    def test_strict_images_rejects_missing_image(self):
        data = self.minimal_data()
        data["figures"] = [{"id": "fig1", "image_asset": "missing.png", "panels": []}]
        self.write_json(data)
        with self.assertRaises(ValueError):
            build_html.build(self.data_path, self.out_path, strict_images=True)

    def test_figure_image_is_embedded_and_hotspot_is_rendered(self):
        data = self.minimal_data()
        image_dir = self.work / "figures"
        image_dir.mkdir()
        # A tiny valid 1x1 PNG keeps this test independent of external assets.
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/"
            "l1sAAAAASUVORK5CYII="
        )
        (image_dir / "figure1.png").write_bytes(png)
        data["figures"] = [{
            "id": "fig1", "figure_number": "1", "image_asset": "figures/figure1.png",
            "panels": [{
                "id": "a", "hotspot_label": "a", "hotspot_coordinates": [0.1, 0.1, 0.5, 0.5],
                "title": "Panel A", "purpose": "Purpose", "how_to_read": "Read axes",
                "observations": "Observation", "argument_supported": "Supports claim",
                "evidence_boundary": "Boundary"
            }]
        }]
        self.write_json(data)
        warnings = build_html.build(self.data_path, self.out_path)
        html = self.out_path.read_text(encoding="utf-8")
        self.assertEqual(warnings, [])
        self.assertIn("data:image/png;base64,", html)
        self.assertIn('class="hotspot"', html)
        self.assertIn("Panel A", html)

    def test_glossary_payload_is_safe_from_script_termination(self):
        data = self.minimal_data()
        data["glossary"] = [{"term": "X", "meaning_in_this_paper": "</script><script>alert(1)</script>"}]
        self.write_json(data)
        build_html.build(self.data_path, self.out_path)
        html = self.out_path.read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert(1)</script>", html)
        self.assertIn("<\\/script>", html)


if __name__ == "__main__":
    unittest.main()
