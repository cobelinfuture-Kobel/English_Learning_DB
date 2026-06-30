# RAZ-S6U_I_DERIVED_BUILD_THIRD_SMOKE_PILOT

## 1. Task name
`RAZ-S6U_I_DerivedBuildThirdSmokePilot`

## 2. Objective
Run a Level I-only derived build smoke pilot after G/H P0+P1 tagging improvements and verify structural safety, warning coverage, and boundary stability before any further expansion.

## 3. Scope guardrails
- Level I only.
- No J-W processing.
- No full G-W build.
- No G/H/I seed-query exposure.
- No promotion, CEFR, adaptive, or learner-state changes.
- No broad taxonomy/pattern/grammar changes were implemented for this task.

## 4. Preflight
- S6T status: `PASS_WITH_WARNINGS`
- S6S accepted: `True`
- Queryable levels before run: `['A', 'B', 'C', 'D', 'E', 'F']`
- S6F must_fix_count before run: `0`
- Level I raw input status: `PASS`
- Level I timeline JSON count: `88`
- Level I preexisting derived status: `ABSENT`
- Current run classification: `FIRST_BUILD`
- Expected mutation scope remained Level I derived outputs plus shared reports/validators only.

## 5. Files inspected
- `docs/ulga/RAZ_S6T_GH_P1_PATCH_DELTA_QA.md`
- `ulga/reports/raz_gh_p1_patch_delta_qa.json`
- `docs/ulga/RAZ_S6S_GH_P1_TARGETED_PATCH_IMPLEMENTATION.md`
- `ulga/reports/raz_gh_p1_targeted_patch_implementation.json`
- `docs/ulga/RAZ_S6R_GH_P1_TARGETED_PATCH_PLAN.md`
- `ulga/reports/raz_gh_p1_targeted_patch_plan.json`
- `docs/ulga/RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md`
- `ulga/reports/raz_gh_tagging_rerun_delta_qa.json`
- `docs/ulga/RAZ_S6P_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_implementation.json`
- `docs/ulga/RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_plan.json`
- `raz_output_jsons/Level_I/*`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 6. Files modified/refreshed
- `raz_output_jsons/derived/Level_I/normalized/raz_I_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_I/normalized/raz_I_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_I/normalized/raz_I_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_I/enriched/raz_I_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_I/enriched/raz_I_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_I/enriched/raz_I_reuse_unit_enriched.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 7. Files created
- `docs/ulga/RAZ_S6U_I_DERIVED_BUILD_THIRD_SMOKE_PILOT.md`
- `ulga/reports/raz_i_derived_build_third_smoke_pilot.json`

## 8. Source status from S6T
- S6T status: `PASS_WITH_WARNINGS`
- S6S patch accepted: `True`
- Watch items carried forward: imperative heading-like acceptance remains a bounded review note.

## 9. Level I raw input status
- Timeline JSON count: `88`
- Raw sentence candidates: `3341`
- Raw page units: `1087`
- Raw reuse units: `1000`
- Raw generated_content=true count: `0`

## 10. Level I pre-build baseline
- `raw_sentence_candidate_count` = `3341`
- `raw_page_unit_count` = `1087`
- `raw_reuse_unit_count` = `1000`
- `normalized_sentence_existing_count` = `0`
- `normalized_page_unit_existing_count` = `0`
- `normalized_reuse_unit_existing_count` = `0`
- `enriched_sentence_existing_count` = `0`
- `enriched_page_unit_existing_count` = `0`
- `enriched_reuse_unit_existing_count` = `0`

## 11. Build command
`python tools/raz_normalized_tagging_pipeline.py --levels I`

## 12. Post-build metrics
- `normalized_sentence_count` = `3341`
- `normalized_page_unit_count` = `1087`
- `normalized_reuse_unit_count` = `1000`
- `enriched_sentence_count` = `3341`
- `enriched_page_unit_count` = `1087`
- `enriched_reuse_unit_count` = `1000`

## 13. Count parity
- `sentence`: `PASS`
- `page_unit`: `PASS`
- `reuse_unit`: `PASS`

## 14. Schema validation
- Status: `PASS`
- Error count: `0`

## 15. Traceability check
- Status: `PASS`
- Missing trace count: `0`

## 16. Duplicate ID check
- Status: `PASS`
- Duplicate count: `0`

## 17. Forbidden audio field check
- Status: `PASS`
- Offending count: `0`

## 18. Warning distribution
- `unknown_theme` = `896`
- `unknown_pattern` = `299`
- `unknown_grammar` = `241`
- `section_heading_detected` = `184`
- `human_review_required` = `1007`
- `malformed_or_schema_warning` = `0`
- `dialogue_or_quotation_warning` = `0`
- `new_warning_types` = `[]`

## 19. Flat report coverage check
- Status: `PASS`
- `unknown_theme`: qa_tags=`896`, flat=`896`, delta=`0`, status=`PASS`
- `unknown_pattern`: qa_tags=`299`, flat=`299`, delta=`0`, status=`PASS`
- `unknown_grammar`: qa_tags=`241`, flat=`241`, delta=`0`, status=`PASS`
- `section_heading_detected`: qa_tags=`184`, flat=`184`, delta=`0`, status=`PASS`
- `human_review_required`: qa_tags=`1007`, flat=`1007`, delta=`0`, status=`PASS`
- `malformed_or_schema_warning`: qa_tags=`0`, flat=`0`, delta=`0`, status=`PASS`
- `dialogue_or_quotation_warning`: qa_tags=`0`, flat=`0`, delta=`0`, status=`PASS`

## 20. Sample audits
- Theme mapping: `PASS_WITH_WARNINGS`; top residual unknown-theme books = `[{'key': "779 | Alistair's Night", 'count': 40}, {'key': '273 | Monster Soccer', 'count': 31}, {'key': '3605 | Cy and Medusa', 'count': 26}, {'key': '1212 | A Visit to the Zoo', 'count': 25}, {'key': '3666 | Rocket Boots', 'count': 25}]`
- Simple declarative pattern: `PASS`; sample_count=`1909`, suspicious_count=`0`
- Imperative watch: `PASS`; imperative_sample_count=`8`, heading_like_accepted_count=`0`
- Section heading: `PASS`; section_heading_count=`184`
- Human review: `PASS_WITH_WARNINGS`; human_review_count=`1007`

## 21. Seed query layer boundary
- Queryable levels after run: `['A', 'B', 'C', 'D', 'E', 'F']`
- `g_exposed = false`
- `h_exposed = false`
- `i_exposed = false`
- Status: `PASS`

## 22. Authority boundary
- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 23. Validator results
- `validate_raz_level_discovery` = `PASS`
- `validate_raz_reusable_content_seed_query_layer` = `PASS`
- `validate_raz_downstream_discovery_drift` = `PASS_WITH_WARNINGS`
- `must_fix_count` = `0`

## 24. Test results
- `py_compile_pipeline` = `PASS`
- `pytest_pipeline` = `16 passed, 26 subtests passed in 0.05s`
- `pipeline_build` = `PASS (python tools/raz_normalized_tagging_pipeline.py --levels I)`
- `validate_raz_level_discovery` = `PASS`
- `validate_raz_reusable_content_seed_query_layer` = `PASS`
- `validate_raz_downstream_discovery_drift` = `PASS_WITH_WARNINGS (must_fix_count=0)`
- `pytest_validators` = `23 passed in 20.27s`

## 25. Smoke pilot status
`PASS_WITH_WARNINGS`

## 26. Risk level
`Low`

## 27. Decision for next stage
`RUN_I_WARNING_CLUSTER_AND_COVERAGE_QA`

## 28. Next recommended task
`RUN_I_WARNING_CLUSTER_AND_COVERAGE_QA`
