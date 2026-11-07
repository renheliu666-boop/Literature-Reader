#!/usr/bin/env python3
"""Build a self-contained offline Literature Reader HTML from paper JSON.
Python 3.9+, standard library only. Images are embedded as data URIs.
"""
from __future__ import annotations
import argparse, base64, json, mimetypes, sys
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "reader.html"
IMAGE_MIME = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
              ".webp":"image/webp",".gif":"image/gif",".svg":"image/svg+xml"}

def safe_json(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))

def embed_image(value, base_dir, label):
    path = Path(value)
    if not path.is_absolute(): path = base_dir / path
    if not path.is_file(): raise ValueError(f"{label}: image not found: {path}")
    mime = IMAGE_MIME.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
    if mime not in IMAGE_MIME.values(): raise ValueError(f"{label}: unsupported image format: {path.suffix}")
    return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")

def normalize_term(key, value):
    if isinstance(value, list) and len(value) == 4:
        return {"full_name":value[0],"chinese_name":value[1],"definition":value[2],"role":value[3],"aliases":[]}
    if not isinstance(value, dict): raise ValueError(f"term {key}: expected object or legacy four-item array")
    aliases = value.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(x, str) for x in aliases):
        raise ValueError(f"term {key}: aliases must be an array of strings")
    formula_only = value.get("formula_only", False)
    if not isinstance(formula_only, bool):
        raise ValueError(f"term {key}: formula_only must be a boolean")
    return {"full_name":str(value.get("full_name","")),"chinese_name":str(value.get("chinese_name","")),
            "definition":str(value.get("definition","")),"analogy":str(value.get("analogy","")),
            "role":str(value.get("role","")),"source":str(value.get("source","")),"aliases":aliases,
            **({"formula_only": True} if formula_only else {})}

def validate_reviewer_view(view):
    if view is None: return
    if not isinstance(view, dict): raise ValueError("reviewer_view must be an object")
    for key in ("research_question","prior_work","core_intuition"):
        if not isinstance(view.get(key),str) or not view[key].strip(): raise ValueError(f"reviewer_view.{key} must be nonempty")
    example=view.get("worked_example")
    if not isinstance(example,dict): raise ValueError("reviewer_view.worked_example must be an object")
    for key in ("scenario","input","processing","output","interpretation"):
        if not isinstance(example.get(key),str) or not example[key].strip(): raise ValueError(f"reviewer_view.worked_example.{key} must be nonempty")

def validate_data(data):
    if not isinstance(data,dict): raise ValueError("JSON root must be an object")
    if not isinstance(data.get("heading"),list) or not data["heading"]: raise ValueError("heading must be a nonempty array")
    if not isinstance(data.get("nodes"),list) or not data["nodes"]: raise ValueError("nodes must be a nonempty array")
    validate_reviewer_view(data.get("reviewer_view"))
    nav=data.get("navigation",[])
    if nav and len(nav)!=len(data["nodes"]): raise ValueError("navigation length must match nodes length")
    figures=data.get("figures",{})
    if not isinstance(figures,dict): raise ValueError("figures must be an object")
    for ni,node in enumerate(data["nodes"],1):
        if not isinstance(node,dict) or not node.get("title") or not node.get("desc"): raise ValueError(f"node {ni}: title and desc required")
        relation=node.get("branch_relation","parallel")
        if relation not in ("parallel","sequence"): raise ValueError(f"node {ni}: invalid branch_relation")
        branches=node.get("branches",[])
        levels=[b.get("level",1) for b in branches]
        if relation=="parallel" and len(set(levels))>1: raise ValueError(f"node {ni}: parallel branches must use same level")
        if relation=="sequence" and levels!=sorted(levels): raise ValueError(f"node {ni}: sequence levels must be nondecreasing")
        for bi,branch in enumerate(branches,1):
            if not branch.get("title"): raise ValueError(f"node {ni}, branch {bi}: title required")
            level=branch.get("level",1)
            if isinstance(level,bool) or not isinstance(level,int) or not 1<=level<=4: raise ValueError(f"node {ni}, branch {bi}: level must be 1..4")
            for mi,item in enumerate(branch.get("items",[]),1):
                for key in ("name","core","effect"):
                    if not item.get(key): raise ValueError(f"node {ni}, branch {bi}, method {mi}: {key} required")
        refs=list(node.get("figures",[]))
        if node.get("figure"): refs.append(node["figure"])
        for ref in refs:
            if str(ref) not in figures: raise ValueError(f"node {ni}: references missing figure {ref}")
    for fid,fig in figures.items():
        if not isinstance(fig,dict) or not fig.get("image"): raise ValueError(f"figure {fid}: image required")
        panels=fig.get("panels",[])
        if panels and fig.get("has_explicit_panels") is not True:
            raise ValueError(f"figure {fid}: panels require has_explicit_panels=true; only original (a)/(b)/(c) labels count")
        if panels and not str(fig.get("panel_label_evidence","")).strip(): raise ValueError(f"figure {fid}: panel_label_evidence required")
        seen=set()
        for pi,panel in enumerate(panels,1):
            letter=str(panel.get("letter","")).strip().lower()
            if len(letter)!=1 or not letter.isalpha(): raise ValueError(f"figure {fid}, panel {pi}: letter must be one alphabetic character")
            if letter in seen: raise ValueError(f"figure {fid}: duplicate panel letter {letter}")
            seen.add(letter)
            rect=panel.get("rect")
            ok=(isinstance(rect,list) and len(rect)==4 and all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in rect)
                and 0<=rect[0]<rect[2]<=1 and 0<=rect[1]<rect[3]<=1)
            if not ok: raise ValueError(f"figure {fid}{letter}: rect must be [x0,y0,x1,y1] normalized to 0..1")
            for key in ("title","purpose","how","result","significance","limit","source"):
                if key not in panel: raise ValueError(f"figure {fid}{letter}: missing {key}; use empty string if not reported")

def render_formula(parts, terms, method_name):
    output = []
    for index, part in enumerate(parts, 1):
        if isinstance(part, str):
            output.append(escape(part))
            continue
        label = f"method {method_name}, parameters part {index}"
        if not isinstance(part, dict) or not isinstance(part.get("text"), str) or not part["text"].strip():
            raise ValueError(f"{label}: expected plain text or an object with nonempty text and a term key")
        key = part.get("term")
        if not isinstance(key, str) or key not in terms:
            raise ValueError(f"{label}: unknown term {key!r}")
        output.append(
            f'<button class="term-link formula-symbol" type="button" data-term="{escape(key)}" '
            f'aria-haspopup="dialog" aria-expanded="false">{escape(part["text"])}</button>'
        )
    return '<span class="formula-text">' + "".join(output) + '</span>'


def render_method(item, terms):
    h=lambda x:escape(str(x if x is not None else ""),quote=True)
    fields=[("输入对象","input"),("执行步骤","steps"),("关键参数/公式","parameters"),
            ("技术差异","difference"),("局限与边界","limit"),("原文定位","source")]
    rows = []
    for label, key in fields:
        value = item.get(key)
        if not value:
            continue
        if key == "parameters" and isinstance(value, list):
            content = render_formula(value, terms, item["name"])
        else:
            content = f'<span>{h(value)}</span>'
        rows.append(f'<div class="drow"><strong>{h(label)}</strong>{content}</div>')
    rows = "".join(rows)
    detail=(f'<button class="details-btn" type="button" aria-expanded="false">查看方法细节</button><div class="details" hidden>{rows}</div>') if rows else ""
    return f'<div class="method"><div class="role">{h(item.get("role",""))}</div><h4>{h(item["name"])}</h4><p class="core">{h(item["core"])}</p><p class="effect">作用：{h(item["effect"])}</p>{detail}</div>'

def render_reviewer_view(view):
    h=lambda x:escape(str(x if x is not None else ""),quote=True)
    if not view:return ""
    cards=[("01","研究问题",view["research_question"]),("02","前人工作",view["prior_work"]),("03","核心直觉",view["core_intuition"])]
    out=['<section class="reviewer-view" id="reviewer-view"><div class="reviewer-intro"><span class="reviewer-kicker">REVIEWER VIEW</span><h2>先理解研究逻辑，再进入技术细节</h2></div><div class="reviewer-grid">']
    for num,title,content in cards: out.append(f'<article class="reviewer-card"><span class="reviewer-number">{num}</span><h3>{h(title)}</h3><p>{h(content)}</p></article>')
    out.append('</div>')
    ex=view["worked_example"]
    out.append('<article class="reviewer-example"><div class="reviewer-example-head"><span class="reviewer-number">04</span><div><h3>具体方法：真实案例的输入—处理—输出</h3>'+f'<p>{h(ex["scenario"])}</p></div></div><div class="reviewer-example-grid">')
    for title,key in (("输入","input"),("处理","processing"),("输出","output"),("结果解释与边界","interpretation")):
        out.append(f'<div class="reviewer-step"><span>{title}</span><p>{h(ex[key])}</p></div>')
    out.append('</div></article></section>')
    return "".join(out)

def render_main(data):
    h=lambda x:escape(str(x if x is not None else ""),quote=True)
    terms=data.get("terms",{})
    heading=data["heading"];out=["<main><header>"]
    if len(heading)>1:out.append(f'<div class="head-cn">{h(heading[0])}</div><h1>{h(heading[1])}</h1>')
    else:out.append(f'<h1>{h(heading[0])}</h1>')
    out.append(f'<p class="sub">{h(data.get("citation",""))}</p></header>')
    out.append(render_reviewer_view(data.get("reviewer_view")))
    out.append('<nav class="nav" aria-label="论文分析导航">')
    for i,node in enumerate(data["nodes"],1):
        nav=data.get("navigation",[]);label=nav[i-1] if len(nav)>=i else node["title"]
        out.append(f'<a href="#m{i}">{i:02d} {h(label)}</a>')
    out.append('</nav><div class="flow">')
    for i,node in enumerate(data["nodes"],1):
        out.append(f'<section class="module" id="m{i}"><div class="result"><span class="count">{i:02d}</span><h2>{h(node["title"])}</h2><p>{h(node["desc"])}</p>')
        if node.get("page"):out.append(f'<div class="loc">{h(node["page"])}</div>')
        out.append('</div><div class="tree"><div class="treetop"><b>'+h(node.get("root","支撑该结果的方法与证据"))+'</b><i></i></div>')
        seq=node.get("branch_relation","parallel")=="sequence"
        out.append('<div class="branches sequence">' if seq else '<div class="branches">')
        for bi,branch in enumerate(node.get("branches",[])):
            if seq and bi:out.append('<div class="sequence-divider">↓ 进入下一阶段</div>')
            out.append(f'<article class="branch" data-level="{branch.get("level",1)}"><div class="branchhead"><h3>{h(branch["title"])}</h3>')
            if branch.get("label"):out.append(f'<span class="branchtag">{h(branch["label"])}</span>')
            out.append('</div>')
            if branch.get("goal"):out.append(f'<p class="branchgoal">{h(branch["goal"])}</p>')
            out.extend(render_method(x,terms) for x in branch.get("items",[]));out.append('</article>')
        out.append('</div>')
        refs=list(node.get("figures",[]))
        if node.get("figure"):refs.append(node["figure"])
        if node.get("evidence") or refs:
            out.append('<div class="evidence"><div><div class="evtitle">原文证据</div>')
            if node.get("evidence"):out.append(f'<div class="evtext">{h(node["evidence"])}</div>')
            out.append('</div><div class="figure-buttons">')
            for fid in dict.fromkeys(str(x) for x in refs):
                title=data["figures"][fid].get("title",f"Fig. {fid}")
                out.append(f'<button class="figbtn" data-fig="{h(fid)}" type="button">查看 {h(title)}</button>')
            out.append('</div></div>')
        out.append('</div></section>')
    out.append('</div>')
    critical=data.get("critical_review")
    if critical:
        out.append('<section class="critical-review"><h2>审稿人评价与研究边界</h2>')
        for key,label in (("innovation","创新性"),("strengths","优势"),("limitations","局限"),("generalization","泛化能力"),("reproducibility","可复现性"),("open_questions","待解决问题")):
            value=critical.get(key)
            if not value:continue
            if isinstance(value,list):out.append(f'<h3>{label}</h3><ul>'+''.join(f'<li>{h(v)}</li>' for v in value)+'</ul>')
            else:out.append(f'<h3>{label}</h3><p>{h(value)}</p>')
        out.append('</section>')
    out.append('</main>');return "".join(out)

def prepare_payload(data,base_dir):
    payload=dict(data);payload["terms"]={k:normalize_term(k,v) for k,v in data.get("terms",{}).items()}
    figs={}
    for fid,fig in data.get("figures",{}).items():
        item=dict(fig);item["image_data"]=embed_image(fig["image"],base_dir,f"figure {fid}");item["panels"]=[]
        for panel in fig.get("panels",[]):
            p=dict(panel);crop=p.get("crop_image")
            p["crop_image_data"]=embed_image(crop,base_dir,f"figure {fid} panel {p['letter']}") if crop else ""
            item["panels"].append(p)
        figs[str(fid)]=item
    payload["figures"]=figs;return payload

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data",type=Path);parser.add_argument("output",type=Path)
    parser.add_argument("--debug-hotspots",action="store_true")
    args=parser.parse_args();data_path=args.data.expanduser().resolve()
    data=json.loads(data_path.read_text(encoding="utf-8"));validate_data(data)
    payload=prepare_payload(data,data_path.parent);template=TEMPLATE.read_text(encoding="utf-8")
    replacements={"__PAGE_TITLE__":escape(str(data.get("page_title",data["heading"][-1])),quote=True),
                  "__MAIN__":render_main(data),"__PAPER_DATA__":safe_json(payload)}
    for token,value in replacements.items():
        if token not in template:raise ValueError(f"Missing template placeholder: {token}")
        template=template.replace(token,value)
    if args.debug_hotspots:
        template=template.replace("</style>",".figure-hotspot{border:2px solid #00c8ff!important;background:rgba(0,180,255,.18)!important}</style>",1)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(template,encoding="utf-8")
    n_panels=sum(len(f.get("panels",[])) for f in data.get("figures",{}).values())
    print(f"Created {args.output} | nodes={len(data['nodes'])} | figures={len(data.get('figures',{}))} | explicit panels={n_panels} | terms={len(data.get('terms',{}))}")
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);raise SystemExit(2)
