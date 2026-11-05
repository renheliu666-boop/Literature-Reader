# Literature Reader · Reviewer-oriented Interactive Paper Reading Skill

将科研论文整理成**审稿人视角四问 + 研究结果主线 + 方法分叉树 + 可点击专业术语 + 组合图逐子图点击详解**的离线单文件 HTML。

## 核心分析顺序

1. **研究问题**：作者要解决什么？为什么重要？解决后有什么价值？
2. **前人工作**：以前怎么做？已有研究还差在哪？
3. **核心直觉**：用简洁、易懂的话讲清论文的本质想法。
4. **具体方法**：用论文中的真实案例讲清输入、处理、输出和结果边界。
5. **研究结果主线**：提取 3—7 项论文真正获得的核心发现。
6. **方法分叉树**：拆解每项发现背后的模型、算法、实验及其作用。
7. **图表证据**：逐张解释 Fig.1a、Fig.1b 等子图。
8. **术语解释**：缩写、模型和专业概念点击查看。
9. **审稿人评价**：判断创新性、方法适配性、证据充分性和结论边界。

## 文件结构

```text
Literature-Reader/
├── SKILL.md
├── README.md
├── LICENSE
├── templates/
│   └── reader.html
├── scripts/
│   ├── build_html.py
│   ├── mark_panels.py
│   └── crop_pdf_figure.py
├── examples/
│   ├── paper_template.json
│   └── paper_template.html
└── references/
    ├── DATA_SCHEMA.md
    └── FIGURE_GUIDE.md
```

## 使用方法

将整个文件夹（或 ZIP 解压后的文件夹）作为 Agent Skill 导入支持 `SKILL.md` 的工具，提供论文 PDF，并使用下面的 Prompt：

> 按 Literature Reader Skill 分析这篇论文。先以审稿人视角回答四个问题：研究问题、前人工作、核心直觉、一个真实案例的输入—处理—输出；明确区分论文原文、前人文献、合理推断、不确定内容和审稿人评价。然后提取研究结果主线、建立方法分叉树、解释专业术语，并对 Fig.1—Fig.n 中所有 a、b、c 子图逐个解读。默认不要显示图解，只有点击子图时才弹出卡片并显示子图局部放大。最后交付单文件 HTML。

Agent 负责阅读论文、制作论文专属 JSON 和图像素材，再调用构建器。Python 脚本只负责结构校验和 HTML 生成，不会自动完成论文语义分析。

## 构建 HTML

环境：Python 3.9+，构建器仅使用标准库。

```bash
python scripts/build_html.py examples/paper_template.json examples/paper_template.html
```

实际论文请复制 `examples/paper_template.json`，填入该论文的 `reviewer_view`、`nodes`、`terms` 和 `figures`，并将图片路径改成自己的图像文件路径。

热点位置调试：

```bash
python scripts/build_html.py paper.json debug.html --debug-hotspots
```

PDF 裁图（可选依赖 PyMuPDF）：

```bash
python -m pip install pymupdf
python scripts/crop_pdf_figure.py paper.pdf 3 figures/fig1.png --dpi 240
```

子图热点标注：

```bash
python scripts/mark_panels.py figures/fig1.png figures/fig1_selector.html
```

打开标注 HTML，拖动框选子图，输入 a/b/c 等标签并导出 JSON。将 `panels` 数组和文字解释合并到论文专属 JSON 中。坐标为归一化比例 `[x0,y0,x1,y1]`，更换裁图后必须重新标注。

## JSON 数据结构

四问内容已正式合并进 `references/DATA_SCHEMA.md`，不再需要单独的 JSON 补充文件。新增顶层 `reviewer_view` 字段，HTML 构建器会在研究结果主线之前展示它。

## 证据标签

- `[论文原文]`：目标论文直接报告的信息。
- `[前人文献]`：其他研究已经发表的结论或方法。
- `[合理推断]`：根据已有证据作出的解释，需说明推理依据。
- `[不确定/待验证]`：原文证据不足，明确指出缺少什么。
- `[审稿人评价]`：对创新性、方法适配性、验证充分性和结论边界的独立评价。

## 设计原则

- 同一个方法分叉根节点下的并列卡片统一使用同一低饱和度背景。
- 只有原文明示的顺序流程才使用递进层级和箭头。
- 方法详情、术语定义和子图解释默认隐藏，点击后再显示。
- 子图热点采用归一化比例坐标，局部放大区域与原图坐标一致。
- 所有图片嵌入最终 HTML，生成结果可离线阅读。
- 研究事实必须重新从当前论文中提取，不能复制示例论文的结论、参数或热点坐标。

## 说明

本整合版提供通用 JSON 模板，不再附带 IL6 论文专属演示数据和演示页面。这样可以避免用户将示例论文的具体结论、图像路径或子图坐标误用于其他研究。原有图表分析、方法树、术语交互和离线 HTML 构建功能均保留。
