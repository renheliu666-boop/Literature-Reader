#!/usr/bin/env python3
"""Create a browser-based annotator for explicitly lettered paper subfigures."""
from __future__ import annotations
import argparse, base64, mimetypes
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image",type=Path,help="Complete original figure image")
    parser.add_argument("output",type=Path,help="Output HTML selector")
    args=parser.parse_args()
    image=args.image.resolve()
    if not image.is_file():parser.error(f"image not found: {image}")
    mime=mimetypes.guess_type(image.name)[0] or "image/png"
    data="data:"+mime+";base64,"+base64.b64encode(image.read_bytes()).decode("ascii")
    page = r"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>原文子图面板标注器</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#081321;color:#eaf5ff;font:14px system-ui,"Microsoft YaHei",sans-serif}
header{padding:14px 18px;background:#0d2035;border-bottom:1px solid #24445f;position:sticky;top:0;z-index:4}
h1{font-size:17px;margin:0 0 5px}p{color:#a9c1d5;margin:0;line-height:1.6}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
button,input{font:inherit}button{background:#12344b;border:1px solid #36718c;color:#dff9ff;padding:8px 12px;border-radius:7px;cursor:pointer}
button.primary{background:#12617a;border-color:#40bcd0}button.danger{background:#472b36;border-color:#87515d}
main{padding:18px;max-width:1500px;margin:auto}.stage{position:relative;display:inline-block;max-width:100%;line-height:0;background:#fff;cursor:crosshair}
.stage img{display:block;max-width:100%;height:auto}.stage canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.list{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px}.item{background:#10263a;border:1px solid #294960;border-radius:8px;padding:8px 10px;line-height:1.5}
.warn{color:#ffd28c;margin-top:8px}
</style>
<header><h1>原文明确子图面板标注</h1><p>仅当原图确实印有 (a)、(b)、(c) 等标签时使用。不要把无面板字母的局部结构人为标成子图。</p>
<div class="toolbar"><label>面板字母 <input id="letter" value="a" maxlength="1" size="2"></label><label>原文标注依据 <input id="evidence" placeholder="例如：原图可见(a)(b)，图注分别描述" size="38"></label><button id="undo">撤销最后一个</button><button id="clear" class="danger">清空</button><button id="export" class="primary">导出 panels JSON</button></div><div class="warn">拖动鼠标框选面板范围，需覆盖面板的坐标轴、图例和标签。</div></header>
<main><div class="stage" id="stage"><img id="source" src="__IMAGE__" alt="完整原图"><canvas id="overlay"></canvas></div><div class="list" id="list"></div></main>
<script>
const img=document.getElementById('source'),stage=document.getElementById('stage'),canvas=document.getElementById('overlay'),ctx=canvas.getContext('2d');
let panels=[],drag=null;
function size(){canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;draw();}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);panels.forEach(p=>{let [x0,y0,x1,y1]=p.rect;ctx.fillStyle='rgba(0,190,230,.12)';ctx.strokeStyle='#00bcd4';ctx.lineWidth=Math.max(2,canvas.width/800);ctx.fillRect(x0*canvas.width,y0*canvas.height,(x1-x0)*canvas.width,(y1-y0)*canvas.height);ctx.strokeRect(x0*canvas.width,y0*canvas.height,(x1-x0)*canvas.width,(y1-y0)*canvas.height);ctx.fillStyle='#061a2b';ctx.fillRect(x0*canvas.width,y0*canvas.height,30,24);ctx.fillStyle='#fff';ctx.font='bold 16px sans-serif';ctx.fillText('('+p.letter+')',x0*canvas.width+3,y0*canvas.height+17);});if(drag){ctx.strokeStyle='#ffb65c';ctx.lineWidth=3;ctx.strokeRect(drag.x,drag.y,drag.w,drag.h);}}
function point(e){let r=img.getBoundingClientRect();return {x:(e.clientX-r.left)*img.naturalWidth/r.width,y:(e.clientY-r.top)*img.naturalHeight/r.height};}
stage.addEventListener('pointerdown',e=>{if(!img.naturalWidth)return;let p=point(e);drag={x:p.x,y:p.y,w:0,h:0};stage.setPointerCapture(e.pointerId);draw();});
stage.addEventListener('pointermove',e=>{if(!drag)return;let p=point(e);drag.w=p.x-drag.x;drag.h=p.y-drag.y;draw();});
stage.addEventListener('pointerup',e=>{if(!drag)return;let d=drag;drag=null;let x0=Math.min(d.x,d.x+d.w)/img.naturalWidth,y0=Math.min(d.y,d.y+d.h)/img.naturalHeight,x1=Math.max(d.x,d.x+d.w)/img.naturalWidth,y1=Math.max(d.y,d.y+d.h)/img.naturalHeight;if(x1-x0<.01||y1-y0<.01){draw();return;}let letter=document.getElementById('letter').value.trim().toLowerCase();if(!/^[a-z]$/.test(letter)){alert('请输入 a-z 中的一个面板字母');draw();return;}if(panels.some(p=>p.letter===letter)){alert('该字母已使用');draw();return;}panels.push({letter,rect:[x0,y0,x1,y1]});document.getElementById('letter').value=String.fromCharCode(letter.charCodeAt(0)+1);render();});
function render(){let list=document.getElementById('list');list.replaceChildren();panels.forEach(p=>{let d=document.createElement('div');d.className='item';d.textContent='('+p.letter+') '+p.rect.map(x=>x.toFixed(4)).join(', ');list.append(d);});draw();}
document.getElementById('undo').onclick=()=>{panels.pop();render();};
document.getElementById('clear').onclick=()=>{if(confirm('清空所有面板标注？')){panels=[];render();}};
document.getElementById('export').onclick=()=>{if(!panels.length){alert('没有标注任何子图。');return;}let evidence=document.getElementById('evidence').value.trim();if(!evidence){alert('请填写原图/图注中明确的面板字母依据');return;}let blob=new Blob([JSON.stringify({has_explicit_panels:true,panel_label_evidence:evidence,panels},null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='explicit_panels.json';a.click();URL.revokeObjectURL(a.href);};
img.addEventListener('load',size);if(img.complete)size();
</script></html>"""
    page=page.replace("__IMAGE__",data)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(page,encoding="utf-8")
    print(f"Created {args.output}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
