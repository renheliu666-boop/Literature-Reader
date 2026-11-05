# Examples

本仓库不捆绑第三方论文 PDF 或论文原图，以避免版权和文件体积问题。

建议用户自行创建以下目录：

```text
examples/
├── your-paper.json
└── figures/
    ├── figure1.png
    └── figure2.png
```

在 JSON 的 `figures[].image_asset` 中使用相对于 JSON 文件所在目录的路径，例如：

```json
{
  "id": "fig1",
  "figure_number": "1",
  "image_asset": "figures/figure1.png",
  "panels": []
}
```

然后执行：

```bash
python scripts/build_html.py examples/your-paper.json examples/your-paper.html
```

没有原图时可先将 `figures` 留空；不要保留指向不存在文件的图片路径。
