# RAZ-S6Q_GH_TaggingRerunDeltaQA

## 1. Task name

`RAZ-S6Q_GH_TaggingRerunDeltaQA`

## 2. Objective

Run an independent G/H delta QA after S6P and verify warning reductions, flat-report parity, schema/count stability, and query/authority boundaries without introducing rule pollution.

## 3. Scope guardrails

- G/H only.
- QA only. No taxonomy, pattern, grammar, query, authority, or promotion changes.
- No I-W processing.
- No G/H query exposure.

## 4. Preflight

- S6P implementation status: `PASS`
- Current queryable levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- Current S6F must_fix_count: `0`
- Read-only QA: `True`
- Production code modified: `False`

## 5. Files inspected

- `docs/ulga/RAZ_S6P_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_implementation.json`
- `docs/ulga/RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_plan.json`
- `docs/ulga/RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md`
- `ulga/reports/raz_warning_report_coverage_patch.json`
- `docs/ulga/RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md`
- `ulga/reports/raz_h_warning_cluster_and_report_coverage_qa.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `tools/raz_h_warning_cluster_and_report_coverage_qa.py`
- `tests/ulga/test_raz_h_warning_cluster_and_report_coverage_qa.py`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_reuse_unit_enriched.json`

## 6. Files created

- `tools/raz_gh_tagging_rerun_delta_qa.py`
- `tests/ulga/test_raz_gh_tagging_rerun_delta_qa.py`
- `docs/ulga/RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md`
- `ulga/reports/raz_gh_tagging_rerun_delta_qa.json`

## 7. Files modified

- `tools/raz_gh_tagging_rerun_delta_qa.py`
- `tests/ulga/test_raz_gh_tagging_rerun_delta_qa.py`
- `docs/ulga/RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md`
- `ulga/reports/raz_gh_tagging_rerun_delta_qa.json`

## 8. Source status from S6P

- S6P status: `PASS`
- S6P decision: `RUN_GH_TAGGING_RERUN_DELTA_QA`

## 9. Baseline metrics

- `G`: enriched=4067, unknown_theme=837, unknown_pattern=643, unknown_grammar=145, section_heading=101, human_review=897
- `H`: enriched=4548, unknown_theme=734, unknown_pattern=660, unknown_grammar=175, section_heading=167, human_review=832

## 10. Current metrics

- `G`: enriched=4067, unknown_theme=616, unknown_pattern=242, unknown_grammar=145, section_heading=101, human_review=691, malformed=0, dialogue=0
- `H`: enriched=4548, unknown_theme=404, unknown_pattern=199, unknown_grammar=175, section_heading=167, human_review=545, malformed=0, dialogue=0

## 11. Delta metrics

- `G`: unknown_theme=-221, unknown_pattern=-401, unknown_grammar=0, section_heading=0, human_review=-206
- `H`: unknown_theme=-330, unknown_pattern=-461, unknown_grammar=0, section_heading=0, human_review=-287

## 12. Delta classification

- `G`: {'unknown_theme': 'EXPECTED_IMPROVEMENT', 'unknown_pattern': 'EXPECTED_IMPROVEMENT', 'unknown_grammar': 'STABLE_ACCEPTABLE', 'section_heading_detected': 'STABLE_ACCEPTABLE', 'human_review_required': 'EXPECTED_IMPROVEMENT', 'malformed_or_schema_warning': 'STABLE_ACCEPTABLE', 'dialogue_or_quotation_warning': 'STABLE_ACCEPTABLE'}
- `H`: {'unknown_theme': 'EXPECTED_IMPROVEMENT', 'unknown_pattern': 'EXPECTED_IMPROVEMENT', 'unknown_grammar': 'STABLE_ACCEPTABLE', 'section_heading_detected': 'STABLE_ACCEPTABLE', 'human_review_required': 'EXPECTED_IMPROVEMENT', 'malformed_or_schema_warning': 'STABLE_ACCEPTABLE', 'dialogue_or_quotation_warning': 'STABLE_ACCEPTABLE'}

## 13. Flat report coverage check

- Status: `PASS`
- `G / unknown_theme`: qa_tags=616, flat=616, delta=0, status=PASS
- `G / unknown_pattern`: qa_tags=242, flat=242, delta=0, status=PASS
- `G / unknown_grammar`: qa_tags=145, flat=145, delta=0, status=PASS
- `G / section_heading_detected`: qa_tags=101, flat=101, delta=0, status=PASS
- `G / human_review_required`: qa_tags=691, flat=691, delta=0, status=PASS
- `G / malformed_or_schema_warning`: qa_tags=0, flat=0, delta=0, status=PASS
- `G / dialogue_or_quotation_warning`: qa_tags=0, flat=0, delta=0, status=PASS
- `H / unknown_theme`: qa_tags=404, flat=404, delta=0, status=PASS
- `H / unknown_pattern`: qa_tags=199, flat=199, delta=0, status=PASS
- `H / unknown_grammar`: qa_tags=175, flat=175, delta=0, status=PASS
- `H / section_heading_detected`: qa_tags=167, flat=167, delta=0, status=PASS
- `H / human_review_required`: qa_tags=545, flat=545, delta=0, status=PASS
- `H / malformed_or_schema_warning`: qa_tags=0, flat=0, delta=0, status=PASS
- `H / dialogue_or_quotation_warning`: qa_tags=0, flat=0, delta=0, status=PASS

## 14. Count parity

- `G`: `PASS`
- `H`: `PASS`

## 15. Schema validation

- `G`: `PASS`
- `H`: `PASS`

## 16. Rule pollution audit

- Status: `PASS`
- simple declarative: `Current simple declarative tags stay inside ordinary declarative scope.`
- heading exclusion: `Section headings remain excluded from simple declarative tagging.`
- dialogue exclusion: `Quoted/direct speech remains excluded from P0 declarative tags.`
- deferred poetry/inversion/artifact: `Deferred poetry/inversion/artifact residuals remain deferred and untagged by P0 declarative rules.`

## 17. Theme mapping audit

- Status: `PASS`
- science/nature/body/health: `science/nature/body/health samples align with current mapped themes.`
- history/civics: `history/biography/civics samples align with current mapped themes.`
- animal nonfiction: `animal nonfiction samples align with current mapped themes.`
- folktale/storyfable: `folktale/storyfable samples align with current mapped themes.`

## 18. Human review audit

- Status: `PASS`
- direct_suppression_detected: `False`
- indirect_reduction_confirmed: `True`
- assessment: `Every current human_review_required record still carries at least one underlying warning family, so the observed reduction is consistent with indirect overlap shrinkage.`

## 19. Duplicate warning check

- Status: `PASS`
- duplicate_count: `0`

## 20. Traceability check

- Status: `PASS`
- missing_trace_count: `0`

## 21. Seed query layer boundary

- queryable_levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- g_exposed: `False`
- h_exposed: `False`
- status: `PASS`

## 22. Authority boundary

- candidate_only: `PASS`
- promotion_allowed: `PASS`

## 23. Validator results

- validate_raz_level_discovery: `PASS`
- validate_raz_reusable_content_seed_query_layer: `PASS`
- validate_raz_downstream_discovery_drift: `PASS_WITH_WARNINGS`
- must_fix_count: `0`

## 24. Test results

- `py_compile_s6q_helper`: `PASS`
- `pytest_s6q_helper`: `3 passed in 0.03s`
- `validate_raz_level_discovery`: `PASS`
- `validate_raz_reusable_content_seed_query_layer`: `PASS`
- `validate_raz_downstream_discovery_drift`: `PASS_WITH_WARNINGS (must_fix_count=0)`
- `pytest_validators`: `23 passed in 19.95s`
- `pytest_pipeline`: `13 passed, 20 subtests passed in 0.07s`
- `pytest_h_warning_helper`: `3 passed in 0.02s`

## 25. QA status

`PASS`

## 26. Risk level

`Low`

## 27. Decision for next stage

`RUN_GH_P1_PATCH_PLAN`

## 28. Next recommended task

`RAZ-S6R_GH_P1_PATCH_PLAN`

