# Literature Reader JSON Data Schema

本文件定义结构化论文分析的数据组织方式。字段不要求全部填满。缺少证据时使用 `null`、空数组、空字符串或 `status: "not_reported"`，不要编造。

## Top-level structure

```json
{
  "paper_metadata": {},
  "source_scope": {},
  "reading_guide": {
    "research_question": {},
    "prior_work": [],
    "core_intuition": {}
  },
  "key_findings": [],
  "finding_method_links": [],
  "method_tree": {"root": "", "nodes": []},
  "equations": [],
  "experiments": {},
  "results": [],
  "figures": [],
  "reviewer_assessment": [],
  "transfer_insights": [],
  "glossary": [],
  "unresolved_questions": []
}
```

## paper_metadata

- `title`：论文标题，必填。
- `subtitle`：可选副标题或中文标题。
- `authors[]`：作者。
- `journal`、`year`、`volume`、`issue`、`pages`、`doi`。
- `source_file`：原始论文文件名。
- `citation_note`：其他书目信息。

## source_scope

- `full_text_read`：是否阅读全文。
- `materials_used[]`：PDF、补充材料、代码、外部资料等。
- `pages_reviewed[]`：实际阅读页码。
- `limitations`：材料范围和阅读限制。

## reading_guide

### research_question

- `object`：研究对象和场景。
- `problem`：具体研究问题。
- `why_important`：为什么重要。
- `expected_value`：解决后可能产生的价值。
- `evidence_refs[]`：原文证据位置。

### prior_work[]

- `research_route`：前人研究路线。
- `typical_approach`：典型做法。
- `what_it_solves`：能够解决什么。
- `limitations`：已知局限；作者未讨论时应注明。
- `paper_entry_point`：本文切入点。
- `evidence_refs[]`：证据位置。

### core_intuition

- `plain_language`：通俗解释。
- `key_observation`：核心观察。
- `why_method_fits`：方法为何适合。
- `evidence_refs[]`：证据位置。

## key_findings[]

- `id`
- `title`
- `finding`
- `quantitative_result`
- `evidence_refs[]`
- `supporting_methods[]`
- `experiment_refs[]`
- `evidence_boundary`
- `information_type`：`paper_original` / `other_literature` / `inference` / `unknown`

## finding_method_links[]

- `finding_id`
- `method_ids[]`
- `experiment_ids[]`
- `figure_panel_refs[]`
- `relationship_type`：`sequence` / `composition` / `parallel` / `validation` / `support`
- `explanation`

## method_tree

- `root`
- `nodes[]`：
  - `id`
  - `parent_id`
  - `name`
  - `description`
  - `input`
  - `operation`
  - `output`
  - `purpose`
  - `relationship_type`
  - `source_refs[]`
  - `sibling_color_group`

同一 `parent_id` 的节点属于同一层级分支。`sibling_color_group` 可显式指定并列节点的颜色组；不填写时由构建器按父节点自动分组。

## equations[]

- `id`
- `equation_number`
- `original_expression`
- `variables[]`：每项可含 `symbol`、`meaning`、`unit`、`dimension`。
- `input`
- `output`
- `role_in_method`
- `plain_language`
- `source_ref`
- `uncertainties[]`

## experiments

- `datasets[]`
- `data_splits`
- `tasks`
- `prediction_horizon`
- `metrics[]`
- `baselines[]`
- `hyperparameters`
- `reproducibility_notes[]`

## results[]

- `id`
- `experiment_id`
- `finding_id`
- `metric`
- `value`
- `unit`
- `comparison`
- `interpretation`
- `source_ref`
- `caveat`

## figures[]

- `id`
- `figure_number`
- `page`
- `image_asset`：相对于 JSON 文件所在目录的本地图片路径。
- `caption`
- `panels[]`：
  - `id`
  - `original_label`
  - `hotspot_label`
  - `hotspot_coordinates`：`[x0, y0, x1, y1]`，归一化 0–1 坐标。
  - `title`
  - `purpose`
  - `how_to_read`
  - `observations`
  - `argument_supported`
  - `evidence_boundary`
  - `finding_ids[]`
  - `method_ids[]`
  - `source_ref`
  - `confidence`

## reviewer_assessment[]

- `issue`
- `evidence`
- `why_it_matters`
- `affected_claim`
- `suggested_validation`
- `severity`
- `information_type`

## transfer_insights[]

- `idea`
- `transferability`：`direct` / `adaptation_required` / `not_directly_transferable`
- `why`
- `required_changes`
- `research_question`
- `information_type`：通常为 `inference`

## glossary[]

- `term`
- `full_name`
- `chinese_translation`
- `meaning_in_this_paper`
- `role`
- `distinction`
- `source_ref`

## unresolved_questions[]

- `question`
- `why_unresolved`
- `needed_material`
- `impact`

## Source reference

建议统一使用：

```json
{
  "type": "pdf_page | figure | table | equation | supplement | external_source",
  "locator": "p. 5, Fig. 3b, Table II, Eq. (7)",
  "quote_or_evidence": "短句或数值定位",
  "url_or_file": null
}
```

引用内容必须短且可定位，不要只写“见论文”。
