#!/usr/bin/env python3
"""Build a self-contained offline Literature Reader HTML from paper JSON.

Python 3.9+, standard library only. Figure images are embedded as data URLs.
"""
from __future__ import annotations

import argparse
import base64
from html import escape
import json
import mimetypes
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "reader.html"


def h(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def safe_json(value: object) -> str:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def assert_reviewer_view(view: object) -> None:
    if view is None:
        return  # Backward compatibility with old paper JSON.
    if not isinstance(view, dict):
        raise ValueError("reviewer_view must be an object")
    for key in ("research_question", "prior_work", "core_intuition"):
        if not isinstance(view.get(key), str) or not view[key].strip():
            raise ValueError(f"reviewer_view.{key} must be a nonempty string")
    example = view.get("worked_example")
    if not isinstance(example, dict):
        raise ValueError("reviewer_view.worked_example must be an object")
    for key in ("scenario", "input", "processing", "output", "interpretation"):
        if not isinstance(example.get(key), str) or not example[key].strip():
            raise ValueError(f"reviewer_view.worked_example.{key} must be a nonempty string")


def assert_data(data: dict, data_dir: Path) -> None:
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    if not isinstance(data.get("heading"), list) or not data["heading"]:
        raise ValueError("heading must be a nonempty array")
    assert_reviewer_view(data.get("reviewer_view"))
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("nodes must be a nonempty array")
    if data.get("navigation") and len(data["navigation"]) != len(nodes):
        raise ValueError("navigation and nodes must have the same length")
    figures = data.get("figures", {})
    if not isinstance(figures, dict):
        raise ValueError("figures must be a mapping of figure IDs to figure objects")
    for ni, node in enumerate(nodes, 1):
        if not isinstance(node, dict) or not node.get("title") or not node.get("desc"):
            raise ValueError(f"node {ni}: title and desc are required")
        relationship = node.get("branch_relation", "parallel")
        if relationship not in ("parallel", "sequence"):
            raise ValueError(f"node {ni}: branch_relation must be parallel or sequence")
        levels = [b.get("level", 1) for b in node.get("branches", [])]
        if relationship == "parallel" and len(set(levels)) > 1:
            raise ValueError(f"node {ni}: sibling branches of the same tree depth must share a level; use sequence only for source-supported sequential steps")
        if relationship == "sequence" and levels != sorted(levels):
            raise ValueError(f"node {ni}: sequence levels must be nondecreasing")
        for bi, branch in enumerate(node.get("branches", []), 1):
            if not branch.get("title"):
                raise ValueError(f"node {ni} branch {bi}: title is required")
            level = branch.get("level", 1)
            if isinstance(level, bool) or not isinstance(level, int) or not (1 <= level <= 4):
                raise ValueError(f"node {ni} branch {bi}: level must be an integer from 1 to 4")
            for mi, item in enumerate(branch.get("items", []), 1):
                for key in ("name", "core", "effect"):
                    if not item.get(key):
                        raise ValueError(f"node {ni} branch {bi} item {mi}: {key} is required")
        f = str(node.get("figure", ""))
        if f and f not in figures:
            raise ValueError(f"node {ni} references missing figure '{f}'")
    for number, fig in figures.items():
        p = Path(str(fig.get("image", "")))
        if not p.is_absolute():
            p = data_dir / p
        if not p.is_file():
            raise ValueError(f"figure {number}: image file not found: {p}")
        if not fig.get("panels"):
            print(f"Warning: figure {number} has no click regions", file=sys.stderr)
        letters = set()
        for pi, panel in enumerate(fig.get("panels", []), 1):
            letter = str(panel.get("letter", ""))
            if not letter or letter in letters:
                raise ValueError(f"figure {number}: panel {pi} letter missing/duplicated")
            letters.add(letter)
            rect = panel.get("rect")
            if (not isinstance(rect, list) or len(rect) != 4
                or not all(isinstance(v, (int, float)) for v in rect)
                or not (0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1)):
                raise ValueError(f"figure {number}{letter}: rect must be [x0,y0,x1,y1] normalized to 0..1")
            for required in ("title", "purpose", "how", "result", "significance", "limit", "source"):
                if required not in panel:
                    raise ValueError(f"figure {number}{letter}: missing {required}; use an empty string if the paper does not report it")
    terms = data.get("terms", {})
    if not isinstance(terms, dict):
        raise ValueError("terms must be an object")
    for term, arr in terms.items():
        if not (isinstance(arr, list) and len(arr) == 4 and all(isinstance(x, str) for x in arr)):
            raise ValueError(f"term {term}: definition must be four strings [full, chinese, explanation, use]")


def embed_images(figures: dict, data_dir: Path) -> tuple[dict, dict, dict]:
    images, panels, meta = {}, {}, {}
    supported = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".webp": "image/webp", ".gif": "image/gif"}
    for num, fig in figures.items():
        path = Path(fig["image"])
        if not path.is_absolute():
            path = data_dir / path
        mime = supported.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
        if mime not in supported.values():
            raise ValueError(f"figure {num}: use PNG, JPEG, WEBP or GIF; got {path.name}")
        images[str(num)] = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        panels[str(num)] = fig.get("panels", [])
        meta[str(num)] = {"source": fig.get("source", f"Fig. {num}")}
    return images, panels, meta


def details_row(title: str, value: object) -> str:
    if value is None or str(value) == "":
        return ""
    return f'<div class="drow"><strong>{h(title)}</strong>{h(value)}</div>'


def render_method(item: dict) -> str:
    detail_fields = [("输入对象", "input"), ("执行步骤", "steps"),
                     ("技术差异", "difference"), ("局限与边界", "limit"),
                     ("原文定位", "source")]
    lines = "".join(details_row(label, item.get(key, "")) for label, key in detail_fields)
    detail_html = (f'<button class="details-btn" type="button" aria-expanded="false">查看方法细节</button>'
                   f'<div class="details" hidden>{lines}</div>') if lines else ""
    return (f'<div class="method"><div class="role">{h(item.get("role", ""))}</div>'
            f'<h4>{h(item["name"])}</h4><p class="core">{h(item["core"])}</p>'
            f'<p class="effect">作用：{h(item["effect"])}</p>{detail_html}</div>')


def render_reviewer_view(view: dict | None) -> str:
    if not view:
        return ""
    cards = [
        ("01", "研究问题", view["research_question"]),
        ("02", "前人工作", view["prior_work"]),
        ("03", "核心直觉", view["core_intuition"]),
    ]
    out = ['<section class="reviewer-view" id="reviewer-view">']
    out.append('<div class="reviewer-intro"><span class="reviewer-kicker">REVIEWER\'S LENS</span>'
               '<h2>先理解研究逻辑，再进入技术细节</h2>'
               '<p>从研究动机、已有工作和核心思路出发，再用真实案例核对方法如何产生结果。</p></div>')
    out.append('<div class="reviewer-grid">')
    for number, title, content in cards:
        out.append(f'<article class="reviewer-card"><span class="reviewer-number">{number}</span>'
                   f'<h3>{h(title)}</h3><p>{h(content)}</p></article>')
    out.append('</div>')
    ex = view["worked_example"]
    out.append('<article class="reviewer-example"><div class="reviewer-example-head">'
               '<span class="reviewer-number">04</span><div><h3>具体方法：真实案例的输入—处理—输出</h3>'
               f'<p>{h(ex["scenario"])}</p></div></div><div class="reviewer-example-grid">')
    for title, key in (("输入", "input"), ("处理", "processing"), ("输出", "output"),
                       ("结果解释与边界", "interpretation")):
        out.append(f'<div class="reviewer-step"><span>{h(title)}</span><p>{h(ex[key])}</p></div>')
    out.append('</div></article></section>')
    return "".join(out)


def render_main(data: dict) -> str:
    heading = data["heading"]
    result = ['<main><header>']
    if len(heading) > 1:
        result.append(f'<div class="head-cn">{h(heading[0])}</div><h1>{h(heading[1])}</h1>')
    else:
        result.append(f'<h1>{h(heading[0])}</h1>')
    result.append(f'<p class="sub">{h(data.get("citation", ""))}</p></header>')
    result.append(render_reviewer_view(data.get("reviewer_view")))
    result.append('<nav class="nav" aria-label="研究模块导航">')
    if data.get("reviewer_view"):
        result.append('<a href="#reviewer-view">审稿人视角</a>')
    navigation = data.get("navigation", [])
    for i, node in enumerate(data["nodes"], 1):
        label = navigation[i-1] if len(navigation) >= i else node["title"]
        result.append(f'<a href="#m{i}">{i:02d} {h(label)}</a>')
    result.append('</nav><div class="flow">')
    for i, node in enumerate(data["nodes"], 1):
        result.append(f'<section class="module" id="m{i}"><div class="result"><span class="count">{i:02d}</span>')
        result.append(f'<h2>{h(node["title"])}</h2><p>{h(node["desc"])}</p>')
        if node.get("page"):
            result.append(f'<div class="loc">{h(node["page"])}</div>')
        result.append('</div><div class="tree"><div class="treetop">')
        sequence = node.get("branch_relation", "parallel") == "sequence"
        branch_cls = "branches sequence" if sequence else "branches"
        result.append(f'<b>{h(node.get("root", "支撑该结果的方法"))}</b><i></i></div><div class="{branch_cls}">')
        for index, branch in enumerate(node.get("branches", [])):
            if sequence and index:
                result.append('<div class="sequence-divider">↓ 进入下一阶段</div>')
            level = branch.get("level", 1)
            result.append(f'<article class="branch" data-level="{level}"><div class="branchhead">')
            result.append(f'<h3>{h(branch["title"])}</h3>')
            if branch.get("label"):
                result.append(f'<span class="branchtag">{h(branch["label"])}</span>')
            result.append('</div>')
            if branch.get("goal"):
                result.append(f'<p class="branchgoal">{h(branch["goal"])}</p>')
            result.extend(render_method(method) for method in branch.get("items", []))
            result.append('</article>')
        result.append('</div>')
        if node.get("evidence") or node.get("figure"):
            num = str(node.get("figure", ""))
            result.append('<div class="evidence"><div>')
            result.append(f'<div class="evtitle">原文证据{(" · Fig. " + h(num)) if num else ""}</div>')
            if node.get("evidence"):
                result.append(f'<div class="evtext">{h(node["evidence"])}</div>')
            result.append('</div>')
            if num:
                result.append(f'<button class="figbtn" data-fig="{h(num)}" type="button">查看原文图 {h(num)}</button>')
            result.append('</div>')
        result.append('</div></section>')
    result.append('</div></main>')
    return ''.join(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Paper-specific JSON")
    parser.add_argument("output", type=Path, help="Output standalone HTML")
    parser.add_argument("--debug-hotspots", action="store_true", help="Show clickable panel outlines for calibration")
    args = parser.parse_args()
    data_file = args.data.expanduser().resolve()
    data = json.loads(data_file.read_text(encoding="utf-8"))
    assert_data(data, data_file.parent)
    images, panels, meta = embed_images(data.get("figures", {}), data_file.parent)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    items = {
        "__PAGE_TITLE__": h(data.get("page_title", data["heading"][-1])),
        "__MAIN__": render_main(data),
        "__GLOSSARY_JSON__": safe_json(data.get("terms", {})),
        "__FIGURE_IMAGES_JSON__": safe_json(images),
        "__FIGURE_PANELS_JSON__": safe_json(panels),
        "__FIGURE_META_JSON__": safe_json(meta),
    }
    for placeholder, content in items.items():
        if placeholder not in template:
            raise ValueError(f"Missing required placeholder in template: {placeholder}")
        template = template.replace(placeholder, content)
    if args.debug_hotspots:
        template = template.replace("</style>", ".fig-hotspot{border:1.5px solid #09a6e7!important;background:rgba(5,155,249,.12)!important}</style>", 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(template, encoding="utf-8")
    summary = (f"Created: {args.output} ({args.output.stat().st_size/1024:.0f} KiB) | "
               f"reviewer_view={bool(data.get('reviewer_view'))} | nodes={len(data['nodes'])} | "
               f"figures={len(images)} | subplots={sum(map(len, panels.values()))} | "
               f"terms={len(data.get('terms', {}))}")
    print(summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
