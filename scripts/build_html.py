#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a self-contained, offline Literature Reader HTML from JSON.

Python 3.9+, standard library only.
Usage:
  python scripts/build_html.py analysis.json output.html
  python scripts/build_html.py analysis.json output.html --strict-images
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "reader.html"
RELATIONS = {
    "sequence": "顺序关系",
    "composition": "组成关系",
    "parallel": "并列关系",
    "validation": "验证关系",
    "support": "辅助关系",
    "direct": "可直接借鉴",
    "adaptation_required": "需要改造",
    "not_directly_transferable": "不宜直接迁移",
}
PALETTE = ["#6fc4e8", "#a7c7a0", "#d5a6e8", "#e5b77d", "#7fbed0", "#e28f9b"]


def esc(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def source_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [value.get("locator"), value.get("quote_or_evidence"), value.get("url_or_file")]
        return "；".join(str(x) for x in parts if x not in (None, ""))
    if isinstance(value, list):
        return "；".join(source_text(x) for x in value if x not in (None, ""))
    return str(value)


def normalize_glossary(items: Any) -> dict[str, dict]:
    result = {}
    if isinstance(items, dict):
        for term, values in items.items():
            values = as_list(values)
            values = (values + ["", "", "", ""])[:4]
            result[str(term)] = {
                "full_name": values[0], "chinese_translation": values[1],
                "meaning_in_this_paper": values[2], "role": values[3],
                "distinction": "", "source_ref": ""
            }
    else:
        for item in as_list(items):
            if isinstance(item, dict) and item.get("term"):
                result[str(item["term"])] = item
    return result


def term_text(value: Any, glossary: dict[str, dict]) -> str:
    raw = display(value)
    if not raw or not glossary:
        return esc(raw)
    terms = sorted(glossary.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE)
    lookup = {t.casefold(): t for t in terms}
    out, cursor = [], 0
    for match in pattern.finditer(raw):
        key = lookup.get(match.group(0).casefold())
        if not key:
            continue
        out.append(esc(raw[cursor:match.start()]))
        out.append(f'<button class="term" type="button" data-term="{esc(key)}">{esc(match.group(0))}</button>')
        cursor = match.end()
    out.append(esc(raw[cursor:]))
    return "".join(out)


def info_rows(items: list[tuple[str, Any]], glossary: dict) -> str:
    out = []
    for label, value in items:
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            value = "；".join(display(x) for x in value)
        out.append(f'<div class="info-row"><strong>{esc(label)}</strong><span>{term_text(value, glossary)}</span></div>')
    return "".join(out)


def source_html(refs: Any, glossary: dict) -> str:
    text = source_text(refs)
    if not text:
        return ""
    return f'<div class="source-ref"><b>原文定位</b>{term_text(text, glossary)}</div>'


def stable_color(group: str) -> str:
    digest = hashlib.sha1(group.encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def normalize_legacy_data(data: dict) -> dict:
    """Convert old heading/nodes/terms/figures JSON while preserving its available content."""
    if "paper_metadata" in data:
        return data
    if "heading" not in data or "nodes" not in data:
        return data

    heading = as_list(data.get("heading"))
    title = heading[-1] if heading else data.get("page_title", "Untitled paper")
    metadata = {
        "title": title, "subtitle": heading[0] if len(heading) > 1 else "",
        "authors": [], "journal": "", "year": None, "doi": "",
        "source_file": "", "citation_note": data.get("citation", "")
    }
    findings, method_nodes, links = [], [], []
    for i, old_node in enumerate(as_list(data.get("nodes")), 1):
        if not isinstance(old_node, dict):
            continue
        fid = f"finding-{i}"
        branch_ids = []
        for j, branch in enumerate(as_list(old_node.get("branches")), 1):
            if not isinstance(branch, dict):
                continue
            bid = f"{fid}-branch-{j}"
            branch_ids.append(bid)
            method_nodes.append({
                "id": bid, "parent_id": None,
                "name": branch.get("title", f"方法分支 {j}"),
                "description": branch.get("goal", ""),
                "input": "", "operation": branch.get("goal", ""), "output": "",
                "purpose": branch.get("goal", ""),
                "relationship_type": old_node.get("branch_relation", "parallel"),
                "source_refs": [old_node.get("evidence", "")] if old_node.get("evidence") else [],
                "sibling_color_group": f"{fid}-branches",
                "legacy_label": branch.get("label", ""),
                "legacy_level": branch.get("level", None)
            })
            for k, item in enumerate(as_list(branch.get("items")), 1):
                if not isinstance(item, dict):
                    continue
                method_nodes.append({
                    "id": f"{bid}-method-{k}", "parent_id": bid,
                    "name": item.get("name", f"方法 {k}"),
                    "description": item.get("core", ""),
                    "input": item.get("input", ""),
                    "operation": item.get("steps", ""),
                    "output": item.get("effect", ""),
                    "purpose": item.get("effect", ""),
                    "relationship_type": item.get("role", "support"),
                    "source_refs": [item.get("source", "")] if item.get("source") else [],
                    "sibling_color_group": f"{bid}-methods",
                    "legacy_difference": item.get("difference", ""),
                    "legacy_limit": item.get("limit", ""),
                    "legacy_details": item
                })
        findings.append({
            "id": fid, "title": old_node.get("title", f"研究发现 {i}"),
            "finding": old_node.get("desc", ""),
            "quantitative_result": "",
            "evidence_refs": [x for x in [old_node.get("page"), old_node.get("evidence")] if x],
            "supporting_methods": branch_ids, "experiment_refs": [],
            "evidence_boundary": old_node.get("limit", ""),
            "information_type": "paper_original"
        })
        links.append({
            "finding_id": fid, "method_ids": branch_ids,
            "experiment_ids": [],
            "figure_panel_refs": [str(old_node.get("figure"))] if old_node.get("figure") else [],
            "relationship_type": old_node.get("branch_relation", "parallel"),
            "explanation": old_node.get("evidence", "")
        })

    figures = []
    old_figures = data.get("figures", {})
    if isinstance(old_figures, dict):
        for number, figure in old_figures.items():
            if not isinstance(figure, dict):
                continue
            panels = []
            for index, panel in enumerate(as_list(figure.get("panels")), 1):
                if not isinstance(panel, dict):
                    continue
                panels.append({
                    "id": str(panel.get("letter", index)),
                    "original_label": panel.get("letter", str(index)),
                    "hotspot_label": panel.get("letter", str(index)),
                    "hotspot_coordinates": panel.get("rect"),
                    "title": panel.get("title", ""),
                    "purpose": panel.get("purpose", ""),
                    "how_to_read": panel.get("how", ""),
                    "observations": panel.get("result", ""),
                    "argument_supported": panel.get("significance", ""),
                    "evidence_boundary": panel.get("limit", ""),
                    "source_ref": panel.get("source", ""),
                    "confidence": "legacy"
                })
            figures.append({
                "id": str(number), "figure_number": str(number), "page": "",
                "image_asset": figure.get("image", ""),
                "caption": figure.get("source", f"Fig. {number}"), "panels": panels
            })

    glossary = []
    old_terms = data.get("terms", {})
    if isinstance(old_terms, dict):
        for term, values in old_terms.items():
            values = as_list(values)
            values = (values + ["", "", "", ""])[:4]
            glossary.append({
                "term": term, "full_name": values[0],
                "chinese_translation": values[1],
                "meaning_in_this_paper": values[2], "role": values[3]
            })

    return {
        "paper_metadata": metadata,
        "source_scope": {
            "full_text_read": None,
            "materials_used": ["由旧版 JSON 自动转换；请核对原始材料范围"],
            "pages_reviewed": [],
            "limitations": "旧版 JSON 不包含完整的新 schema 字段。未提供的研究导览、实验设计和审稿评价不会自动补造。"
        },
        "reading_guide": {"research_question": {}, "prior_work": [], "core_intuition": {}},
        "key_findings": findings, "finding_method_links": links,
        "method_tree": {"root": "旧版研究发现对应的方法分支", "nodes": method_nodes},
        "equations": [], "experiments": {}, "results": [], "figures": figures,
        "reviewer_assessment": [], "transfer_insights": [], "glossary": glossary,
        "unresolved_questions": [{
            "question": "新版阅读导览、实验设计及审稿评价尚未补充",
            "why_unresolved": "旧版 JSON 不含这些字段",
            "needed_material": "论文全文及补充材料",
            "impact": "不能将空缺内容当作论文已经分析过"
        }],
        "_converted_from_legacy": True
    }


def validate_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是 object。")
    if not isinstance(data.get("paper_metadata"), dict):
        raise ValueError("缺少 paper_metadata；请使用 templates/paper-analysis-template.json。")
    if not str(data["paper_metadata"].get("title", "")).strip():
        raise ValueError("paper_metadata.title 不能为空。")
    for key in ("key_findings", "finding_method_links", "equations", "results",
                "figures", "reviewer_assessment", "transfer_insights", "unresolved_questions"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"{key} 必须是数组。")
    tree = data.get("method_tree", {})
    if not isinstance(tree, dict) or not isinstance(tree.get("nodes", []), list):
        raise ValueError("method_tree.nodes 必须是数组。")


def render_guide(guide: dict, glossary: dict) -> str:
    rq = guide.get("research_question") or {}
    core = guide.get("core_intuition") or {}
    prior_items = []
    for item in as_list(guide.get("prior_work")):
        if not isinstance(item, dict):
            continue
        prior_items.append(
            '<article class="prior-item">'
            f'<h4>{term_text(item.get("research_route", "研究路线"), glossary)}</h4>'
            f'<p>{term_text(item.get("typical_approach", ""), glossary)}</p>'
            f'{info_rows([("能够解决", item.get("what_it_solves")), ("局限", item.get("limitations")), ("本文切入点", item.get("paper_entry_point"))], glossary)}'
            f'{source_html(item.get("evidence_refs"), glossary)}</article>'
        )
    cards = [
        ("研究问题", info_rows([
            ("研究对象", rq.get("object")), ("要解决的问题", rq.get("problem")),
            ("为什么重要", rq.get("why_important")), ("预期价值", rq.get("expected_value"))
        ], glossary)),
        ("前人工作", "".join(prior_items) or '<p class="empty-note">当前材料未提供前人工作路线；请根据 Introduction / Related Work 补充。不得凭空补写。</p>'),
        ("核心直觉", info_rows([
            ("通俗解释", core.get("plain_language")),
            ("关键观察", core.get("key_observation")),
            ("方法为何适用", core.get("why_method_fits"))
        ], glossary))
    ]
    out = ['<section id="reading-guide"><div class="guide-grid">']
    for title, body in cards:
        out.append(f'<article class="guide-card"><h3>{title}</h3>{body}</article>')
    out.append('</div></section>')
    return "".join(out)


def render_findings(items: list, glossary: dict) -> str:
    out = ['<section class="section" id="findings"><div class="section-head"><span>01</span><div><h2>核心研究发现</h2><p>每项发现都应能追溯到方法、实验和原文证据</p></div></div><div class="finding-grid">']
    valid = [x for x in items if isinstance(x, dict)]
    if not valid:
        out.append('<p class="empty-note">尚未填写核心研究发现。</p>')
    for i, item in enumerate(valid, 1):
        out.append(
            f'<article class="finding-card"><div class="finding-no">F{i:02d}</div>'
            f'<h3>{term_text(item.get("title", ""), glossary)}</h3>'
            f'<p>{term_text(item.get("finding", ""), glossary)}</p>'
            f'{info_rows([("定量结果", item.get("quantitative_result")), ("支撑方法", item.get("supporting_methods")), ("证据边界", item.get("evidence_boundary"))], glossary)}'
            f'{source_html(item.get("evidence_refs"), glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_links(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="finding-links"><div class="section-head"><span>02</span><div><h2>研究发现与方法、实验的对应关系</h2><p>区分顺序、组成、并列、验证和辅助关系</p></div></div><div class="link-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        rel = RELATIONS.get(item.get("relationship_type"), item.get("relationship_type", ""))
        out.append(
            f'<article class="link-card"><span class="relation">{esc(rel)}</span>'
            f'<h3>发现：{term_text(item.get("finding_id", ""), glossary)}</h3>'
            f'<p>{term_text(item.get("explanation", ""), glossary)}</p>'
            f'{info_rows([("方法节点", item.get("method_ids")), ("实验节点", item.get("experiment_ids")), ("图表证据", item.get("figure_panel_refs"))], glossary)}</article>'
        )
    out.append('</div></section>')
    return "".join(out)


def render_method_tree(tree: dict, glossary: dict) -> str:
    nodes = tree.get("nodes", []) if isinstance(tree, dict) else []
    if not nodes:
        return ""
    by_id = {str(n.get("id")): n for n in nodes if isinstance(n, dict) and n.get("id") is not None}
    children, roots = {}, []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        parent = node.get("parent_id")
        if parent is None or str(parent) not in by_id:
            roots.append(node)
        else:
            children.setdefault(str(parent), []).append(node)

    def node_html(node: dict, depth: int, trail: set[str]) -> str:
        nid = str(node.get("id", ""))
        if nid in trail:
            return '<article class="method-node"><b>检测到循环引用，请检查 parent_id。</b></article>'
        next_trail = set(trail); next_trail.add(nid)
        group = str(node.get("sibling_color_group") or node.get("parent_id") or "root")
        color = stable_color(group)
        rel = RELATIONS.get(node.get("relationship_type"), node.get("relationship_type", ""))
        details = info_rows([
            ("输入", node.get("input")), ("处理 / 操作", node.get("operation")),
            ("输出", node.get("output")), ("作用", node.get("purpose")),
            ("旧版差异说明", node.get("legacy_difference")),
            ("旧版局限说明", node.get("legacy_limit"))
        ], glossary)
        kids = "".join(node_html(child, depth + 1, next_trail) for child in children.get(nid, []))
        return (
            f'<article class="method-node" data-depth="{min(depth,5)}" style="--node-accent:{color}">'
            f'<div class="method-node-head"><h3>{term_text(node.get("name", ""), glossary)}</h3><span class="relation">{esc(rel)}</span></div>'
            f'<p>{term_text(node.get("description", ""), glossary)}</p>{details}'
            f'{source_html(node.get("source_refs"), glossary)}'
            f'{"<div class=method-children>"+kids+"</div>" if kids else ""}</article>'
        )

    out = ['<section class="section" id="method-tree"><div class="section-head"><span>03</span><div><h2>方法分叉树</h2><p>颜色区分同级分支；只有原文支持时才表达先后关系</p></div></div>']
    if tree.get("root"):
        out.append(f'<div class="tree-root">{term_text(tree["root"], glossary)}</div>')
    out.append('<div class="method-tree-grid">')
    out.extend(node_html(n, 1, set()) for n in roots)
    out.append('</div></section>')
    return "".join(out)


def render_equations(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="equations"><div class="section-head"><span>04</span><div><h2>关键公式</h2><p>保留原式，并解释变量、单位和方法位置</p></div></div>']
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append('<article class="equation-card">')
        out.append(f'<h3>{term_text(item.get("equation_number") or item.get("id") or "公式", glossary)}</h3>')
        if item.get("original_expression"):
            out.append(f'<div class="equation-expression">{esc(item["original_expression"])}</div>')
        out.append(f'<p>{term_text(item.get("plain_language", ""), glossary)}</p>')
        out.append(info_rows([("变量", item.get("variables")), ("输入", item.get("input")), ("输出", item.get("output")), ("方法作用", item.get("role_in_method")), ("不确定性", item.get("uncertainties"))], glossary))
        out.append(source_html(item.get("source_ref"), glossary))
        out.append('</article>')
    out.append('</section>')
    return "".join(out)


def render_experiments(experiments: dict, glossary: dict) -> str:
    if not experiments:
        return ""
    body = info_rows([
        ("数据集", experiments.get("datasets")), ("数据划分", experiments.get("data_splits")),
        ("任务定义", experiments.get("tasks")), ("预测窗口", experiments.get("prediction_horizon")),
        ("评价指标", experiments.get("metrics")), ("对比基线", experiments.get("baselines")),
        ("超参数", experiments.get("hyperparameters")),
        ("可复现说明", experiments.get("reproducibility_notes"))
    ], glossary)
    if not body:
        return ""
    return f'<section class="section" id="experiments"><div class="section-head"><span>05</span><div><h2>实验设计</h2><p>数据、划分、任务、指标、基线与复现条件</p></div></div><article class="info-panel">{body}</article></section>'


def render_results(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="results"><div class="section-head"><span>06</span><div><h2>实验结果</h2><p>解释数值、比较对象和结果边界</p></div></div><div class="result-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append('<article class="result-card">')
        out.append(f'<h3>{term_text(item.get("metric") or item.get("id") or "结果", glossary)}</h3>')
        out.append(info_rows([
            ("数值", item.get("value")), ("单位", item.get("unit")),
            ("比较", item.get("comparison")), ("解释", item.get("interpretation")),
            ("注意事项", item.get("caveat"))
        ], glossary))
        out.append(source_html(item.get("source_ref"), glossary))
        out.append('</article>')
    out.append('</div></section>')
    return "".join(out)


def image_data_uri(asset: str, json_dir: Path) -> tuple[str | None, str | None]:
    if not asset:
        return None, "未提供 image_asset"
    if re.match(r"^https?://", str(asset), re.I):
        return None, "不接受远程图片；请下载图片并使用本地相对路径以保证离线"
    path = Path(asset)
    if not path.is_absolute():
        path = json_dir / path
    if not path.exists() or not path.is_file():
        return None, f"图片不存在：{path}"
    mime = mimetypes.guess_type(path.name)[0] or {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".gif": "image/gif"
    }.get(path.suffix.lower())
    if not mime or not mime.startswith("image/"):
        return None, f"不支持的图片格式：{path.suffix}"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}", None


def valid_rect(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    try:
        x0, y0, x1, y1 = [float(x) for x in value]
    except (TypeError, ValueError):
        return False
    return 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1


def render_figures(items: list, glossary: dict, json_dir: Path, strict_images: bool, warnings: list) -> tuple[str, dict]:
    if not items:
        return "", {}
    out = ['<section class="section" id="figures"><div class="section-head"><span>07</span><div><h2>原文图表与逐子图解读</h2><p>点击子图边框显示解释；点击原图可放大</p></div></div>']
    interaction = {}
    for idx, fig in enumerate(items, 1):
        if not isinstance(fig, dict):
            continue
        fid = str(fig.get("id") or fig.get("figure_number") or idx)
        uri, warning = image_data_uri(str(fig.get("image_asset") or ""), json_dir)
        if warning:
            warnings.append(f"Figure {fid}: {warning}")
            if strict_images:
                raise ValueError(f"Figure {fid}: {warning}")
        caption = fig.get("caption") or f'Figure {fig.get("figure_number", fid)}'
        out.append('<article class="figure-card">')
        out.append(f'<div class="figure-head"><div><h3>{term_text(caption, glossary)}</h3><p>页码：{esc(fig.get("page") or "未标注")}</p></div></div>')
        panel_map = {}
        if uri:
            out.append('<div class="figure-image-wrap">')
            out.append(f'<img class="figure-image" src="{uri}" alt="{esc(caption)}" data-zoom="{uri}" data-alt="{esc(caption)}">')
            out.append('<div class="hotspot-layer">')
            for pidx, panel in enumerate(as_list(fig.get("panels")), 1):
                if not isinstance(panel, dict):
                    continue
                pid = str(panel.get("id") or panel.get("original_label") or pidx)
                rect = panel.get("hotspot_coordinates")
                if not valid_rect(rect):
                    warnings.append(f"Figure {fid}, panel {pid}: hotspot_coordinates 缺失或不在 0–1 范围内，未生成热点。")
                    continue
                x0,y0,x1,y1 = [float(x) for x in rect]
                label = panel.get("hotspot_label") or panel.get("original_label") or pid
                style = f"left:{x0*100:.4f}%;top:{y0*100:.4f}%;width:{(x1-x0)*100:.4f}%;height:{(y1-y0)*100:.4f}%"
                out.append(f'<button class="hotspot" type="button" data-figure="{esc(fid)}" data-panel="{esc(pid)}" style="{style}" aria-label="查看子图 {esc(label)} 解读" aria-expanded="false"><span>{esc(label)}</span></button>')
                panel_map[pid] = {
                    "hotspot_label": label, "original_label": panel.get("original_label", ""),
                    "title": panel.get("title", ""), "purpose": panel.get("purpose", ""),
                    "how_to_read": panel.get("how_to_read", ""),
                    "observations": panel.get("observations", ""),
                    "argument_supported": panel.get("argument_supported", ""),
                    "evidence_boundary": panel.get("evidence_boundary", ""),
                    "source_ref": panel.get("source_ref", "")
                }
            out.append('</div></div>')
        else:
            out.append('<p class="empty-note">未显示原图。请检查图片路径；图片缺失不会生成破损图片链接。</p>')
        out.append(f'<div class="panel-detail" id="detail-{esc(fid)}" hidden></div>')
        out.append('</article>')
        interaction[fid] = {"panels": panel_map}
    out.append('</section>')
    return "".join(out), interaction


def render_review(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="review"><div class="section-head"><span>08</span><div><h2>审稿人视角评价</h2><p>指出证据支持程度与可补充的验证</p></div></div><div class="review-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append('<article class="review-card">')
        out.append(f'<h3>{term_text(item.get("issue", "评价事项"), glossary)}</h3>')
        out.append(info_rows([
            ("原文依据", item.get("evidence")), ("重要性", item.get("why_it_matters")),
            ("影响的主张", item.get("affected_claim")),
            ("建议验证", item.get("suggested_validation")),
            ("严重程度", item.get("severity")), ("信息类型", item.get("information_type"))
        ], glossary))
        out.append('</article>')
    out.append('</div></section>')
    return "".join(out)


def render_transfer(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="transfer"><div class="section-head"><span>09</span><div><h2>研究思路迁移</h2><p>区分可直接借鉴、需要改造和不宜直接迁移</p></div></div><div class="transfer-grid">']
    for item in items:
        if not isinstance(item, dict):
            continue
        label = RELATIONS.get(item.get("transferability"), item.get("transferability", ""))
        out.append('<article class="transfer-card">')
        out.append(f'<span class="relation">{esc(label)}</span><h3>{term_text(item.get("idea", ""), glossary)}</h3>')
        out.append(info_rows([
            ("为什么", item.get("why")), ("需要改造", item.get("required_changes")),
            ("可形成的问题", item.get("research_question")),
            ("信息类型", item.get("information_type"))
        ], glossary))
        out.append('</article>')
    out.append('</div></section>')
    return "".join(out)


def render_unresolved(items: list, glossary: dict) -> str:
    if not items:
        return ""
    out = ['<section class="section" id="unresolved"><div class="section-head"><span>10</span><div><h2>待核实问题</h2><p>材料不足或论文未明确说明的事项</p></div></div>']
    for item in items:
        if not isinstance(item, dict):
            continue
        out.append('<article class="unresolved-card">')
        out.append(f'<h3>{term_text(item.get("question", ""), glossary)}</h3>')
        out.append(info_rows([
            ("尚未解决原因", item.get("why_unresolved")),
            ("需要的材料", item.get("needed_material")),
            ("影响", item.get("impact"))
        ], glossary))
        out.append('</article>')
    out.append('</section>')
    return "".join(out)


def render_scope(scope: dict, glossary: dict) -> str:
    if not scope:
        return ""
    body = info_rows([
        ("是否阅读全文", scope.get("full_text_read")),
        ("使用材料", scope.get("materials_used")),
        ("已检查页码", scope.get("pages_reviewed")),
        ("材料局限", scope.get("limitations"))
    ], glossary)
    if not body:
        return ""
    return f'<section class="section"><div class="section-head"><span>INFO</span><div><h2>材料范围与阅读说明</h2></div></div><article class="info-panel">{body}</article></section>'


def render_page(data: dict, json_path: Path, strict_images: bool = False) -> tuple[str, list[str]]:
    warnings = []
    glossary = normalize_glossary(data.get("glossary"))
    meta = data.get("paper_metadata", {})
    title = term_text(meta.get("title", "Untitled paper"), glossary)
    parts = ['<header class="hero"><h1>', title, '</h1></header>']

    # Requirement: guide cards are immediately below the title, before bibliographic metadata.
    parts.append(render_guide(data.get("reading_guide") or {}, glossary))

    authors = "、".join(display(x) for x in as_list(meta.get("authors")) if display(x))
    citation_items = [authors, meta.get("journal"), meta.get("year"), meta.get("volume"), meta.get("issue"), meta.get("pages")]
    citation = " · ".join(esc(x) for x in citation_items if x not in (None, ""))
    doi = str(meta.get("doi") or "").strip()
    if doi:
        citation += (' · ' if citation else '') + f'DOI: {esc(doi)}'
    if meta.get("citation_note"):
        citation += (' · ' if citation else '') + esc(meta["citation_note"])
    if citation:
        parts.append(f'<div class="metadata">{citation}</div>')

    if data.get("_converted_from_legacy"):
        parts.append('<p class="empty-note">本页面由旧版 JSON 自动转换。未在旧数据中出现的阅读导览、实验或评价信息没有自动补造，请根据论文原文补充。</p>')

    nav = [
        ("findings", "核心发现"), ("finding-links", "发现—方法关联"),
        ("method-tree", "方法分叉树"), ("equations", "公式"),
        ("experiments", "实验设计"), ("results", "实验结果"),
        ("figures", "原文图表"), ("review", "审稿评价"),
        ("transfer", "迁移启发"), ("unresolved", "待核实问题")
    ]
    parts.append('<nav class="nav">')
    for anchor, label in nav:
        parts.append(f'<a href="#{anchor}">{label}</a>')
    parts.append('</nav>')

    parts.append(render_findings(as_list(data.get("key_findings")), glossary))
    parts.append(render_links(as_list(data.get("finding_method_links")), glossary))
    parts.append(render_method_tree(data.get("method_tree") or {}, glossary))
    parts.append(render_equations(as_list(data.get("equations")), glossary))
    parts.append(render_experiments(data.get("experiments") or {}, glossary))
    parts.append(render_results(as_list(data.get("results")), glossary))
    figures_html, figure_data = render_figures(as_list(data.get("figures")), glossary, json_path.parent, strict_images, warnings)
    parts.append(figures_html)
    parts.append(render_review(as_list(data.get("reviewer_assessment")), glossary))
    parts.append(render_transfer(as_list(data.get("transfer_insights")), glossary))
    parts.append(render_unresolved(as_list(data.get("unresolved_questions")), glossary))
    parts.append(render_scope(data.get("source_scope") or {}, glossary))
    parts.append('<div class="footer-note">由 Literature Reader 生成。请以论文原文为准；分析者推断与待核实事项应与作者结论区分。</div>')

    template = TEMPLATE.read_text(encoding="utf-8")
    content = "".join(parts)
    payload = {"glossary": glossary, "figures": figure_data}
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("<!-- CONTENT -->", content).replace("<!-- DATA -->", payload_json)
    return html, warnings


def build(input_path: Path, output_path: Path, strict_images: bool = False) -> list[str]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if "paper_metadata" not in data and "heading" in data and "nodes" in data:
        data = normalize_legacy_data(data)
    validate_data(data)
    html, warnings = render_page(data, input_path.resolve(), strict_images)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_html", type=Path)
    parser.add_argument("--strict-images", action="store_true", help="缺失或无效图片时中止")
    args = parser.parse_args()
    if not args.input_json.exists():
        parser.error(f"输入 JSON 不存在：{args.input_json}")
    if not TEMPLATE.exists():
        parser.error(f"HTML 模板不存在：{TEMPLATE}")
    try:
        warnings = build(args.input_json, args.output_html, args.strict_images)
    except Exception as exc:
        print(f"构建失败：{exc}", file=sys.stderr)
        return 1
    for warning in warnings:
        print("警告：" + warning, file=sys.stderr)
    print(f"HTML 已生成：{args.output_html.resolve()}")
    print(f"文件大小：{args.output_html.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
