# 阅读器数据

将 JSON 和本篇论文的图件放入任务工作目录。字符串只当作纯文本；不要写 HTML。所有可选数组可省略，不要放占位文字。资产路径必须相对于 JSON 且落在同一目录或子目录。生成器接受 PNG、JPEG、WebP、GIF；无需联网或第三方 Python 包。

## 顶层数据

| 键 | 内容 |
|---|---|
| `paper` | 必需：`title`、`summary`、`source`；可选 `accent`（标题第二行）、`short_title`（侧栏）、`metadata`（作者、期刊、DOI 字符串数组）、`stats`（最多四项 `{value,label}`，标签说明条件或来源） |
| `overview` | 必需：`question`、`prior`、`answer`；可选 `takeaway` |
| `prior` | 并列条目 `{title, approach, limit}`；按路线分，不把前人结果误写成本篇验证 |
| `contributions` | 条目 `{title, text, impact}`；`impact` 可选 |
| `methods` | 方法条目，格式见下 |
| `experiment` | 可选 `{title, facts, example, figures}`；`facts` 是 `{label,text}` 数组；`example` 是 `{scenario,input,process,output,limit}`，允许省略部分字段。综述可把标题设为“文献证据与范围”。 |
| `results` | 条目 `{title, observation, interpretation, limit, source, metrics, figures}`；必须有 `title, observation, source`，`metrics` 是指标字符串数组 |
| `results_title` | 可选标题覆盖，如“主要研究认识” |
| `review` | `{strengths,limits,next}`，均为字符串数组；可省略单组 |
| `terms` | 词条字典，见下 |
| `figures` | 图件字典，见下 |
| `recap` | `{steps, takeaway, questions}`；`steps` 为 `{title,text}` 数组；只有有向的研究推理才用它。questions 为自检问题字符串数组。 |

方法条目：`{title, source, summary, details, relation, formulas, figures, limit}`，其中 `title, source, summary` 必填。可选的 `details` 是 `{label,text}` 数组；只有 `relation: "sequence"` 会在这些卡片之间显示箭头；`"parallel"` 或不填时卡片同级。若方法本身只有并行组，可在标题中说明“并行”。`formulas` 为 `{label, expression, explanation}` 数组，前两项必填。

## 术语和公式

`terms` 以短 ID 为键，值为 `{name, english, definition, role, source, aliases, formula_only}`。只有 `name,definition` 必填。`aliases` 可列缩写、全称、译名；生成器在正文优先匹配较长别名并对英文用词边界。正文或公式可用 `[[term-id|显示文字]]` 精确指定；公式专属词条加 `"formula_only":true`，只通过显式标记点击，不加入词典或自动匹配。HTML 会转义纯文本。词义来自论文或明确标注的解释，避免把模型假设写成通用定义。

公式的 `expression` 使用显式标记覆盖所有独立数学量。例如

```text
[[z-output|h]] = ([[z-input|ĥ]] − [[z-mean|μ]]) / [[z-sd|σ]]
```

分别定义四个词条。每张卡片写该符号在当前公式中代表什么、如何参与计算和原式编号。量纲明确时写在释义中。括号、等号、常数和普通算术符号照常显示。具名函数和有解释价值的求和索引可单独标记。带帽、上下标和转置属于同一个量时保留原记号，在卡片里解释各部分。独立的量不要合并，例如将 `γ` 与 `dᵢₖ` 分别标记。同一公式内的重复量可以复用词条 ID，但每次出现都需要标记。若同名符号在另一公式中代表不同量，使用新的 ID。

验收时把每条公式与论文对照，并检查公式区域的变量、参数、矩阵、独立索引及具名函数是否都位于可点击按钮内。优先用原文可核实的定义。含义有歧义时在相应卡片注明。

## 完整图与有字母的子图

```json
{
  "figures": {
    "7": {
      "title": "图 7｜消融实验",
      "source": "PDF 第 7 页，Fig. 7",
      "image": "figures/fig7.png",
      "description": "用一段话解释整图的坐标、图例、观察及边界。",
      "panel_evidence": "图注明确标注 (a) 和 (b)。",
      "panels": [
        {"letter":"a", "box":[0.01,0.04,0.48,0.47], "title":"条件一",
         "description":"看哪些轴与对照、直接结果及边界。"}
      ]
    }
  }
}
```

在方法、结果或实验的 `figures` 数组写图 ID，例如 `["7"]`。每张图需至少被引用一次。没有面板字母时省略 `panels` 和 `panel_evidence`。有面板时人工核对 `box=[左,上,右,下]`（相对整图，范围 0–1），包含轴、数值与图例；可加可选字段 `image` 指向独立裁图，否则浏览器从整图裁剪。图或数据未提供时，省略图片、保留出处文字；不得生成看似来自论文的替代图。

视觉参考是用户自制的 `TSGSAN_Reader_v6.html`。模板保留其颜色变量、标题区、编号导航、三问卡、方法与公式卡、绿色结果标签和回顾链；不把参考文件里的论文结论和图片带入后续论文。
