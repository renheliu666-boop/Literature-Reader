"use strict";
const {terms, figures} = JSON.parse(document.getElementById("reader-data").textContent);
const $ = id => document.getElementById(id);
const pop = $("term-popover");
const figureDialog = $("figure-dialog");
const panelCard = $("panel-card");
let activeTerm, activeFigure, activePanel, figureButton, panelButton;
let panelGeneration = 0;

function add(parent, tag, value, cls) {
  const el = document.createElement(tag);
  el.textContent = value;
  if (cls) el.className = cls;
  parent.append(el);
  return el;
}
function closeTerm(restore = false) {
  if (!activeTerm) return;
  activeTerm.setAttribute("aria-expanded", "false");
  pop.classList.remove("open");
  if (restore) activeTerm.focus({preventScroll:true});
  activeTerm = null;
}
function positionTerm() {
  if (!activeTerm) return;
  const box = activeTerm.getBoundingClientRect();
  const gap = 10;
  if (box.bottom < 0 || box.top > innerHeight) return closeTerm();
  pop.style.left = Math.max(gap, Math.min(innerWidth - pop.offsetWidth - gap, box.left)) + "px";
  const above = box.top - pop.offsetHeight - gap;
  const ideal = box.bottom + pop.offsetHeight + gap <= innerHeight ? box.bottom + gap : above;
  pop.style.top = Math.max(gap, Math.min(innerHeight - pop.offsetHeight - gap, ideal)) + "px";
}
function openTerm(button) {
  if (activeTerm === button) return closeTerm(true);
  closeTerm();
  const t = terms[button.dataset.term];
  if (!t) return;
  activeTerm = button;
  const body = $("term-body");
  body.replaceChildren();
  add(body, "div", t.name, "term-popover-title");
  for (const [key, label] of [["english","英文"],["definition","含义"],["role","在本文中的作用"],["source","出处"]]) {
    if (!t[key]) continue;
    add(body, "h4", label);
    add(body, "p", t[key]);
  }
  button.setAttribute("aria-expanded", "true");
  pop.classList.add("open");
  positionTerm();
  $("term-close").focus({preventScroll:true});
}

function closePanel(restore = false) {
  panelGeneration++;
  if (activePanel) {
    figureDialog.querySelectorAll("[data-panel]").forEach(btn => btn.setAttribute("aria-pressed","false"));
    panelCard.hidden = true;
    $("panel-image").removeAttribute("src");
    if (restore && panelButton) panelButton.focus({preventScroll:true});
  }
  activePanel = panelButton = null;
}
async function showPanel(index, button) {
  if (!activeFigure || !activeFigure.panels[index]) return;
  closePanel();
  const p = activeFigure.panels[index];
  const generation = ++panelGeneration;
  activePanel = p;
  panelButton = button;
  figureDialog.querySelectorAll("[data-panel]").forEach(btn => btn.setAttribute("aria-pressed", String(Number(btn.dataset.panel) === index)));
  $("panel-title").textContent = "(" + p.letter + ") " + p.title;
  $("panel-desc").textContent = p.description;
  const preview = $("panel-image");
  preview.alt = p.title;
  if (p.image) {
    preview.src = p.image;
  } else {
    try {
      const full = $("figure-image");
      await full.decode();
      if (generation !== panelGeneration) return;
      const [x0,y0,x1,y1] = p.box;
      const w = full.naturalWidth, h = full.naturalHeight;
      const sw = Math.max(1, Math.round((x1-x0)*w)), sh = Math.max(1, Math.round((y1-y0)*h));
      const canvas = document.createElement("canvas");
      canvas.width = sw; canvas.height = sh;
      canvas.getContext("2d").drawImage(full,Math.floor(x0*w),Math.floor(y0*h),sw,sh,0,0,sw,sh);
      preview.src = canvas.toDataURL("image/png");
    } catch {
      if (generation !== panelGeneration) return;
      preview.removeAttribute("src");
      preview.alt = "无法生成子图局部，请对照完整原图。";
    }
  }
  panelCard.hidden = false;
  panelCard.scrollIntoView({block:"nearest"});
  $("panel-close").focus({preventScroll:true});
}
function openFigure(button) {
  const f = figures[button.dataset.figure];
  if (!f) return;
  closeTerm();
  closePanel();
  activeFigure = f;
  figureButton = button;
  $("figure-title").textContent = f.title;
  $("figure-source").textContent = f.source;
  $("figure-desc").textContent = f.description;
  $("figure-image").alt = f.title;
  $("figure-image").src = f.image;
  const hotspots = $("figure-hotspots"), buttons = $("panel-buttons");
  hotspots.replaceChildren(); buttons.replaceChildren();
  f.panels.forEach((p, i) => {
    const label = "(" + p.letter + ")";
    const hot = add(hotspots,"button","","figure-hotspot");
    const list = add(buttons,"button",label + " " + p.title,"subpart-btn");
    for (const btn of [hot,list]) {
      btn.type = "button"; btn.dataset.panel = i; btn.setAttribute("aria-pressed","false");
    }
    hot.setAttribute("aria-label", label + " " + p.title);
    add(hot,"span",label,"hotspot-tag");
    const [x0,y0,x1,y1] = p.box;
    Object.assign(hot.style,{left:x0*100+"%",top:y0*100+"%",width:(x1-x0)*100+"%",height:(y1-y0)*100+"%"});
  });
  figureDialog.showModal();
  $("figure-close").focus();
}

document.querySelectorAll("[data-preview]").forEach(img => {img.src = figures[img.dataset.preview].image;});
document.addEventListener("click", ev => {
  const term = ev.target.closest("[data-term]");
  if (term) return openTerm(term);
  if (ev.target.closest("#term-close")) return closeTerm(true);
  if (!pop.contains(ev.target)) closeTerm();
  const fig = ev.target.closest("[data-figure]");
  if (fig) return openFigure(fig);
  const panel = ev.target.closest("[data-panel]");
  if (panel) return void showPanel(Number(panel.dataset.panel),panel);
  if (ev.target.closest("#panel-close")) return closePanel(true);
  if (ev.target === figureDialog || ev.target.closest("#figure-close")) figureDialog.close();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && activeTerm) { ev.preventDefault(); closeTerm(true); }
});
figureDialog.addEventListener("cancel", ev => {
  if (activePanel) {ev.preventDefault(); closePanel(true);}
});
figureDialog.addEventListener("close", () => {
  closePanel();
  activeFigure = null;
  if (figureButton) figureButton.focus({preventScroll:true});
  figureButton = null;
});
window.addEventListener("resize",positionTerm);
window.addEventListener("scroll",ev => {
  if (!(ev.target instanceof Node) || !pop.contains(ev.target)) positionTerm();
},true);

const search = $("term-search");
if (search) {
  const entries = [...document.querySelectorAll(".glossary-grid [data-term]")];
  const filter = () => {
    const query = search.value.trim().toLowerCase();
    let count = 0;
    for (const btn of entries) {
      const t = terms[btn.dataset.term];
      btn.hidden = ![t.name,t.english,...(t.aliases || [])].filter(Boolean).join(" ").toLowerCase().includes(query);
      if (!btn.hidden) count++;
    }
    $("term-count").textContent = count + " 个术语";
  };
  search.addEventListener("input",filter);
  filter();
}

const nav = [...document.querySelectorAll(".nav a")];
const refreshNav = () => {
  let current = nav[0];
  for (const a of nav) if ($(a.hash.slice(1)).getBoundingClientRect().top <= 105) current = a;
  nav.forEach(a => {
    a.classList.toggle("active",a === current);
    if (a === current) a.setAttribute("aria-current","location"); else a.removeAttribute("aria-current");
  });
};
let scheduled = false;
window.addEventListener("scroll", () => {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {scheduled = false; refreshNav();});
},{passive:true});
refreshNav();
