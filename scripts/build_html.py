#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a standalone, offline Literature Reader HTML from the current JSON schema.

Python 3.9+; standard library only.
Usage:
  python scripts/build_html.py input.json output.html
  python scripts/build_html.py input.json output.html --strict-images
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "reader.html"
IMAGE_MIMES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
RELATION_LABELS = {
    "sequence": "顺序关系",
    "composition": "组成关系",
    "parallel": "并列关系",
    "validation": "验证关系",
    "support": "辅助关系",
    "direct": "直接借鉴",
    "adaptation_required": "需要改造",
    "not_directly_transferable": "不宜直接迁移",
}


def esc(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def source_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [
            value.get("locator"),
            value.get("quote_or_evidence"),
            value.get("url_or_file"),
        ]
        return "；".join(str(x) for x in parts if x not in (None, ""))
    if isinstance(value, list):
        return "；".join(source_text(x) for x in value if x not in (None, ""))
    return str(value)


def term_text(value: Any, glossary: dict[str, dict]) -> str:
    """Escape text and wrap matching glossary terms in accessible buttons."""
    raw = display(value)
    if not raw or not glossary:
        return esc(raw)
    terms = sorted(glossary.keys(), key=len, reverse=True)
    lookup = {key.casefold(): key for key in terms}
    pattern = re.compile("|".join(re.escape(key) for key in terms), re.IGNORECASE)
    output = []
    cursor = 0
    for match in pattern.finditer(raw):
        key = lookup.get(match.group(0).casefold())
        if not key:
            continue
        output.append(esc(raw[cursor:match.start()]))
        output.append(
            f'<button class="term" type="button" data-term="{esc(key)}" '
            f'aria-haspopup="dialog" aria-expanded="false">{esc(match.group(0))}</button>'
        )
        cursor = match.end()
    output.append(esc(raw[cursor:]))
    return "".join(output)


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def source_refs_html(refs: Any, glossary: dict) -> str:
    refs = as_list(refs)
    if not refs:
        return ""
    body = "；".join(source_text(ref) for ref in refs if source_text(ref))
    if not body:
        return ""
    return f'<div class="source-ref"><b>原文定位</b>{term_text(body, glossary)}</div>'


def info_rows(items: list[tuple[str, Any]], glossary: dict) -> str:
    out = []
    for label, value in items:
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            value = "；".join(display(x) for x in value)
        out.append(
            f'<div class="info-row"><strong>{esc(label)}</strong>'
            f'<span>{term_text(value, glossary)}</span></div>'
        )
    return "".join(out)


def normalize_legacy_data(data: dict) -> dict:
    """Convert the repository's previous heading/nodes/terms JSON into the new schema."""
    if "paper_metadata" in data:
        return data
    if "heading" not in data or "nodes" not in data:
        return data

    heading = as_list(data.get("heading"))
    title = heading[-1] if heading else data.get("page_title", "Untitled paper")
    metadata = {
        "title": title,
        "authors": [],
        "journal": "",
        "year": None,
        "doi": "",
        "source_file": "",
        "subtitle": heading[0] if len(heading) > 1 else "",
        "citation_note": data.get("citation", ""),
    }

    findings = []
    method_nodes = []
    links = []
    for i, old_node in enumerate(data.get("nodes", []), 1):
        finding_id = f"finding-{i}"
        branch_ids = []
        for j, branch in enumerate(old_node.get("branches", []), 1):
            branch_id = f"{finding_id}-branch-{j}"
            branch_ids.append(branch_id)
            method_nodes.append({
                "id": branch_id,
                "parent_id": None,
                "name": branch.get("title", f"方法分支 {j}"),
                "description": branch.get("goal", ""),
                "input": "",
                "operation": "",
                "output": "",
                "purpose": branch.get("goal", ""),
                "relationship_type": old_node.get("branch_relation", "parallel"),
                "source_refs": [],
                "sibling_color_group": f"{finding_id}-branches",
            })
            for k, item in enumerate(branch.get("items", []), 1):
                method_nodes.append({
                    "id": f"{branch_id}-method-{k}",
                    "parent_id": branch_id,
                    "name": item.get("name", f"方法 {k}"),
                    "description": item.get("core", ""),
                    "input": item.get("input", ""),
                    "operation": item.get("steps", ""),
                    "output": item.get("effect", ""),
                    "purpose": item.get("effect", ""),
                    "relationship_type": item.get("role", "support"),
                    "source_refs": [item.get("source", "")] if item.get("source") else [],
                    "sibling_color_group": f"{branch_id}-methods",
                })
        findings.append({
            "id": finding_id,
            "title": old_node.get("title", f"研究发现 {i}"),
            "finding": old_node.get("desc", ""),
            "quantitative_result": "",
            "evidence_refs": [old_node.get("page", ""), old_node.get("evidence", "")],
            "supporting_methods": branch_ids,
            "experiment_refs": [],
            "evidence_boundary": "",
            "information_type": "paper_original",
        })
        links.append({
            "finding_id": finding_id,
            "method_ids": branch_ids,
            "experiment_ids": [],
            "figure_panel_refs": [str(old_node.get("figure"))] if old_node.get("figure") else [],
            "relationship_type": old_node.get("branch_relation", "parallel"),
            "explanation": old_node.get("evidence", ""),
        })

    old_figures = data.get("figures", {})
    figures = []
    if isinstance(old_figures, dict):
        for number, figure in old_figures.items():
            panels = []
            for index, panel in enumerate(figure.get("panels", []), 1):
                panels.append({
                    "id": panel.get("letter", str(index)),
                    "original_label": panel.get("letter", str(index)),
                    "hotspot_label": panel.get("letter", str(index)),
                    "hotspot_coordinates": panel.get("rect"),
                    "purpose": panel.get("purpose", ""),
                    "how_to_read": panel.get("how", ""),
                    "observations": panel.get("result", ""),
                    "argument_supported": panel.get("significance", ""),
                    "evidence_boundary": panel.get("limit", ""),
                    "source_ref": panel.get("source", ""),
                    "title": panel.get("title", ""),
                    "confidence": "legacy",
                })
            figures.append({
                "id": str(number),
                "figure_number": str(number),
                "page": "",
                "image_asset": figure.get("image", ""),
                "caption": figure.get("source", f"Fig. {number}"),
                "panels": panels,
            })

    old_terms = data.get("terms", {})
    glossary = []
    if isinstance(old_terms, dict):
        for term, values in old_terms.items():
            values = as_list(values)
            values = (values + ["", "", "", ""])[:4]
            glossary.append({
                "term": term,
                "full_name": values[0],
                "chinese_translation": values[1],
                "meaning_in_this_paper": values[2],
                "role": values[3],
                "distinction": "",
                "source_ref": "",
            })

    return {
        "page_title": data.get("page_title", title),
        "paper_metadata": metadata,
        "source_scope": {
            "full_text_read": None,
            "materials_used": ["由旧版 JSON 自动转换；请核对原始材料范围"],
            "pages_reviewed": [],
            "limitations": "旧版数据未包含完整的新 schema 字段；阅读导览、实验、审稿评价等内容不会自动补造。",
        },
        "reading_guide": {
            "research_question": {},
            "prior_work": [],
            "core_intuition": {},
        },
        "key_findings": findings,
        "finding_method_links": links,
        "method_tree": {
            "root": "各项研究发现对应的方法分支",
            "nodes": method_nodes,
        },
        "equations": [],
        "experiments": {},
        "results": [],
        "figures": figures,
        "reviewer_assessment": [],
        "transfer_insights": [],
        "glossary": glossary,
        "unresolved_questions": [{
            "question": "新版阅读导览、实验设计及审稿评价尚未补充",
            "why_unresolved": "原始旧版 JSON 不含这些字段",
            "needed_material": "论文全文及补充材料",
            "impact": "不能将空缺内容当作论文已经分析过",
        }],
        "_converted_from_legacy": True,
    }


def normalize_glossary(items: Any) -> dict[str, dict]:
    result = {}
    if isinstance(items, dict):
        # Also accept the older {term: [full, cn, meaning, role]} form.
        for term, values in items.items():
            values = as_list(values)
            values = (values + ["", "", "", ""])[:4]
            result[str(term)] = {
                "full_name": values[0],
                "chinese_translation": values[1],
                "meaning_in_this_paper": values[2],
                "role": values[3],
                "distinction": "",
            }
        return result
    for item in as_list(items):
        if not isinstance(item, dict) or not item.get("term"):
            continue
        result[str(item["term"])] = item
    return result


def validate_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是 object。")
    if not isinstance(data.get("paper_metadata"), dict):
        raise ValueError("缺少 paper_metadata；请使用新版 paper-analysis-template.json。")
    if not data["paper_metadata"].get("title"):
        raise ValueError("paper_metadata.title 不能为空。")
    for key in ("key_findings", "finding_method_links", "equations",
                "results", "figures", "reviewer_assessment",
                "transfer_insights", "unresolved_questions"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"{key} 必须是数组。")
    method_tree = data.get("method_tree", {})
    if not isinstance(method_tree, dict) or not isinstance(method_tree.get("nodes", []), list):
        raise ValueError("method_tree.nodes 必须是数组。")


def render_reading_guide(guide: dict, glossary: dict) -> str:
    rq = guide.get("research_question") or {}
    core = guide.get("core_intuition") or {}
    prior = as_list(guide.get("prior_work"))
    cards = [
        ("研究问题", [
            ("研究对象", rq.get("object")),
            ("要解决的问题", rq.get("problem")),
            ("为什么重要", rq.get("why_important")),
            ("预期价值", rq.get("expected_value")),
        ]),
        ("前人工作", []),
        ("核心直觉", [
            ("通俗解释", core.get("plain_language")),
            ("关键观察", core.get("key_observation")),
            ("方法为何适用", core.get("why_method_fits")),
        ]),
    ]
    prior_html = []
    for item in prior:
        if not isinstance(item, dict):
            continue
        prior_html.append(
            '<article class="prior-item">'
            f'<h4>{term_text(item.get("research_route", "研究路线"), glossary)}</h4>'
            f'<p>{term_text(item.get("typical_approach", ""), glossary)}</p>'
            f'{info_rows([("能够解决", item.get("what_it_solves")), ("局限", item.get("limitations")), ("本文切入点", item.get("paper_entry_point"))], glossary)}'
            f'{source_refs_html(item.get("evidence_refs"), glossary)}'
            '</article>'
        )
    out = ['<section class="section" id="reading-guide"><div class="section-head"><span>01</span><div><h2>阅读导览</h2><p>先明确问题、研究缺口与作者的核心思路</p></div></div><div class="guide-grid">']
    for title, fields in cards:
        if title == "前人工作":
            body = "".join(prior_html) or '<p class="empty-note">当前材料未提供前人工作路线，请根据论文 Introduction / Related Work 补充。</p>'
        else:
            body = info_rows(fields, glossary)
        out.append(f'<article class="guide-card"><h3>{title}</h3>{body}</article>')
    out.append('</div></section>')
    return "".join(out)


def render_findings(findings: list, glossary: dict) -> str:
    out = ['<section class="section" id="findings"><div class="section-head"><span>02</span><div><h2>核心研究发现</h2><p>每项发现都应能追溯到方法、实验和原文证据</p></div></div><div class="finding-grid">']
    if not findings:
        out.append('<p class="empty-note">尚未填写核心研究发现。</p>')
    for i, item in enumerate(findings, 1):
        if not isinstance(item, dict):
            continue
        refs = source_refs_html(item.get("evidence_refs"), glossary)
        out.append(
            f'<article class="finding-card"><div class="finding-no">F{i:02d}</div>'
            f'<h3>{term_text(item.get("title", ""), glossary)}</h3>'
            f'<p>{term_text(item.get("finding", ""), glossary)}</p>'
            f'{info_rows([("定量结果", item.get("quantitative_result")), ("证据边界", item.get("evidence_boundary"))], glossary)}'
            f'{refs}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_finding_links(links: list, glossary: dict) -> str:
    if not links:
        return ""
    out = ['<section class="section" id="finding-links"><div class="section-head"><span>03</span><div><h2>研究发现与方法、实验的对应关系</h2><p>区分顺序、组成、并列、验证和辅助关系</p></div></div><div class="link-grid">']
    for item in links:
        if not isinstance(item, dict):
            continue
        relation = RELATION_LABELS.get(item.get("relationship_type"), item.get("relationship_type", ""))
        out.append(
            f'<article class="link-card"><span class="relation">{esc(relation)}</span>'
            f'<h3>发现：{term_text(item.get("finding_id", ""), glossary)}</h3>'
            f'<p>{term_text(item.get("explanation", ""), glossary)}</p>'
            f'{info_rows([("方法节点", item.get("method_ids")), ("实验节点", item.get("experiment_ids")), ("图表证据", item.get("figure_panel_refs"))], glossary)}'
            '</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_method_tree(tree: dict, glossary: dict) -> str:
    nodes = tree.get("nodes", []) if isinstance(tree, dict) else []
    if not nodes:
        return ""
    by_id = {str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id") is not None}
    children: dict[str, list] = {}
    roots = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        parent = node.get("parent_id")
        if parent is None or str(parent) not in by_id:
            roots.append(node)
        else:
            children.setdefault(str(parent), []).append(node)

    def node_html(node: dict, depth: int, trail: set[str]) -> str:
        node_id = str(node.get("id", ""))
        if node_id in trail:
            return '<div class="method-node cycle-warning">检测到循环引用，请检查 parent_id。</div>'
        next_trail = set(trail)
        next_trail.add(node_id)
        relation = RELATION_LABELS.get(node.get("relationship_type"), node.get("relationship_type", ""))
        rows = info_rows([
            ("输入", node.get("input")),
            ("处理 / 操作", node.get("operation")),
            ("输出", node.get("output")),
            ("作用", node.get("purpose")),
        ], glossary)
        child_html = "".join(node_html(child, depth + 1, next_trail) for child in children.get(node_id, []))
        return (
            f'<article class="method-node" data-depth="{min(depth, 5)}">'
            f'<div class="method-node-head"><h3>{term_text(node.get("name", ""), glossary)}</h3>'
            f'<span class="relation">{esc(relation)}</span></div>'
            f'<p>{term_text(node.get("description", ""), glossary)}</p>{rows}'
            f'{source_refs_html(node.get("source_refs"), glossary)}'
            f'{f"<div class=method-children>{child_html}</div>" if child_html else ""}'
            '</article>'
        )

    out = ['<section class="section" id="method-tree"><div class="section-head"><span>04</span><div><h2>方法分叉树</h2><p>按 parent_id 展示层级；只有原文明确支持时才标记顺序关系</p></div></div>']
    root_title = tree.get("root")
    if root_title:
        out.append(f'<div class="tree-root">{term_text(root_title, glossary)}</div>')
    out.append('<div class="method-tree-grid">')
    out.extend(node_html(node, 1, set()) for node in roots)
    out.append('</div></section>')
    return "".join(out)


def render_equations(equations: list, glossary: dict) -> str:
    if not equations:
        return ""
    out = ['<section class="section" id="equations"><div class="section-head"><span>05</span><div><h2>关键公式</h2><p>保留原文表达，并解释变量、输入输出和公式作用</p></div></div><div class="equation-grid">']
    for item in equations:
        if not isinstance(item, dict):
            continue
        variables = item.get("variables", [])
        var_html = []
        for var in as_list(variables):
            if isinstance(var, dict):
                var_html.append(
                    f'<div class="info-row"><strong>{esc(var.get("symbol", var.get("name", "变量")))}</strong>'
                    f'<span>{term_text(var.get("meaning", ""), glossary)}'
                    f'{("；单位：" + esc(var.get("unit"))) if var.get("unit") else ""}</span></div>'
                )
            else:
                var_html.append(f'<div class="info-row"><span>{term_text(var, glossary)}</span></div>')
        out.append(
            f'<article class="equation-card"><h3>{term_text(item.get("equation_number", "公式"), glossary)}</h3>'
            f'<pre>{esc(item.get("original_expression", ""))}</pre>'
            f'{info_rows([("通俗解释", item.get("plain_language")), ("输入", item.get("input")), ("输出", item.get("output")), ("方法中的作用", item.get("role_in_method"))], glossary)}'
            f'{"".join(var_html)}{source_refs_html(item.get("source_ref"), glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_experiments(experiments: dict, glossary: dict) -> str:
    if not experiments:
        return ""
    datasets = as_list(experiments.get("datasets"))
    metrics = as_list(experiments.get("metrics"))
    baselines = as_list(experiments.get("baselines"))
    rows = [
        ("数据划分", experiments.get("data_splits")),
        ("任务设置", experiments.get("tasks")),
        ("预测窗口", experiments.get("prediction_horizon")),
        ("评价指标", metrics),
        ("对比基线", baselines),
        ("超参数", experiments.get("hyperparameters")),
        ("可复现性信息", experiments.get("reproducibility_notes")),
    ]
    out = ['<section class="section" id="experiments"><div class="section-head"><span>06</span><div><h2>实验设计</h2><p>核对数据、样本划分、任务、指标与对比设置</p></div></div><div class="experiment-grid">']
    for i, dataset in enumerate(datasets, 1):
        if isinstance(dataset, dict):
            out.append(
                f'<article class="experiment-card"><h3>数据集 {i}：{term_text(dataset.get("name", ""), glossary)}</h3>'
                f'{info_rows([(k.replace("_", " "), v) for k, v in dataset.items() if k != "name"], glossary)}</article>'
            )
        else:
            out.append(f'<article class="experiment-card"><h3>数据集 {i}</h3><p>{term_text(dataset, glossary)}</p></article>')
    if not datasets:
        out.append('<article class="experiment-card"><h3>数据集</h3><p class="empty-note">未报告或尚未填写。</p></article>')
    out.append(f'<article class="experiment-card"><h3>实验设置</h3>{info_rows(rows, glossary)}</article>')
    out.append('</div></section>')
    return "".join(out)


def render_results(results: list, glossary: dict) -> str:
    if not results:
        return ""
    out = ['<section class="section" id="results"><div class="section-head"><span>07</span><div><h2>实验结果</h2><p>解释数值、比较对象和结果能够支持的结论</p></div></div><div class="result-grid">']
    for item in results:
        if not isinstance(item, dict):
            continue
        out.append(
            f'<article class="result-card"><h3>{term_text(item.get("metric", item.get("id", "结果")), glossary)}</h3>'
            f'<div class="result-value">{term_text(item.get("value", ""), glossary)}'
            f'{(" " + esc(item.get("unit"))) if item.get("unit") else ""}</div>'
            f'{info_rows([("实验", item.get("experiment_id")), ("对应发现", item.get("finding_id")), ("比较", item.get("comparison")), ("解释", item.get("interpretation")), ("注意事项", item.get("caveat"))], glossary)}'
            f'{source_refs_html(item.get("source_ref"), glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def image_data(image_asset: Any, data_dir: Path) -> tuple[str | None, str | None]:
    if isinstance(image_asset, dict):
        image_asset = image_asset.get("path") or image_asset.get("file") or image_asset.get("uri")
    if not image_asset:
        return None, "未提供 image_asset"
    value = str(image_asset)
    if value.startswith("data:image/"):
        return value, None
    path = Path(value)
    if not path.is_absolute():
        path = data_dir / path
    if not path.is_file():
        return None, f"图片文件不存在：{path}"
    mime = IMAGE_MIMES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
    if mime not in IMAGE_MIMES.values():
        return None, f"不支持的图片格式：{path.suffix}"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}", None


def panel_rect(panel: dict) -> list[float] | None:
    coords = panel.get("hotspot_coordinates", panel.get("rect"))
    if isinstance(coords, dict):
        coords = [coords.get("x0"), coords.get("y0"), coords.get("x1"), coords.get("y1")]
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        return None
    try:
        rect = [float(x) for x in coords]
    except (TypeError, ValueError):
        return None
    if not (0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1):
        return None
    return rect


def render_figures(figures: list, data_dir: Path, glossary: dict, strict_images: bool):
    images, panels_map, meta_map = {}, {}, {}
    out = ['<section class="section" id="figures"><div class="section-head"><span>08</span><div><h2>原文图表与逐子图解释</h2><p>点击图表后，再选择子图查看解释；图片与页面资源均内嵌</p></div></div><div class="figure-grid">']
    warnings = []
    for i, fig in enumerate(figures, 1):
        if not isinstance(fig, dict):
            continue
        number = str(fig.get("figure_number") or fig.get("id") or i)
        key = str(fig.get("id") or number)
        data_url, error = image_data(fig.get("image_asset"), data_dir)
        if error:
            message = f"Figure {number}: {error}"
            if strict_images:
                raise ValueError(message)
            warnings.append(message)
            continue
        panel_payload = []
        for j, panel in enumerate(as_list(fig.get("panels")), 1):
            if not isinstance(panel, dict):
                continue
            rect = panel_rect(panel)
            if rect is None:
                warnings.append(f"Figure {number}, panel {j}: hotspot_coordinates 缺失或不在 0–1 范围，已跳过该热点。")
                continue
            label = panel.get("original_label") or panel.get("hotspot_label") or panel.get("id") or chr(96 + j)
            panel_payload.append({
                "letter": str(label),
                "rect": rect,
                "title": panel.get("title") or panel.get("hotspot_label") or f"子图 {label}",
                "purpose": display(panel.get("purpose", "")),
                "how": display(panel.get("how_to_read", "")),
                "result": display(panel.get("observations", "")),
                "significance": display(panel.get("argument_supported", "")),
                "limit": display(panel.get("evidence_boundary", "")),
                "source": source_text(panel.get("source_ref", "")),
            })
        images[key] = data_url
        panels_map[key] = panel_payload
        meta_map[key] = {
            "caption": display(fig.get("caption", f"Figure {number}")),
            "page": display(fig.get("page", "")),
        }
        out.append(
            f'<article class="figure-card"><div class="figure-kicker">FIGURE {esc(number)}</div>'
            f'<h3>{term_text(fig.get("caption", f"Figure {number}"), glossary)}</h3>'
            f'<p>{term_text(fig.get("page", ""), glossary)}</p>'
            f'<button class="primary-btn" type="button" data-fig="{esc(key)}">打开原图并查看子图</button>'
            f'<span class="panel-count">{len(panel_payload)} 个可点击子图</span></article>'
        )
    if not images:
        out.append('<p class="empty-note">当前没有可展示的原文图片。请检查 figures[].image_asset 路径及图片文件。</p>')
    out.append('</div></section>')
    return "".join(out), images, panels_map, meta_map, warnings


def render_review(review: list, glossary: dict) -> str:
    if not review:
        return ""
    out = ['<section class="section" id="review"><div class="section-head"><span>09</span><div><h2>审稿人视角评价</h2><p>问题判断必须有论文证据，建议不能写成作者已完成的工作</p></div></div><div class="review-grid">']
    for item in review:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity", "")
        out.append(
            f'<article class="review-card"><div class="review-top"><h3>{term_text(item.get("issue", ""), glossary)}</h3>'
            f'<span class="severity">{esc(severity)}</span></div>'
            f'{info_rows([("论文依据", item.get("evidence")), ("为何重要", item.get("why_it_matters")), ("影响的结论", item.get("affected_claim")), ("建议验证", item.get("suggested_validation")), ("信息性质", item.get("information_type"))], glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_transfer(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="transfer"><div class="section-head"><span>10</span><div><h2>对用户研究的迁移启发</h2><p>区分可直接借鉴、需要改造和不宜直接迁移的内容</p></div></div><div class="transfer-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        relation = RELATION_LABELS.get(item.get("transferability"), item.get("transferability", ""))
        out.append(
            f'<article class="transfer-card"><span class="relation">{esc(relation)}</span>'
            f'<h3>{term_text(item.get("idea", ""), glossary)}</h3>'
            f'{info_rows([("原因", item.get("why")), ("需要调整", item.get("required_changes")), ("可形成的研究问题", item.get("research_question")), ("信息性质", item.get("information_type"))], glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_unresolved(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="unresolved"><div class="section-head"><span>11</span><div><h2>尚待核实的问题</h2><p>明确指出材料缺口，不用推测补齐</p></div></div><div class="unresolved-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append(
            f'<article class="unresolved-card"><h3>{term_text(item.get("question", ""), glossary)}</h3>'
            f'{info_rows([("尚未解决的原因", item.get("why_unresolved")), ("需要的材料", item.get("needed_material")), ("影响", item.get("impact"))], glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_main(data: dict, glossary: dict, figures_html: str) -> str:
    meta = data.get("paper_metadata", {})
    title = meta.get("title", "Untitled paper")
    subtitle = meta.get("subtitle", "")
    authors = meta.get("authors", [])
    author_text = "、".join(display(x) for x in as_list(authors) if display(x))
    citation = " · ".join(x for x in [
        author_text,
        display(meta.get("journal", "")),
        display(meta.get("year", "")),
        display(meta.get("doi", "")),
    ] if x)
    if meta.get("citation_note"):
        citation = " · ".join(x for x in [citation, display(meta["citation_note"])] if x)

    nav = [
        ("reading-guide", "阅读导览"),
        ("findings", "核心发现"),
        ("finding-links", "发现—方法关联"),
        ("method-tree", "方法分叉树"),
        ("equations", "公式"),
        ("experiments", "实验设计"),
        ("results", "实验结果"),
        ("figures", "原文图表"),
        ("review", "审稿评价"),
        ("transfer", "迁移启发"),
        ("unresolved", "待核实问题"),
    ]
    parts = ['<main class="page"><header class="hero">']
    if subtitle:
        parts.append(f'<div class="subtitle">{term_text(subtitle, glossary)}</div>')
    parts.append(f'<h1>{term_text(title, glossary)}</h1>')
    if citation:
        parts.append(f'<p class="citation">{term_text(citation, glossary)}</p>')
    if data.get("_converted_from_legacy"):
        parts.append('<p class="legacy-note">本页面由旧版 JSON 自动转换。缺少的研究导览、实验及审稿信息没有自动编造，请补充原文证据。</p>')
    parts.append('</header><nav class="nav">')
    for anchor, label in nav:
        parts.append(f'<a href="#{anchor}">{esc(label)}</a>')
    parts.append('</nav>')
    guide = data.get("reading_guide") or {}
    parts.append(render_reading_guide(guide, glossary))
    parts.append(render_findings(as_list(data.get("key_findings")), glossary))
    parts.append(render_finding_links(as_list(data.get("finding_method_links")), glossary))
    parts.append(render_method_tree(data.get("method_tree") or {}, glossary))
    parts.append(render_equations(as_list(data.get("equations")), glossary))
    parts.append(render_experiments(data.get("experiments") or {}, glossary))
    parts.append(render_results(as_list(data.get("results")), glossary))
    parts.append(figures_html)
    parts.append(render_review(as_list(data.get("reviewer_assessment")), glossary))
    parts.append(render_transfer(as_list(data.get("transfer_insights")), glossary))
    parts.append(render_unresolved(as_list(data.get("unresolved_questions")), glossary))
    scope = data.get("source_scope") or {}
    if scope:
        parts.append(
            '<section class="section source-scope"><div class="section-head"><span>INFO</span><div><h2>材料范围与阅读说明</h2></div></div>'
            + info_rows([
                ("是否阅读全文", scope.get("full_text_read")),
                ("使用材料", scope.get("materials_used")),
                ("已检查页码", scope.get("pages_reviewed")),
                ("材料局限", scope.get("limitations")),
            ], glossary)
            + '</section>'
        )
    parts.append('</main>')
    return "".join(parts)


def safe_json(value: Any) -> str:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def build_document(data: dict, data_dir: Path, output_path: Path, strict_images: bool = False) -> list[str]:
    data = normalize_legacy_data(data)
    validate_data(data)
    glossary = normalize_glossary(data.get("glossary", []))
    figures_html, images, panels, meta, warnings = render_figures(
        as_list(data.get("figures")), data_dir, glossary, strict_images
    )
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(
            f"找不到 HTML 模板：{TEMPLATE_PATH}。请将 reader.html 放入仓库 templates/ 目录。"
        )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__PAGE_TITLE__": esc(data.get("page_title") or data["paper_metadata"]["title"]),
        "__MAIN__": render_main(data, glossary, figures_html),
        "__GLOSSARY_JSON__": safe_json({
            term: {
                "full_name": item.get("full_name", ""),
                "chinese_translation": item.get("chinese_translation", ""),
                "meaning_in_this_paper": item.get("meaning_in_this_paper", ""),
                "role": item.get("role", ""),
                "distinction": item.get("distinction", ""),
            } for term, item in glossary.items()
        }),
        "__FIGURE_IMAGES_JSON__": safe_json(images),
        "__FIGURE_PANELS_JSON__": safe_json(panels),
        "__FIGURE_META_JSON__": safe_json(meta),
    }
    for placeholder, content in replacements.items():
        if placeholder not in template:
            raise ValueError(f"HTML 模板缺少占位符：{placeholder}")
        template = template.replace(placeholder, content)
    if "__" in template and re.search(r"__[A-Z][A-Z0-9_]+__", template):
        raise ValueError("HTML 模板仍有未替换的占位符。")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding="utf-8")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline interactive Literature Reader HTML.")
    parser.add_argument("data", type=Path, help="论文分析 JSON 文件")
    parser.add_argument("output", type=Path, help="输出 HTML 文件")
    parser.add_argument("--strict-images", action="store_true",
                        help="图片缺失或格式错误时直接报错；默认跳过缺失图片并给出警告")
    args = parser.parse_args()

    data_path = args.data.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        warnings = build_document(data, data_path.parent, output_path, args.strict_images)
        print(f"Created: {output_path} ({output_path.stat().st_size / 1024:.1f} KiB)")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
