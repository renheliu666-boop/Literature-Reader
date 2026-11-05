# Literature Reader — Research-First Interactive Paper Analysis

这是一个用于科研论文深度精读的独立 Skill。它以“研究结果主线”为核心，强调：

- 标题下方固定展示：研究问题、前人工作、核心直觉。
- 提炼 3–7 条核心研究发现，并反向关联支撑方法和实验。
- 用分叉树表达方法之间的并列、组成、顺序、验证和辅助关系。
- 对组合图逐子图交互解释：点击后才展示分析卡片。
- 专业术语点击解释。
- 严格区分论文原文、其他文献、合理推断和未知信息。
- 默认输出可离线打开的交互式 HTML。

## 文件结构

```text
Literature-Reader-New-Skill/
├── SKILL.md
├── README.md
├── references/
│   └── DATA_SCHEMA.md
└── templates/
    └── paper-analysis-template.json
```

## 使用方式

1. 将整个目录上传到你的 Skill 仓库。
2. 将 `SKILL.md` 作为 Skill 主说明文件。
3. 用户提供论文 PDF 后，先阅读全文，再按 Skill 生成分析。
4. 默认交付 HTML；如果需要结构化数据，同时交付 `paper-analysis-template.json` 对应结构的 JSON。

## 重要约束

本 Skill 不允许虚构论文细节。任何无法从论文或明确授权的外部来源核实的信息，都必须标注为未知或待核实。
