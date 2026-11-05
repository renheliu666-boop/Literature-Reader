# Literature Reader

面向科研论文深度精读的独立 Skill。以研究问题和研究发现为主线，生成可离线打开的交互式 HTML。

## 核心功能

- 论文标题下方固定显示三个导读卡片：**研究问题、前人工作、核心直觉**。
- 提炼 3–7 条核心研究发现，并关联支撑方法、实验和证据。
- 以分叉树呈现方法的并列、组成、顺序、验证和辅助关系。
- 组合图逐子图交互：点击子图热点后才显示解释卡片。
- 专业术语点击后显示中文解释和本文语境。
- 区分论文原文、其他文献、合理推断和未知信息。
- 将图片、CSS、JavaScript 内嵌到 HTML，支持离线打开。
- 支持新版 JSON，并提供旧版 `heading/nodes/terms/figures` JSON 兼容转换。

## 目录结构

```text
Literature-Reader/
├── SKILL.md
├── README.md
├── LICENSE
├── references/
│   ├── DATA_SCHEMA.md
│   └── FIGURE_GUIDE.md
├── scripts/
│   ├── build_html.py
│   ├── mark_panels.py
│   └── crop_pdf_figure.py
├── templates/
│   ├── paper-analysis-template.json
│   └── reader.html
├── tests/
│   └── test_build_html.py
└── examples/
    └── README.md
```

## 使用 Skill

1. 将整个仓库上传到 GitHub。
2. 在 ChatGPT/Codex 等支持 Skill 的环境中，将仓库作为 Skill 使用。
3. 提供论文 PDF、补充材料或明确指定的来源。
4. 要求按 `SKILL.md` 精读。默认先分析论文，再生成结构化 JSON 和 HTML。

## 本地生成交互式 HTML

要求：Python 3.9 或更高版本；构建 HTML 仅使用 Python 标准库。

把论文分析 JSON 保存为 `analysis.json`。图片路径相对于 JSON 文件所在目录填写，例如：

```json
{
  "figures": [
    {
      "id": "fig-1",
      "figure_number": "1",
      "image_asset": "figures/figure1.png",
      "panels": []
    }
  ]
}
```

运行：

```bash
python scripts/build_html.py analysis.json output.html
```

若要求所有图片必须存在：

```bash
python scripts/build_html.py analysis.json output.html --strict-images
```

构建器会输出缺失图片警告。普通模式下缺失图片不会生成破损图片链接；严格模式下会中止。

## 组合图子图坐标标注

先从论文 PDF 提取高清组合图，然后运行：

```bash
python scripts/mark_panels.py figures/figure1.png figures/figure1_selector.html
```

浏览器打开生成的 selector HTML，拖动框选子图，输入 a、b、c 等标签，导出 `panels.json`。把导出的归一化坐标填入对应 figure 的 `panels[].hotspot_coordinates`。

坐标格式为 `[x0, y0, x1, y1]`，取值范围 0–1，分别表示左、上、右、下边界。标注工具只负责坐标，不负责学术解释。

## 从 PDF 提取图像

可选依赖 PyMuPDF：

```bash
python -m pip install pymupdf
python scripts/crop_pdf_figure.py paper.pdf 5 figures/figure1.png --dpi 240
```

页码是 PDF 物理页码，从 1 开始。可选裁剪矩形使用 PDF point 坐标：

```bash
python scripts/crop_pdf_figure.py paper.pdf 5 figures/figure1.png --rect 50 80 550 700 --dpi 300
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 重要约束

- 不得虚构论文细节、数据、图表和引用。
- 原文未说明的内容应标注未知或待核实。
- 旧版 JSON 兼容转换只能保留已有信息，不能自动补造缺失的研究导览、实验设计或审稿评价。
- 图片应由用户提供或从用户提供的 PDF 中提取；本仓库不捆绑任何论文版权图片。
