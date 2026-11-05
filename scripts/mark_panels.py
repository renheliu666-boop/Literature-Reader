#!/usr/bin/env python3
"""Create an offline drag-to-mark helper for multi-panel figure rectangles.

Uses Python standard library only. The generated HTML is a calibration helper.
Drag around each subplot and enter its letter; export normalized 0..1 coordinates.
"""
from pathlib import Path
import argparse
import base64
from html import escape

PAGE = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>子图区域标注器</title>
<style>
*{box-sizing:border-box}body{font:15px/1.5 system-ui,'Microsoft YaHei',sans-serif;color:#eaf3ff;background:#0d1421;margin:0;padding:18px}
h1{font-size:23px;margin:4px 0 10px}p{margin:5px 0 16px;color:#afc7df}.row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start}
.sheet{position:relative;display:inline-block;line-height:0;max-width:100%;cursor:crosshair;user-select:none;touch-action:none;border:1px solid #43637e}
.sheet img{display:block;width:auto;max-width:100%;max-height:80vh;object-fit:contain;pointer-events:none}
.overlay{position:absolute;inset:0;pointer-events:none}.sel{position:absolute;outline:2px solid #11b6ef;background:#11b6ef30}
.sel b{position:absolute;left:0;top:0;background:#17436f;color:white;font:700 13px monospace;padding:4px}
#side{flex:1;min-width:260px;max-width:450px}button{border:1px solid #4c779d;border-radius:7px;background:#183452;color:#f3fcff;padding:10px;margin:3px;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:50vh;overflow:auto;border:1px solid #2b4b69;background:#111f2f;border-radius:10px;padding:12px}
</style></head><body><h1>多子图区域标注器</h1><p>沿子图边界按下并拖动鼠标 → 输入 a、b、c … 子图标签。坐标自动归一化为 0—1；请逐个核对框选范围。支持撤销与导出 JSON。</p>
<div class="row"><div class="sheet" id="sheet"><img id="source" src="__IMAGE__" alt="待标注的原始组合图"><div class="overlay" id="overlay"></div></div>
<div id="side"><div><button id="undo">撤销最后一个</button><button id="clear">清除</button><button id="save">导出子图 JSON</button></div><pre id="output">拖动左侧图片框选子图。</pre></div></div>
<script>
const sheet=document.getElementById('sheet'),overlay=document.getElementById('overlay'),out=document.getElementById('output'),rects=[];
let start=null,temp=null;
function norm(event){let b=sheet.getBoundingClientRect();return [Math.min(1,Math.max(0,(event.clientX-b.left)/b.width)),Math.min(1,Math.max(0,(event.clientY-b.top)/b.height))];}
function order(a,b){return [Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])].map(x=>Number(x.toFixed(6)));}
function update(){overlay.replaceChildren();for(let p of rects){let d=document.createElement('div');d.className='sel';box(d,p.rect);let b=document.createElement('b');b.textContent=p.letter;d.append(b);overlay.append(d);}if(temp)overlay.append(temp);out.textContent=JSON.stringify({panels:rects.map(p=>({...p,title:'',purpose:'',how:'',result:'',significance:'',limit:'',source:''}))},null,2);}
function box(d,rect){d.style.left=(rect[0]*100)+'%';d.style.top=(rect[1]*100)+'%';d.style.width=((rect[2]-rect[0])*100)+'%';d.style.height=((rect[3]-rect[1])*100)+'%';}
sheet.addEventListener('pointerdown',e=>{if(e.button!==0)return;start=norm(e);temp=document.createElement('div');temp.className='sel';sheet.setPointerCapture(e.pointerId);update();});
sheet.addEventListener('pointermove',e=>{if(!start)return;box(temp,order(start,norm(e)));});
sheet.addEventListener('pointerup',e=>{if(!start)return;let rect=order(start,norm(e));start=null;temp=null;if(rect[2]-rect[0]<.01||rect[3]-rect[1]<.01){update();return;}let label=prompt('请输入子图标签（a、b、c、…）',''+String.fromCharCode(97+rects.length));if(label){label=label.trim();if(rects.some(p=>p.letter===label))alert('标签已存在，请先重新选择');else rects.push({letter:label,rect});}update();});
document.getElementById('undo').onclick=()=>{rects.pop();update();};document.getElementById('clear').onclick=()=>{if(confirm('清除全部已标记子图？')){rects.length=0;update();}};
document.getElementById('save').onclick=()=>{let b=new Blob([out.textContent],{type:'application/json;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='panels.json';a.click();URL.revokeObjectURL(a.href);};update();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path)
    ap.add_argument("output", type=Path)
    a = ap.parse_args()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif"}.get(a.image.suffix.lower())
    if not mime or not a.image.exists():
        raise SystemExit("Image must exist and be PNG, JPEG, WEBP or GIF")
    data = "data:" + mime + ";base64," + base64.b64encode(a.image.read_bytes()).decode("ascii")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(PAGE.replace("__IMAGE__", escape(data, quote=True)), encoding="utf-8")
    print(f"Wrote: {a.output}")


if __name__ == "__main__":
    main()
