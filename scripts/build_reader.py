"""Build a self-contained V6 paper reader from plain JSON and local images."""
import argparse
import base64
import html
import json
import math
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif"}
TOKEN = re.compile(r"\[\[([^|\[\]]+)(?:\|([^\[\]]+))?\]\]")


def e(value):
    return html.escape(value, quote=True)


def json_js(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace("<", r"\u003c")


def required(obj, keys, label):
    for key in keys.split():
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise ValueError(f"{label}.{key}: required nonempty text")


def embedded_image(base, value):
    rel = Path(value)
    target = (base / rel).resolve()
    mime = TYPES.get(target.suffix.lower())
    if rel.is_absolute() or not target.is_relative_to(base) or not mime or not target.is_file():
        raise ValueError(f"Image must be a supported file inside the data directory: {value}")
    data = target.read_bytes()
    if not data:
        raise ValueError(f"Empty image: {value}")
    return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")


class Reader:
    def __init__(self, data, base):
        self.data, self.base = data, base
        self.terms = data.get("terms", {})
        self.figures = {}
        self.used = set()
        self.sections = []
        self.nav = []
        self.aliases = {}
        for key, t in self.terms.items():
            required(t, "name definition", f"terms.{key}")
            if t.get("formula_only"):
                continue
            for alias in [t["name"], t.get("english", ""), *t.get("aliases", [])]:
                if alias:
                    normalized = alias.casefold()
                    if normalized in self.aliases and self.aliases[normalized][1] != key:
                        raise ValueError(f"Conflicting term alias: {alias}")
                    self.aliases[normalized] = (alias, key)
        patterns = []
        for alias, _ in sorted(self.aliases.values(), key=lambda x: len(x[0]), reverse=True):
            left = r"(?<![A-Za-z0-9_-])" if alias[0].isascii() and alias[0].isalnum() else ""
            right = r"(?![A-Za-z0-9_-])" if alias[-1].isascii() and alias[-1].isalnum() else ""
            patterns.append(left + re.escape(alias) + right)
        self.auto = re.compile("|".join(patterns), re.IGNORECASE | re.ASCII) if patterns else None
        for key, fig in data.get("figures", {}).items():
            required(fig, "title source image description", f"figures.{key}")
            panels = fig.get("panels", [])
            if panels:
                required(fig, "panel_evidence", f"figures.{key}")
            found = set()
            hydrated = []
            for p in panels:
                required(p, "letter title description", f"figures.{key}.panels")
                letter = p["letter"].lower()
                if not re.fullmatch("[a-z]", letter) or letter in found:
                    raise ValueError(f"Invalid or repeated panel label in figure {key}: {letter}")
                found.add(letter)
                box = p.get("box", [])
                if (len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
                        or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)):
                    raise ValueError(f"Invalid normalized box: {key}({letter})")
                hydrated.append(dict(p, letter=letter,
                    image=embedded_image(base, p["image"]) if p.get("image") else None))
            self.figures[key] = dict(fig, image=embedded_image(base, fig["image"]), panels=hydrated)

    def term(self, key, label, cls="term-inline"):
        if key not in self.terms:
            raise ValueError(f"Unknown term: {key}")
        return f'<button type="button" class="{cls}" data-term="{e(key)}" aria-expanded="false">{e(label)}</button>'

    def rich(self, value, auto=True):
        def plain(s):
            if not (auto and self.auto):
                return e(s)
            out, start = [], 0
            for m in self.auto.finditer(s):
                hit = self.aliases.get(m[0].casefold())
                if hit:
                    out += [e(s[start:m.start()]), self.term(hit[1], m[0])]
                    start = m.end()
            return "".join(out) + e(s[start:])
        out, start = [], 0
        for m in TOKEN.finditer(value):
            out += [plain(value[start:m.start()]), self.term(m[1], m[2] or self.terms.get(m[1], {}).get("name", m[1]))]
            start = m.end()
        return "".join(out) + plain(value[start:])

    def figures_at(self, ids):
        out = []
        for key in map(str, ids):
            if key not in self.figures:
                raise ValueError(f"Unknown figure: {key}")
            f = self.figures[key]
            self.used.add(key)
            out.append(f'<button class="figure-inline" type="button" data-figure="{e(key)}" aria-haspopup="dialog">'
                       f'<img loading="lazy" data-preview="{e(key)}" alt="{e(f["title"])}"><span>'
                       f'<b>{e(f["title"])}</b><em>查看原图 ↗</em></span></button>')
        return "".join(out)

    def section(self, key, nav, label, title, content):
        if not content:
            return
        n = f"{len(self.nav)+1:02}"
        self.nav.append(f'<a href="#{key}"><span>{n}</span>{e(nav)}</a>')
        self.sections.append(f'<section class="section" id="{key}"><div class="section-head">'
                             f'<span class="section-index">{n}</span><div><div class="eyebrow">{label}</div>'
                             f'<h2>{e(title)}</h2></div></div>{content}</section>')

    def list_items(self, items):
        return '<ul class="check-list">' + "".join(f"<li>{self.rich(t)}</li>" for t in items) + "</ul>" if items else ""

    def note(self, label, value, cls="callout"):
        return f'<p class="{cls}"><strong>{e(label)}</strong> {self.rich(value)}</p>' if value else ""

    def detail_cards(self, items, relation="parallel"):
        if relation not in ("parallel", "sequence"):
            raise ValueError(f"Invalid method relation: {relation}")
        if not items:
            return ""
        cards = [f'<div class="detail-card"><h4>{e(x["label"])}</h4><p>{self.rich(x["text"])}</p></div>' for x in items]
        if relation == "sequence":
            return '<div class="steps-sequence">' + '<div class="stage-arrow" aria-hidden="true">↓</div>'.join(cards) + "</div>"
        return '<div class="explain-grid">' + "".join(cards) + "</div>"

    def render(self):
        d = self.data
        paper, o = d["paper"], d["overview"]
        required(paper, "title summary source", "paper")
        required(o, "question prior answer", "overview")
        r = self.rich
        cards = []
        for key, cls, tag, icon, title in [
            ("question","problem","PROBLEM","⌁","文章研究了什么问题？"),
            ("prior","prior","PRIOR WORK","◫","前人怎么做？不足在哪里？"),
            ("answer","solution","THIS PAPER","⟡","本文做了什么？"),
        ]:
            cards.append(f'<article class="glass-card {cls}-card"><div class="card-tag">{tag}</div>'
                         f'<div class="card-icon" aria-hidden="true">{icon}</div><h3>{title}</h3><p>{r(o[key])}</p></article>')
        self.section("overview","三问总览","THREE-PART OVERVIEW","先用三个问题读懂整篇论文",
                     '<div class="three-cards">' + "".join(cards) + "</div>" +
                     self.note("核心直觉", o.get("takeaway"),"takeaway"))
        if prior := d.get("prior"):
            rows = "".join(f'<tr><th scope="row">{r(x["title"])}</th><td>{r(x["approach"])}</td><td>{r(x["limit"])}</td></tr>' for x in prior)
            self.section("prior","前人方法","RELATED METHODS","前人方法：问题卡在哪里？",
                         '<div class="comparison"><table><thead><tr><th>方法类别</th><th>基本思路</th><th>适用条件或不足</th>'
                         '</tr></thead><tbody>'+rows+'</tbody></table></div>')
        if contributions := d.get("contributions"):
            content = "".join(f'<article class="contrib"><h3>{e(x["title"])}</h3><p>{r(x["text"])}</p>'
                              + self.note("作用",x.get("impact")) + '</article>' for x in contributions)
            self.section("contribution","本文贡献","CONTRIBUTIONS","本文的主要贡献",'<div class="contrib-grid">'+content+'</div>')
        if methods := d.get("methods"):
            blocks = []
            for i, m in enumerate(methods, 1):
                required(m, "title source summary", f"methods.{i}")
                fs = []
                for f in m.get("formulas", []):
                    required(f, "label expression", f"methods.{i}.formulas")
                    fs.append(f'<div class="formula-panel"><div class="formula-label">{e(f["label"])}</div>'
                              f'<div class="formula-expression">{r(f["expression"], False)}</div>'
                              + (f'<p>{r(f["explanation"])}</p>' if f.get("explanation") else "") + '</div>')
                blocks.append(f'<article class="method-block"><div class="method-title"><span>{len(self.nav)+1}.{i}</span><div>'
                    f'<h3>{e(m["title"])}</h3><p>{e(m["source"])}</p></div></div><p>{r(m["summary"])}</p>'
                    + self.figures_at(m.get("figures", [])) + self.detail_cards(m.get("details", []),m.get("relation","parallel"))
                    + "".join(fs) + self.note("复现与边界",m.get("limit")) + '</article>')
            self.section("method","研究方法","METHOD · STEP BY STEP","研究方法：从原理到输出","".join(blocks))
        if exp := d.get("experiment"):
            facts = "".join(f'<div><b>{e(x["label"])}</b><span>{r(x["text"])}</span></div>' for x in exp.get("facts", []))
            details = [{"label": label, "text": exp["example"][key]} for key, label in
                       [("scenario","案例"),("input","输入"),("process","处理"),("output","输出"),("limit","解读与边界")]
                       if exp.get("example", {}).get(key)]
            self.section("experiment","实验设计","EXPERIMENT DESIGN",exp.get("title","实验是怎么设计的？"),
                self.figures_at(exp.get("figures", [])) + (f'<div class="experiment-table">{facts}</div>' if facts else "")
                + ('<div class="example-block"><h3>真实案例走读</h3>'+self.detail_cards(details)+'</div>' if details else ""))
        if results := d.get("results"):
            blocks = []
            for i, x in enumerate(results,1):
                required(x, "title observation source", f"results.{i}")
                metrics = "".join(f'<span>{r(v)}</span>' for v in x.get("metrics", []))
                blocks.append(f'<article class="result-block"><div class="result-head"><span>RESULT {i:02}</span>'
                    f'<h3>{e(x["title"])}</h3></div><p>{r(x["observation"])}</p>'
                    + (f'<div class="metric-pills">{metrics}</div>' if metrics else "")
                    + self.figures_at(x.get("figures", [])) + self.note("这支持什么",x.get("interpretation"))
                    + self.note("证据边界",x.get("limit"),"caution-note") + f'<p class="source">{e(x["source"])}</p></article>')
            self.section("results","研究结果","RESULTS & EVIDENCE",d.get("results_title","研究结果：证据支持什么？"),"".join(blocks))
        if review := d.get("review"):
            cards = "".join(f'<article class="glass-card {cls}"><h3>{label}</h3>{self.list_items(review[key])}</article>'
                            for key, cls, label in [("strengths","","论文的主要价值"),("limits","caution-card","结论与证据的边界")]
                            if review.get(key))
            next_steps = self.list_items(review.get("next", []))
            self.section("critical","批判性阅读","CRITICAL READING","如何评价这篇论文？",
                         (f'<div class="two-col">{cards}</div>' if cards else "") +
                         (f'<div class="callout"><strong>优先验证</strong>{next_steps}</div>' if next_steps else ""))
        buttons = "".join(self.term(k,v["name"],"term") for k,v in self.terms.items() if not v.get("formula_only"))
        if buttons:
            self.section("glossary","术语词典","GLOSSARY","专业名词互动词典",
                         '<div class="glossary-tools"><input id="term-search" type="search" aria-label="搜索术语" placeholder="搜索缩写、全称或译名">'
                         '<span id="term-count" aria-live="polite"></span></div><div class="glossary-grid">'+buttons+'</div>')
        if recap := d.get("recap"):
            steps = '<i aria-hidden="true">→</i>'.join(f'<div><small>{i:02}</small><b>{r(x["title"])}</b><p>{r(x["text"])}</p></div>'
                      for i, x in enumerate(recap.get("steps", []), 1))
            self.section("takeaway","全文回顾","RECAP","用一条逻辑链回顾全文",
                         (f'<div class="recap-chain">{steps}</div>' if steps else "") +
                         self.note("核心结论",recap.get("takeaway"),"takeaway") + self.list_items(recap.get("questions", [])))
        if unused := self.figures.keys() - self.used:
            raise ValueError(f"Figures not referenced: {', '.join(sorted(unused))}")
        if len(paper.get("stats", [])) > 4:
            raise ValueError("paper.stats accepts at most 4 items")
        stats = "".join(f'<div><strong>{e(x["value"])}</strong><small>{e(x["label"])}</small></div>' for x in paper.get("stats", []))
        meta = "".join(f"<span>{e(x)}</span>" for x in paper.get("metadata", []))
        accent = f'<br><span>{e(paper["accent"])}</span>' if paper.get("accent") else ""
        hero = '<header class="hero" id="top"><div class="hero-kicker"><span class="pulse"></span>PAPER DEEP DIVE</div>' + (
            f'<h1>{e(paper["title"])}{accent}</h1><p class="hero-sub">{r(paper["summary"])}</p>'
            f'<div class="hero-meta">{meta}<span>{e(paper["source"])}</span></div>'
            + (f'<div class="hero-stats">{stats}</div>' if stats else "") + "</header>")
        tokens = {"TITLE":e(paper["title"]), "BRAND":e(paper.get("short_title") or "PAPER READER"),
                  "NAV":"".join(self.nav), "CONTENT":hero+"".join(self.sections),
                  "CSS":(ASSETS/"reader.css").read_text(encoding="utf-8"),
                  "JS":(ASSETS/"reader.js").read_text(encoding="utf-8"),
                  "DATA":json_js({"terms":self.terms,"figures":self.figures})}
        template = (ASSETS/"reader.html").read_text(encoding="utf-8")
        return re.sub(r"@@([A-Z]+)@@", lambda m: tokens[m[1]], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        source = args.data.resolve()
        if args.output.suffix.lower() != ".html" or source == args.output.resolve():
            raise ValueError("Output must be a separate .html file")
        data = json.loads(source.read_text(encoding="utf-8-sig"))
        result = Reader(data, source.parent).render()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
        print(f"Built {args.output} ({len(result.encode('utf-8')):,} bytes)")
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
