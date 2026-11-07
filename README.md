# Literature Reader

面向科研论文精读的完整 Agent Skill。它将审稿人视角分析、证据核查、研究结果主线、方法分叉树、原图交互和中英文术语解释整合为一套可重复执行的流程，并生成可离线打开的单文件 HTML。

## 分析流程

1. 研究问题：作者要解决什么，为什么重要？
2. 前人工作：以前怎么做，已有方法还差在哪？
3. 核心直觉：本文最关键的想法是什么？
4. 具体方法：用真实案例解释输入—处理—输出。
5. 研究结果主线：提取论文真正获得的发现/研究认识。
6. 方法分叉树：解释模型、算法、实验、参数和证据关系。
7. 图表证据：打开完整原图；仅对原文明确标注 (a)、(b)、(c) 等面板建立热点。
8. 术语解释：中英文缩写、全称和专业词汇点击后显示小型浮动卡片。
9. 审稿人评价：创新性、方法适配性、证据充分性和结论边界。

## 项目结构

```text
Literature-Reader/
├── SKILL.md
├── README.md
├── LICENSE
├── templates/reader.html
├── scripts/
│   ├── build_html.py
│   ├── mark_panels.py
│   └── crop_pdf_figure.py
├── references/
│   ├── DATA_SCHEMA.md
│   └── FIGURE_GUIDE.md
├── examples/
│   ├── paper_template.json
│   └── paper_template.html
└── tests/test_builder.py
```

## 环境

- Python 3.9+
- HTML 构建只使用 Python 标准库。
- PDF 裁图可选安装 PyMuPDF：`python -m pip install pymupdf`。
- 不需要 Node、React、Vue、CDN 或在线 API。

## 快速使用

复制 `examples/paper_template.json`，填写当前论文的 `reviewer_view`、`nodes`、`terms` 和 `figures`。图片路径相对于 JSON 所在目录。

```bash
python scripts/build_html.py paper.json paper_reader.html
```

热点调试：

```bash
python scripts/build_html.py paper.json debug.html --debug-hotspots
```

PDF 裁出完整图件：

```bash
python scripts/crop_pdf_figure.py paper.pdf 3 figures/fig1.png --dpi 240
```

人工标注原文明确标注的子图：

```bash
python scripts/mark_panels.py figures/fig1.png figures/fig1_panels.html
```

## 关键交互规则

- 点击正文图件入口，打开完整原图。
- 只有原文明确标注的子图面板才有热点；点击热点显示局部放大和解释卡片。
- 没有 a/b/c 等原文面板标记的图保持完整图，不进行人为拆分。
- 点击中英文术语，在词汇附近显示小型浮动卡片；点击外部、关闭或按 Esc 关闭。
- 「关键参数/公式」中的变量、函数和运算符可用 `parameters` 片段引用词条，点击查看该符号在当前公式里的含义。写法见 [公式参数与符号](references/DATA_SCHEMA.md#公式参数与符号)。
- 方法细节默认收起，点击后展开。
- 不生成独立 Figure Index 缩略图画廊。
- 不添加 READ · CLICK · UNDERSTAND、侧边栏宣传语、阅读教程或重复免责声明。

## 推荐提示词

```text
请使用 Literature Reader Skill 深度分析我上传的论文。

先以审稿人视角回答四个问题：研究问题、前人工作及不足、核心直觉、真实案例的输入—处理—输出。明确区分论文原文、前人文献、合理推断、不确定内容和审稿人评价。

然后提取研究结果主线，建立方法分叉树，解释方法机制、输入、步骤、技术差异和局限。逐张解释论文原图。

图表规则：只有原文明确标注 (a)、(b)、(c) 等字母的面板才作为独立子图；其他图一律按完整原图处理，不得人为拆分。中英文术语均可点击，点击后显示靠近词汇的小型浮动卡片，不要全屏弹窗。

最终生成深色科技风、无独立 Figure Index、无侧边栏宣传模块、可离线打开的单文件 HTML，并按 Skill 的验收清单检查。
```

## 更新现有 GitHub 仓库

将 ZIP 解压后，把全部内容放到 `renheliu666-boop/Literature-Reader` 仓库根目录，确保 `SKILL.md` 位于根目录。建议先备份或创建分支，再检查：

```bash
git status
git diff
git add SKILL.md README.md LICENSE templates scripts references examples tests
git commit -m "Upgrade Literature Reader skill"
git push
```

GitHub 托管不会自动将 Skill 安装到 Agent；仍需按所用 Agent 的方式导入 Skill 目录。

论文语义分析由 Agent 完成，构建器只负责结构校验和 HTML 渲染。所有科学事实必须从当前论文重新提取，不能复制示例内容。
