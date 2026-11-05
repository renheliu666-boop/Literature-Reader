#!/usr/bin/env python3
"""Create a local drag-to-mark helper for multi-panel figure rectangles.

Usage:
  python scripts/mark_panels.py figures/figure1.png figures/figure1_selector.html

The generated selector is self-contained and works offline. It exports normalized
0..1 coordinates; it does not write academic explanations.
"""
from pathlib import Path
import argparse
import base64
from html import escape

PAGE = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>子图区域标注器</title>
<style>
*{box-sizing:border-box}body{font:15px/1.5 system-ui,"Microsoft YaHei",sans-serif;color:#eaf3ff;background:#0d1421;margin:0;padding:18px}
h1{font-size:23px;margin:4px 0 10px}p{margin:5px 0 16px;color:#afc7df}.row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start}
.sheet{position:relative;display:inline-block;line-height:0;max-width:100%;cursor:crosshair;user-select:none;touch-action:none;border:1px solid #43637e}
.sheet img{display:block;width:auto;max-width:100%;max-height:82vh;object-fit:contain;pointer-events:none}
.overlay{position:absolute;inset:0;pointer-events:none}.sel{position:absolute;outline:2px solid #11b6ef;background:#11b6ef30}
.sel b{position:absolute;left:0;top:0;background:#17436f;color:white;font:700 13px monospace;padding:4px}
#side{flex:1;min-width:260px;max-width:450px}button{border:1px solid #4c779d;border-radius:7px;background:#183452;color:#f3fcff;padding:10px;margin:3px;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:55vh;overflow:auto;border:1px solid #2b4b69;background:#111f2f;border-radius:10px;padding:12px}
</style></head><body><h1>多子图区域标注器</h1>
<p>在图片上按下并拖动，框选子图；输入 a、b、c 等标签。坐标自动归一化到 0–1。请逐个核对边界。</p>
<div class="row"><div class="sheet" id="sheet"><img id="source" src="__IMAGE__" alt="待标注原图"><div class="overlay" id="overlay"></div></div>
<div id="side"><button id="undo">撤销最后一个</button><button id="clear">清除全部</button><button id="save">导出 JSON</button><pre id="output">拖动左侧图片框选子图。</pre></div></div>
<script>
const sheet=document.getElementById("sheet"),overlay=document.getElementById("overlay"),out=document.getElementById("output"),rects=[];
let start=null,temp=null;
function norm(e){const b=sheet.getBoundingClientRect();return [Math.min(1,Math.max(0,(e.clientX-b.left)/b.width)),Math.min(1,Math.max(0,(e.clientY-b.top)/b.height))];}
function order(a,b){return [Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])].map(x=>Number(x.toFixed(6)));}
function box(d,r){d.style.left=r[0]*100+"%";d.style.top=r[1]*100+"%";d.style.width=(r[2]-r[0])*100+"%";d.style.height=(r[3]-r[1])*100+"%";}
function update(){overlay.replaceChildren();for(const p of rects){const d=document.createElement("div");d.className="sel";box(d,p.rect);const b=document.createElement("b");b.textContent=p.letter;d.append(b);overlay.append(d);}if(temp)overlay.append(temp);out.textContent=JSON.stringify({panels:rects.map(p=>({id:p.letter,original_label:p.letter,hotspot_label:p.letter,hotspot_coordinates:p.rect}))},null,2);}
sheet.addEventListener("pointerdown",e=>{if(e.button!==0)return;start=norm(e);temp=document.createElement("div");temp.className="sel";sheet.setPointerCapture(e.pointerId);update();});
sheet.addEventListener("pointermove",e=>{if(start&&temp)box(temp,order(start,norm(e)));});
sheet.addEventListener("pointerup",e=>{if(!start)return;const r=order(start,norm(e));start=null;temp=null;if(r[2]-r[0]<.01||r[3]-r[1]<.01){update();return;}let label=prompt("请输入子图标签（a、b、c…）",String.fromCharCode(97+rects.length));if(label){label=label.trim();if(rects.some(p=>p.letter===label))alert("该标签已存在");else rects.push({letter:label,rect:r});}update();});
document.getElementById("undo").onclick=()=>{rects.pop();update();};
document.getElementById("clear").onclick=()=>{if(confirm("清除全部标注？")){rects.length=0;update();}};
document.getElementById("save").onclick=()=>{const blob=new Blob([out.textContent],{type:"application/json;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="panels.json";a.click();URL.revokeObjectURL(url);};
update();
</script></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    mime = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp",".gif":"image/gif"}.get(args.image.suffix.lower())
    if not args.image.exists() or not mime:
        parser.error("图片必须存在，且格式为 PNG/JPEG/WEBP/GIF")
    encoded = base64.b64encode(args.image.read_bytes()).decode("ascii")
    uri = f"data:{mime};base64,{encoded}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(PAGE.replace("__IMAGE__", escape(uri, quote=True)), encoding="utf-8")
    print(f"已生成：{args.output}")


if __name__ == "__main__":
    main()
