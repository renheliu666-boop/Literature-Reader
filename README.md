# Literature Reader · Interactive Figures Skill

把科研论文整理成**研究结果主线 + 方法分叉树 + 点击式专业术语解释 + 组合图逐子图点击详解**的离线单文件 HTML。

沿用 [Literature-Reader](https://github.com/renheliu666-boop/Literature-Reader) 的结果主线和科研简洁风格，新增 Fig. 1a/1b/1c 等独立子图热点，点击才显示图解、局部放大和研究证据；未点击时不显示解释。

## 文件结构

```text
Literature-Reader-Interactive-Figures/
├── SKILL.md                    # Agent 应遵循的分析与生成规范
├── README.md                   # 本说明
├── templates/
│   └── reader.html             # 深蓝科研 UI 模板（静态原生 JS/CSS）
├── scripts/
│   ├── build_html.py           # JSON → 脱机单文件 HTML（Python 标准库）
│   ├── mark_panels.py          # 图像拖框，生成相对区域坐标（Python 标准库）
│   └── crop_pdf_figure.py      # 选取 PDF 页面区域并导出高清 PNG（可选 PyMuPDF）
├── examples/
│   ├── IL6_论文分析数据.json     # 完整示例，6 图 / 46 个子图 / 50 个术语
│   ├── IL6_交互式文献阅读.html   # 已生成的离线演示
│   └── figures/                # 构建示例需要的图像资源
└── references/
    ├── DATA_SCHEMA.md          # JSON 字段与坐标规则
    └── FIGURE_GUIDE.md         # 组合图逐项分析规范
```

## 使用

将完整文件夹（或 ZIP 解压后的文件夹）作为 Agent Skill 导入支持 `SKILL.md` 的工具，提供新的论文 PDF，并请求：

> 按 literature-reader-interactive-figures Skill 分析这篇论文。生成研究结果主线、方法分叉树、可点击术语解释；对 Fig.1—Fig.n 中所有 a、b、c 子图逐个解读。默认不要显示图解，只有点击子图时才弹出卡片，并显示子图局部放大。最后交付单文件 HTML。

Agent 阅读论文、制作论文专属 JSON 和图像素材，再调用构建器。本 Skill **不把一个普通 Python 脚本宣称为能够自动理解 PDF 的模型**：论文语义分析与逐图核对须由具备文献阅读能力的 Agent 完成。

构建示例（在 Skill 根目录运行）：

```bash
python scripts/build_html.py examples/IL6_论文分析数据.json examples/IL6_交互式文献阅读.html
```

用于核对热点位置的调试版本：

```bash
python scripts/build_html.py examples/IL6_论文分析数据.json debug.html --debug-hotspots
```

用鼠标拖框制作某张图的 `rect` 坐标：

```bash
python scripts/mark_panels.py examples/figures/fig1.jpg fig1_标注助手.html
```

打开标注助手，逐个框选子图，输入 a/b/c 等，导出 `panels.json`。将它的 `panels` 数组与文本解释合并到论文专属 JSON 中。坐标为归一化比例 `[x0,y0,x1,y1]`，适用于不同像素尺寸的图。

如需从 PDF 裁图，使用可选脚本：

```bash
python -m pip install pymupdf
python scripts/crop_pdf_figure.py paper.pdf 3 figures/figure1.png --dpi 240
```

也可以添加 `--rect X0 Y0 X1 Y1`，以 PDF 点为单位指定范围。物理页码从 1 开始。

## 同级同色与递进换色（低饱和度）

**同一个“方法分叉”根节点下的并列卡片，统一使用雾蓝灰背景、同色系边框和标签。**例如 IL6 论文中“三条信号的互补贡献”“候选转录因子发现”“四个转录因子的功能贡献”均属于一棵分叉树中的并列卡片，应当同色，而不是因为研究论证顺序而变成蓝/绿/紫三色。

在 `paper.json` 的 `nodes[]` 中，`"branch_relation": "parallel"` 是默认值，所有兄弟 `branches[]` 的 `"level"` 必须相同（通常都是 `1`）；否则生成脚本会报错。如果论文确实有顺序操作、需要画出**明确的递进箭头**，才使用 `"branch_relation": "sequence"`，此时卡片纵向串联且可用不同 `level` 逐层换色。四级颜色均低饱和：雾蓝灰 / 灰青绿 / 灰紫 / 暖灰棕。

这一规则按**图中的实际连线和父子关系**判断，不由页面第几行、研究章节顺序或内容是否是后续实验来决定。详情见 `references/DATA_SCHEMA.md`。

## 默认交互

- 同一方法分叉树下的并列卡片背景完全一致；仅明确纵向连接的递进阶段切换低饱和度背景色。
- 方法卡片默认只显示**方法名称、技术机制、解决问题**；点“查看方法细节”才展开。
- 术语默认不显示定义；**点击**才出现术语卡片。
- 原文组合图显示整图，子图解释卡片默认隐藏；点击 a、b、c… 对应区域出现具体目的、读图方法、观察结果、论文意义、研究边界，并放大该子图。
- 支持切换子图、关闭、Esc、手机布局；最终 HTML 不请求外部网络资源。

详细证据要求见 `SKILL.md`；新的论文必须重新阅读原文，不能复制 IL6 的科研事实和坐标到其他论文。

## 环境要求

- 生成 HTML：Python 3.9+，**仅标准库**。
- 手工子图区域标注：Python 3.9+，**仅标准库**，浏览器打开生成的标注 HTML。
- PDF 高清裁图：可选安装 PyMuPDF。
- 打开阅读 HTML：现代 Chrome/Edge/Firefox/Safari。

## 来源

本版本根据用户提供的 IL6 论文及已确认的 Literature-Reader 样式整理。示例图片仅用于对应论文的个人科研阅读与方法演示。保留原论文信息与图号，后续用于其他论文时需尊重原文和图像使用许可。
