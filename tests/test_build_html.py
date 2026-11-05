# -*- coding: utf-8 -*-
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_html


TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/pWQAAAAASUVORK5CYII="
)


class LiteratureReaderBuildTests(unittest.TestCase):
    def make_data(self, image_path):
        return {
            "page_title": "测试论文",
            "paper_metadata": {
                "title": "A test paper about hydrology",
                "authors": ["A. Author"],
                "journal": "Test Journal",
                "year": 2026,
                "doi": "10.xxxx/example"
            },
            "source_scope": {
                "full_text_read": True,
                "materials_used": ["PDF"],
                "pages_reviewed": ["1-5"],
                "limitations": "测试数据，仅用于构建检查"
            },
            "reading_guide": {
                "research_question": {
                    "object": "测试研究对象",
                    "problem": "测试研究问题",
                    "why_important": "测试重要性",
                    "expected_value": "测试预期价值",
                    "evidence_refs": []
                },
                "prior_work": [{
                    "research_route": "传统路线",
                    "typical_approach": "传统方法描述",
                    "what_it_solves": "能够解决的问题",
                    "limitations": "方法局限",
                    "paper_entry_point": "本文切入点",
                    "evidence_refs": []
                }],
                "core_intuition": {
                    "plain_language": "这是核心直觉",
                    "key_observation": "核心观察",
                    "why_method_fits": "方法适用原因",
                    "evidence_refs": []
                }
            },
            "key_findings": [{
                "id": "F1",
                "title": "测试发现",
                "finding": "测试结果说明",
                "quantitative_result": "RMSE = 0.1",
                "evidence_refs": [{"type": "figure", "locator": "Fig. 1"}],
                "supporting_methods": ["M1"],
                "experiment_refs": ["E1"],
                "evidence_boundary": "仅用于测试",
                "information_type": "paper_original"
            }],
            "finding_method_links": [{
                "finding_id": "F1",
                "method_ids": ["M1"],
                "experiment_ids": ["E1"],
                "figure_panel_refs": ["Fig. 1a"],
                "relationship_type": "validation",
                "explanation": "验证测试"
            }],
            "method_tree": {
                "root": "测试方法根节点",
                "nodes": [{
                    "id": "M1",
                    "parent_id": None,
                    "name": "测试方法",
                    "description": "测试方法描述",
                    "input": "输入数据",
                    "operation": "处理步骤",
                    "output": "输出结果",
                    "purpose": "方法作用",
                    "relationship_type": "parallel",
                    "source_refs": ["Methods"]
                }]
            },
            "equations": [{
                "id": "EQ1",
                "equation_number": "(1)",
                "original_expression": "y = ax + b",
                "variables": [{"symbol": "x", "meaning": "输入", "unit": "m"}],
                "input": "x",
                "output": "y",
                "role_in_method": "测试公式",
                "plain_language": "线性关系",
                "source_ref": "Eq. (1)"
            }],
            "experiments": {
                "datasets": [{"name": "测试数据集", "time_range": "2020-2025"}],
                "data_splits": {"train": "70%", "test": "30%"},
                "tasks": {"task": "预测"},
                "prediction_horizon": "1 day",
                "metrics": ["RMSE"],
                "baselines": ["Baseline"],
                "hyperparameters": {},
                "reproducibility_notes": []
            },
            "results": [{
                "id": "R1",
                "experiment_id": "E1",
                "finding_id": "F1",
                "metric": "RMSE",
                "value": 0.1,
                "unit": "m",
                "comparison": "对照组",
                "interpretation": "测试解释",
                "source_ref": "Table 1",
                "caveat": "测试边界"
            }],
            "figures": [{
                "id": "1",
                "figure_number": "1",
                "page": "Page 2",
                "image_asset": str(image_path),
                "caption": "测试组合图",
                "panels": [{
                    "id": "1a",
                    "original_label": "a",
                    "hotspot_label": "a",
                    "hotspot_coordinates": [0.0, 0.0, 1.0, 1.0],
                    "purpose": "实验目的",
                    "how_to_read": "读图方法",
                    "observations": "观察结果",
                    "argument_supported": "论证意义",
                    "evidence_boundary": "证据边界",
                    "source_ref": "Fig. 1a",
                    "confidence": "high"
                }]
            }],
            "reviewer_assessment": [{
                "issue": "样本量",
                "evidence": "测试依据",
                "why_it_matters": "影响稳健性",
                "affected_claim": "泛化结论",
                "suggested_validation": "增加验证",
                "severity": "medium",
                "information_type": "inference"
            }],
            "transfer_insights": [{
                "idea": "可借鉴的方法",
                "transferability": "adaptation_required",
                "why": "原因",
                "required_changes": "调整数据",
                "research_question": "新问题",
                "information_type": "inference"
            }],
            "glossary": [{
                "term": "RMSE",
                "full_name": "Root Mean Square Error",
                "chinese_translation": "均方根误差",
                "meaning_in_this_paper": "用于衡量误差",
                "role": "评价指标",
                "distinction": "不同于 MAE",
                "source_ref": "Methods"
            }],
            "unresolved_questions": [{
                "question": "是否存在独立测试集？",
                "why_unresolved": "测试数据未说明",
                "needed_material": "补充材料",
                "impact": "影响泛化判断"
            }]
        }

    def test_new_schema_builds_offline_html(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            image = temp_path / "tiny.png"
            image.write_bytes(TINY_PNG)
            data = self.make_data(image)
            output = temp_path / "result.html"
            warnings = build_html.build_document(data, temp_path, output, strict_images=True)
            html = output.read_text(encoding="utf-8")
            self.assertEqual(warnings, [])
            self.assertIn("阅读导览", html)
            self.assertIn("核心研究发现", html)
            self.assertIn("方法分叉树", html)
            self.assertIn("Root Mean Square Error", html)
            self.assertIn("data:image/png;base64,", html)
            self.assertIn("测试组合图", html)
            self.assertNotIn("__MAIN__", html)
            self.assertNotIn("__GLOSSARY_JSON__", html)

    def test_legacy_json_is_converted(self):
        old = {
            "heading": ["中文标题", "English title"],
            "citation": "Legacy citation",
            "nodes": [{
                "title": "旧版发现",
                "desc": "旧版描述",
                "page": "p. 2",
                "branches": [{
                    "title": "旧版方法分支",
                    "items": [{
                        "name": "旧版方法",
                        "core": "核心思路",
                        "effect": "方法作用",
                        "input": "输入",
                        "steps": "步骤",
                        "source": "Methods"
                    }]
                }]
            }],
            "terms": {"RMSE": ["Root Mean Square Error", "均方根误差", "误差指标", "评价作用"]},
            "figures": {}
        }
        converted = build_html.normalize_legacy_data(old)
        self.assertIn("paper_metadata", converted)
        self.assertEqual(len(converted["key_findings"]), 1)
        self.assertEqual(len(converted["method_tree"]["nodes"]), 2)
        self.assertEqual(converted["glossary"][0]["term"], "RMSE")

    def test_missing_image_warns_or_fails_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            data = self.make_data(temp_path / "missing.png")
            output = temp_path / "result.html"
            warnings = build_html.build_document(data, temp_path, output, strict_images=False)
            self.assertTrue(any("图片文件不存在" in item for item in warnings))
            self.assertTrue(output.exists())
            with self.assertRaises(ValueError):
                build_html.build_document(data, temp_path, output, strict_images=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
