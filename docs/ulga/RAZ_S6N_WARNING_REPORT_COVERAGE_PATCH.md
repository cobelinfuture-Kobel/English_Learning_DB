# RAZ-S6N_WarningReportCoveragePatch

## 1. Task name

- `RAZ-S6N_WarningReportCoveragePatch`

## 2. Objective

- Patch `raz_tagging_warnings.json` generation so flat warning reporting fully reflects warning families already present in enriched `qa_tags`.
- Fix the `S6M` undercoverage gap for `unknown_pattern` and `human_review_required` without changing tagging semantics.

## 3. Scope guardrails

- No `I-W` processing.
- No full `G-W` build.
- No seed query expansion beyond `A-F`.
- No promotion.
- No CEFR/adaptive/learner-state change.
- No taxonomy, pattern, or grammar rule change.

## 4. Preflight

- Inspected `S6M` QA artifacts and confirmed the pre-patch gap:
  - `Level H unknown_pattern = 660` in `qa_tags`, `0` in flat report
  - `Level H human_review_required = 832` in `qa_tags`, `0` in flat report
- Inspected current warning emission logic in `tools/raz_normalized_tagging_pipeline.py`.
- Confirmed root cause was report emission only:
  - `unknown_pattern` was appended to `qa_tags.warnings` but not to `result.warnings`
  - `human_review_required` was derived from `qa_tags.needs_human_review` / `review_status` but not emitted into `result.warnings`

## 5. Files inspected

- `docs/ulga/RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md`
- `ulga/reports/raz_h_warning_cluster_and_report_coverage_qa.json`
- `tools/raz_h_warning_cluster_and_report_coverage_qa.py`
- `tests/ulga/test_raz_h_warning_cluster_and_report_coverage_qa.py`
- `docs/ulga/RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md`
- `ulga/reports/raz_h_derived_build_second_smoke_pilot.json`
- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `ulga/reports/raz_g_warning_cluster_qa.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 6. Files modified

- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`

## 7. Files created

- `docs/ulga/RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md`
- `ulga/reports/raz_warning_report_coverage_patch.json`

## 8. Patch summary

- Added a minimal warning emission helper with duplicate prevention for `(record_id, warning_type)`.
- Preserved existing `qa_tags`, `needs_human_review`, and `review_status` semantics.
- Added flat warning emission for:
  - `unknown_pattern`
  - `human_review_required`
- Left `unknown_theme`, `unknown_grammar`, and `section_heading_detected` behavior unchanged.

## 9. Pre-patch coverage gap

- `unknown_pattern`:
  - `qa_tags_count = 660`
  - `flat_report_count = 0`
  - `coverage_status = MISSING_FROM_FLAT_REPORT`
- `human_review_required`:
  - `qa_tags_count = 832`
  - `flat_report_count = 0`
  - `coverage_status = MISSING_FROM_FLAT_REPORT`

## 10. Implementation details

- Introduced `append_warning_record(...)` in `tools/raz_normalized_tagging_pipeline.py`.
- Replaced direct `warnings.append(WarningRecord(...))` calls inside `make_qa_tags(...)` with the helper so same-record duplicate families are blocked consistently.
- Emitted:
  - `unknown_pattern` with message `No sentence pattern tag was confidently inferred by S4 rule-based tagger.`
  - `human_review_required` with message `Record requires human review due to QA warning flags.`
- No taxonomy inference, pattern inference, grammar inference, review-state logic, or authority logic was changed.

## 11. Validation levels used

- Explicit pipeline rerun used `Level G` and `Level H`
- Command:
  - `python tools/raz_normalized_tagging_pipeline.py --levels G H`
- `S6M` helper remains `Level H`-focused for coverage-matrix QA, which is acceptable for this task and documented.

## 12. Post-patch coverage matrix

- `unknown_theme`: qa_tags=`734`, flat=`734`, delta=`0`, status=`PASS`
- `unknown_pattern`: qa_tags=`660`, flat=`660`, delta=`0`, status=`PASS`
- `unknown_grammar`: qa_tags=`175`, flat=`175`, delta=`0`, status=`PASS`
- `section_heading_detected`: qa_tags=`167`, flat=`167`, delta=`0`, status=`PASS`
- `human_review_required`: qa_tags=`832`, flat=`832`, delta=`0`, status=`PASS`
- `malformed_or_schema_warning`: qa_tags=`0`, flat=`0`, delta=`0`, status=`PASS`
- `dialogue_or_quotation_warning`: qa_tags=`0`, flat=`0`, delta=`0`, status=`PASS`

Additional validation signal from the refreshed flat report for `G/H`:

- `Level G`: `unknown_theme=837`, `unknown_pattern=643`, `unknown_grammar=145`, `section_heading_detected=101`, `human_review_required=897`
- `Level H`: `unknown_theme=734`, `unknown_pattern=660`, `unknown_grammar=175`, `section_heading_detected=167`, `human_review_required=832`

## 13. Duplicate warning check

- Status: `PASS`
- `duplicate_count = 0`

## 14. Traceability check

- Status: `PASS`
- `missing_trace_count = 0`
- Flat warning entries preserve `record_id`, `level`, `book_id`, and `raw_file_path`.

## 15. Warning semantics check

- `warning_counts_lowered = false`
- `qa_tags_semantics_changed = false`
- `review_status_semantics_changed = false`
- `taxonomy_or_pattern_rule_changed = false`
- `grammar_rule_changed = false`

## 16. Seed query layer boundary

- Queryable levels after patch:
  - `A`
  - `B`
  - `C`
  - `D`
  - `E`
  - `F`
- `G exposed = false`
- `H exposed = false`
- Status: `PASS`

## 17. Authority boundary

- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 18. Validator results

- `validate_raz_level_discovery = PASS`
- `validate_raz_reusable_content_seed_query_layer = PASS`
- `validate_raz_downstream_discovery_drift = PASS_WITH_WARNINGS`
- `must_fix_count = 0`

## 19. Test results

- `python -m py_compile tools/raz_normalized_tagging_pipeline.py` -> `PASS`
- `python -m py_compile tools/raz_h_warning_cluster_and_report_coverage_qa.py` -> `PASS`
- `python -m pytest tests/test_raz_normalized_tagging_pipeline.py -q` -> `6 passed, 8 subtests passed`
- `python -m pytest tests/ulga/test_raz_h_warning_cluster_and_report_coverage_qa.py -q` -> `3 passed`
- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q` -> `23 passed`

## 20. Patch status

- `PASS`

## 21. Risk level

- `Medium`

Residual risk:

- The report-coverage bug is fixed, but the newly visible `unknown_pattern` counts for `G` and `H` confirm a real pattern-taxonomy backlog that should be handled separately.

## 22. Decision for next stage

- `RUN_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN`

## 23. Next recommended task

- Run a focused `G/H` taxonomy-and-pattern patch planning task now that flat warning reporting is trustworthy enough for cross-level comparison.
