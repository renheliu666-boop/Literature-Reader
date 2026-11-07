# DATA_SCHEMA：论文结构化数据规范

构建命令：`python scripts/build_html.py paper.json output.html`。图片路径相对于 JSON 文件目录，构建后全部嵌入 HTML。

## 顶层字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---:|---|
| `page_title` | string | 否 | 浏览器标题 |
| `heading` | string[] | 是 | 中文标题；可追加英文原题 |
| `citation` | string | 否 | 作者、年份、期刊、DOI |
| `reviewer_view` | object | 推荐 | 审稿人视角四问 |
| `navigation` | string[] | 否 | 与 nodes 等长的导航标签 |
| `nodes` | object[] | 是 | 研究结果/研究认识主线 |
| `terms` | object | 否 | 中英文术语词典 |
| `figures` | object | 否 | 完整原图及明确标注子图 |
| `critical_review` | object | 否 | 审稿人评价和研究边界 |

## reviewer_view

```json
{
  "reviewer_view": {
    "research_question": "[论文原文] 研究对象、核心问题、重要性和解决后的价值。",
    "prior_work": "[前人文献] 前人方法和进展；[审稿人评价] 具体不足。",
    "core_intuition": "[合理推断] 本文核心思路及推理依据。",
    "worked_example": {
      "scenario": "[论文原文] 真实案例对象和上下文。",
      "input": "真实数据、变量、样本、尺度和参数。",
      "processing": "原文报告的预处理、方法步骤、对照和验证。",
      "output": "论文实际报告的指标或结果。",
      "interpretation": "[合理推断] 结果支持什么，不能推出什么。"
    }
  }
}
```

## nodes：结果主线和方法树

```json
{
  "nodes": [{
    "title": "结论式研究发现标题",
    "desc": "[论文原文] 1—2句说明发现和关键证据。",
    "page": "Results第X节；PDF第X页；Fig. X",
    "root": "支撑该结果的方法与证据",
    "branch_relation": "parallel",
    "branches": [{
      "title": "方法模块标题",
      "label": "模型/实验/统计分析",
      "goal": "该分支回答的问题",
      "level": 1,
      "items": [{
        "name": "论文原文方法名称",
        "core": "输入/限制 + 核心机制 → 输出",
        "effect": "具体解决的问题",
        "role": "方法在证据链中的作用",
        "input": "真实输入和数据条件",
        "steps": "原文步骤、参数和操作顺序",
        "parameters": "关键公式、参数和单位",
        "difference": "相对基线或其他方法的真实差异",
        "limit": "适用边界和局限",
        "source": "章节、页码、图表"
      }]
    }],
    "evidence": "原文证据概述",
    "figure": "1"
  }]
}
```

`branch_relation` 只能是 `parallel` 或 `sequence`。并列分支使用相同 level；只有原文证实的顺序流程才用 sequence。每个方法的 name/core/effect 必填。`figure` 必须指向 figures 中存在的图号。一个结果可用 `figures: ["1","2"]` 引用多张图。

## 公式参数与符号

`parameters` 可以是普通字符串，也可以是按原公式顺序排列的片段数组。数组里的字符串照常显示，`{"text": "符号", "term": "词条键"}` 将该片段变成点击入口。`term` 必须精确对应 `terms` 中的键。显示文字以 `text` 为准，可保留上下标和特殊符号。保留需要的空格和括号，连续片段会直接拼接。

```json
{
  "parameters": [
    "式（2）",
    {"text": "hᵢ", "term": "eq2.h_i"},
    " = σ(",
    {"text": "W", "term": "eq2.W"},
    "xᵢ + b)"
  ]
}
```

在顶层 `terms` 定义相应词条。例如 `"eq2.h_i": {"formula_only": true, "definition": "第 i 个节点的输出特征向量。", "role": "记录该式计算出的节点表示。", "source": "式（2）"}`。`formula_only: true` 表示词条只通过显式片段引用，不参与正文中的自动术语匹配。相同字符若在两处表示不同量，为每种含义分别定义词条键。已有的专业术语（如激活函数名）也可以直接引用其词条。

## terms：中英文术语

推荐对象格式：

```json
{
  "terms": {
    "GNN": {
      "full_name": "Graph Neural Network",
      "chinese_name": "图神经网络",
      "definition": "利用图结构及邻居关系学习节点或图表示的神经网络方法。",
      "analogy": "把节点看成路口，模型会综合相邻路口的信息。",
      "role": "本文使用图结构聚合电网节点特征。",
      "aliases": ["Graph Neural Network", "Graph Neural Networks", "图神经网络"],
      "source": "论文第X节或可核验来源"
    }
  }
}
```

别名包括缩写、英文全称、单复数、大小写变体和中文名称。英文匹配忽略大小写并使用词边界，避免 GNN 错误匹配到 Ts-GNN 内部。别名不得同时指向不同术语。不能确认英文全称时留空，不得猜。兼容旧格式 `[英文全称, 中文名称, 释义, 本文作用]`。

## figures：完整原图和可选子图

```json
{
  "figures": {
    "1": {
      "title": "Fig. 1 原图标题",
      "image": "figures/fig1.png",
      "source": "Fig. 1；PDF第X页",
      "description": "完整原图的目的、结构、图例、坐标和结论边界。",
      "has_explicit_panels": false,
      "panel_label_evidence": "",
      "panels": []
    },
    "2": {
      "title": "Fig. 2 原图标题",
      "image": "figures/fig2.png",
      "source": "Fig. 2；PDF第Y页",
      "description": "完整图解释。",
      "has_explicit_panels": true,
      "panel_label_evidence": "原图可见(a)、(b)标签，图注分别描述。",
      "panels": [{
        "letter": "a",
        "rect": [0.02, 0.04, 0.48, 0.46],
        "crop_image": "figures/fig2a.png",
        "title": "子图a回答的问题",
        "purpose": "实验目的或对照设计",
        "how": "坐标轴、图例、颜色、单位、统计标记如何读取",
        "result": "原图直接展示的结果",
        "significance": "结果支持论文的哪项主张",
        "limit": "图中证据不能推出什么",
        "source": "Fig. 2a；PDF第Y页"
      }]
    }
  }
}
```

硬性规则：
- `image` 始终是完整原图。
- `panels` 只存原文明确标注 a/b/c 等面板。
- `panels` 非空时，`has_explicit_panels` 必须为 true，且 `panel_label_evidence` 非空。
- 无明确面板字母时，使用 false 和空数组。
- `rect` 为完整原图中的归一化 `[x0,y0,x1,y1]`，范围 0–1。
- `crop_image` 可选；未提供时由浏览器 Canvas 裁局部预览。
- 流程框、折线系列、热图区域、网络局部和颜色分区不得写入 panels。

## critical_review（可选）

```json
{
  "critical_review": {
    "innovation": "[审稿人评价] 实质创新及依据。",
    "strengths": ["证据支持的优点"],
    "limitations": ["原文局限或审稿人识别的不足"],
    "generalization": "适用范围和泛化边界。",
    "reproducibility": "数据、代码、参数和验证的可复现性。",
    "open_questions": ["仍需回答的问题"]
  }
}
```

## 构建器校验

构建器检查必需字段、图片路径、并列/顺序层级、面板坐标、重复字母，以及子图是否声明原文标签。脚本无法自动验证面板字母是否真实存在；必须由 Agent 对照 PDF 原图和图注确认。
