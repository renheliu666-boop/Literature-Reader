# Literature Reader JSON Data Schema

该文件定义结构化论文分析的数据组织建议。它是供 Skill 生成数据和 HTML 读取的逻辑 schema，不要求所有论文都填满每个字段。缺少证据时使用 `null`、空数组或 `status: "not_reported"`，不要编造。

## Top-level structure

```json
{
  "paper_metadata": {},
  "source_scope": {},
  "reading_guide": {},
  "key_findings": [],
  "finding_method_links": [],
  "method_tree": {},
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

## Field definitions

### paper_metadata
- `title`
- `authors[]`
- `journal`
- `year`
- `volume`
- `issue`
- `pages`
- `doi`
- `source_file`

### source_scope
- `full_text_read`：boolean
- `materials_used[]`：PDF、补充材料、代码、外部资料
- `pages_reviewed[]`
- `limitations`

### reading_guide
- `research_question`
  - `object`
  - `problem`
  - `why_important`
  - `expected_value`
  - `evidence_refs[]`
- `prior_work[]`
  - `research_route`
  - `typical_approach`
  - `what_it_solves`
  - `limitations`
  - `paper_entry_point`
  - `evidence_refs[]`
- `core_intuition`
  - `plain_language`
  - `key_observation`
  - `why_method_fits`
  - `evidence_refs[]`

### key_findings[]
- `id`
- `title`
- `finding`
- `quantitative_result`
- `evidence_refs[]`
- `supporting_methods[]`
- `experiment_refs[]`
- `evidence_boundary`
- `information_type`：`paper_original` / `other_literature` / `inference` / `unknown`

### finding_method_links[]
- `finding_id`
- `method_ids[]`
- `experiment_ids[]`
- `figure_panel_refs[]`
- `relationship_type`：`sequence` / `composition` / `parallel` / `validation` / `support`
- `explanation`

### method_tree
- `root`
- `nodes[]`
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

### equations[]
- `id`
- `equation_number`
- `original_expression`
- `variables[]`
- `input`
- `output`
- `role_in_method`
- `plain_language`
- `source_ref`
- `uncertainties[]`

### experiments
- `datasets[]`
- `data_splits`
- `tasks`
- `prediction_horizon`
- `metrics[]`
- `baselines[]`
- `hyperparameters`
- `reproducibility_notes`

### results[]
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

### figures[]
- `id`
- `figure_number`
- `page`
- `image_asset`
- `caption`
- `panels[]`
  - `id`
  - `original_label`
  - `hotspot_label`
  - `hotspot_coordinates`
  - `purpose`
  - `how_to_read`
  - `observations`
  - `argument_supported`
  - `evidence_boundary`
  - `finding_ids[]`
  - `method_ids[]`
  - `source_ref`
  - `confidence`
- `hotspot_note`

### reviewer_assessment[]
- `issue`
- `evidence`
- `why_it_matters`
- `affected_claim`
- `suggested_validation`
- `severity`
- `information_type`

### transfer_insights[]
- `idea`
- `transferability`：`direct` / `adaptation_required` / `not_directly_transferable`
- `why`
- `required_changes`
- `research_question`
- `information_type`：通常为 `inference`

### glossary[]
- `term`
- `full_name`
- `chinese_translation`
- `meaning_in_this_paper`
- `role`
- `distinction`
- `source_ref`

### unresolved_questions[]
- `question`
- `why_unresolved`
- `needed_material`
- `impact`

## Source references

`source_ref` 建议使用统一格式：

```json
{
  "type": "pdf_page | figure | table | equation | supplement | external_source",
  "locator": "p. 5, Fig. 3b, Table II, Eq. (7)",
  "quote_or_evidence": "短句或数值定位",
  "url_or_file": null
}
```

引用内容必须短且可定位。不要只写“见论文”。
