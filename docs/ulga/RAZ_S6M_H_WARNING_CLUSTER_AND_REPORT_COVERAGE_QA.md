# RAZ-S6M_H_WarningClusterAndReportCoverageQA

## 1. Task name

- `RAZ-S6M_H_WarningClusterAndReportCoverageQA`

## 2. Objective

- Analyze `Level H` warning clusters after `S6L`.
- Verify warning-report coverage alignment between enriched `qa_tags` and `raz_tagging_warnings.json`.
- Decide whether the next step should be warning comparison QA, taxonomy/pattern planning, or a warning-report coverage patch.

## 3. Scope guardrails

- `Level H` QA only.
- No `Level I-W` processing.
- No seed query expansion beyond `A-F`.
- No content promotion.
- No CEFR/adaptive/learner-state changes.
- No production pipeline rewrite in this task.

## 4. Preflight

- Inspected `S6L` smoke-pilot artifacts and confirmed build integrity remained `PASS` for count parity, schema, traceability, duplicate ID, forbidden audio, and authority boundaries.
- Confirmed `S6L` already documented a reporting gap where `unknown_pattern` and `human_review_required` were preserved in enriched `qa_tags` but absent from the flat warning report.
- Inspected `Level H` normalized/enriched artifacts, tagging reports, `S6K` / `S6K1` baselines, seed query policy/validation, discovery validation, drift validation, and the active tagging pipeline code path.

## 5. Files inspected

- `docs/ulga/RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md`
- `ulga/reports/raz_h_derived_build_second_smoke_pilot.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_reuse_unit_enriched.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `ulga/reports/raz_g_warning_cluster_qa.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`

## 6. Files created

- `tools/raz_h_warning_cluster_and_report_coverage_qa.py`
- `tests/ulga/test_raz_h_warning_cluster_and_report_coverage_qa.py`
- `docs/ulga/RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md`
- `ulga/reports/raz_h_warning_cluster_and_report_coverage_qa.json`

## 7. Files modified

- `None`

## 8. S6L build integrity recap

- Source smoke-pilot status: `PASS_WITH_WARNINGS`
- Count parity: `PASS`
- Schema validation: `PASS`
- Traceability: `PASS`
- Duplicate ID check: `PASS`
- Forbidden audio field check: `PASS`

## 9. H warning distribution from qa_tags

- `unknown_theme = 404`
- `unknown_pattern = 199`
- `unknown_grammar = 175`
- `section_heading_detected = 167`
- `human_review_required = 545`
- `malformed_or_schema_warning = 0`
- `dialogue_or_quotation_warning = 0`
- `new_warning_types = ['unknown_pattern']`

## 10. H warning distribution from flat report

- `unknown_theme = 404`
- `unknown_pattern = 199`
- `unknown_grammar = 175`
- `section_heading_detected = 167`
- `human_review_required = 545`
- `malformed_or_schema_warning = 0`
- `dialogue_or_quotation_warning = 0`

## 11. Report coverage matrix

- `unknown_theme`: qa_tags=404, flat=404, delta=0, status=PASS
- `unknown_pattern`: qa_tags=199, flat=199, delta=0, status=PASS
- `unknown_grammar`: qa_tags=175, flat=175, delta=0, status=PASS
- `section_heading_detected`: qa_tags=167, flat=167, delta=0, status=PASS
- `human_review_required`: qa_tags=545, flat=545, delta=0, status=PASS
- `malformed_or_schema_warning`: qa_tags=0, flat=0, delta=0, status=PASS
- `dialogue_or_quotation_warning`: qa_tags=0, flat=0, delta=0, status=PASS

## 12. unknown_pattern cluster analysis

- Count: `199`
- Count by record type: `{'sentence': 199}`
- Overlap with `unknown_theme`: `13`
- Overlap with `unknown_grammar`: `7`
- Overlap with `section_heading_detected`: `0`
- Overlap with `human_review_required`: `13`
- Root cause: `PATTERN_TAXONOMY_GAP`
- Pattern taxonomy gap likelihood: `MEDIUM`
- Reporting artifact likelihood: `LOW`
- Pipeline defect likelihood: `LOW`
- Section-heading-derived likelihood: `LOW`
- Assessment: `unknown_pattern` is sentence-only and mostly falls into normal declarative sentences that simply received no `sentence_pattern_tags`, with smaller poetic, inversion, expressive, and pronunciation-annotation subclusters. This points to rule/taxonomy coverage backlog, not data loss or section-boundary failure.

## 13. section_heading_detected cluster analysis

- Count: `167`
- Count by record type: `{'section_heading': 167}`
- `true_heading_count = 162`
- `ambiguous_heading_count = 5`
- `likely_false_positive_count = 0`
- Classification: `MIXED_TRUE_AND_AMBIGUOUS`
- Section-boundary defect likelihood: `LOW`
- Heading query exclusion should remain: `True`
- Assessment: the sampled records are classic nonfiction headings such as `Around the World`, `A Friend in Brazil`, and bird/species labels. This looks like intended warning-only behavior rather than a sentence-boundary defect.

## 14. human_review_required cluster analysis

- Count: `545`
- Overlap with `unknown_pattern`: `13`
- Overlap with `unknown_theme`: `404`
- Overlap with `unknown_grammar`: `96`
- Overlap with `section_heading_detected`: `167`
- Assessment: `mostly_redundant_with_other_warning_families_and_underreported_in_flat_report`

## 15. Warning overlap matrix

- `unknown_theme` vs `unknown_pattern`: `13`
- `unknown_theme` vs `unknown_grammar`: `25`
- `unknown_theme` vs `section_heading_detected`: `26`
- `unknown_theme` vs `human_review_required`: `404`
- `unknown_pattern` vs `unknown_grammar`: `7`
- `unknown_pattern` vs `section_heading_detected`: `0`
- `unknown_pattern` vs `human_review_required`: `13`
- `unknown_grammar` vs `section_heading_detected`: `83`
- `unknown_grammar` vs `human_review_required`: `96`
- `section_heading_detected` vs `human_review_required`: `167`

## 16. Top warning-contributing books/pages/units

- Top books: `[{'key': '1382 | Pip, the Monster Princess', 'count': 91}, {'key': '263 | Cool as a Cuke', 'count': 89}, {'key': '262 | Club Monster', 'count': 88}, {'key': '945 | Tag-Along Goat', 'count': 87}, {'key': "1148 | Nami's Gifts", 'count': 79}, {'key': '1456 | Anna and the Dancing Goose', 'count': 71}, {'key': '3886 | Welcome to Turkey', 'count': 70}, {'key': '1523 | The Day I Needed Help', 'count': 63}, {'key': '3595 | Hedgehogs', 'count': 61}, {'key': '100 | The Owl and the Pussycat', 'count': 54}]`
- Top page units: `[{'key': 'RAZ_H_1523_P008', 'count': 18}, {'key': 'RAZ_H_890_P006', 'count': 18}, {'key': 'RAZ_H_3886_P015', 'count': 17}, {'key': 'RAZ_H_3595_P013', 'count': 16}, {'key': 'RAZ_H_3865_P003', 'count': 16}, {'key': 'RAZ_H_1148_P007', 'count': 15}, {'key': 'RAZ_H_1369_P012', 'count': 15}, {'key': 'RAZ_H_1382_P005', 'count': 15}, {'key': 'RAZ_H_1382_P008', 'count': 15}, {'key': 'RAZ_H_1523_P011', 'count': 15}]`

## 17. Representative samples

- `unknown_pattern`: `[{'record_id': 'RAZ_H_100_CAND_000001', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P003', 'text': 'The Owl and the Pussycat went to sea in a beautiful pea-green boat.', 'warnings': ['unknown_pattern'], 'review_status': 'pending'}, {'record_id': 'RAZ_H_100_CAND_000013', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P009', 'text': 'They then sailed away for a year and a day to the land where the Pong-tree grows.', 'warnings': ['unknown_pattern'], 'review_status': 'pending'}, {'record_id': 'RAZ_H_100_CAND_000014', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P010', 'text': 'And there in the wood a piggy-wig stood.', 'warnings': ['human_review_required', 'unknown_pattern', 'unknown_theme'], 'review_status': 'human_review_required'}]`
- `section_heading_detected`: `[{'record_id': 'RAZ_H_101_CAND_000001', 'record_type': 'section_heading', 'book_id': '101', 'title': 'Friends Around the World', 'page_unit_id': 'RAZ_H_101_P004', 'text': 'Around the World', 'warnings': ['human_review_required', 'section_heading_detected', 'unknown_grammar'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_H_101_CAND_000004', 'record_type': 'section_heading', 'book_id': '101', 'title': 'Friends Around the World', 'page_unit_id': 'RAZ_H_101_P005', 'text': 'A Friend in Brazil', 'warnings': ['human_review_required', 'section_heading_detected'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_H_101_CAND_000010', 'record_type': 'section_heading', 'book_id': '101', 'title': 'Friends Around the World', 'page_unit_id': 'RAZ_H_101_P007', 'text': 'A Friend in China', 'warnings': ['human_review_required', 'section_heading_detected'], 'review_status': 'human_review_required'}]`
- `human_review_required`: `[{'record_id': 'RAZ_H_100_CAND_000003', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P005', 'text': 'The Owl looked up at the stars above.', 'warnings': ['human_review_required', 'unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_H_100_CAND_000004', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P005', 'text': 'He sang with a small guitar.', 'warnings': ['human_review_required', 'unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_H_100_CAND_000006', 'record_type': 'sentence', 'book_id': '100', 'title': 'The Owl and the Pussycat', 'page_unit_id': 'RAZ_H_100_P006', 'text': 'What a beautiful Kitty you are,', 'warnings': ['human_review_required', 'unknown_theme'], 'review_status': 'human_review_required'}]`

## 18. Root-cause assessment

- Pattern taxonomy gap likelihood: `MEDIUM`
- Reporting gap likelihood: `MEDIUM`
- Pipeline defect likelihood: `LOW`
- Section-boundary defect likelihood: `LOW`
- unknown_pattern root cause: `PATTERN_TAXONOMY_GAP`
- section_heading root cause: `MIXED_TRUE_AND_AMBIGUOUS`
- Report coverage status: `PASS`
- Flat-report undercoverage cause:
  - `unknown_pattern` is appended only to `qa_tags.warnings` in `make_qa_tags` and never appended as a `WarningRecord`.
  - `human_review_required` is derived from `qa_tags.needs_human_review` / `review_status` and is also never emitted as a standalone `WarningRecord`.
  - `raz_tagging_warnings.json` writes only `result.warnings`, so these families are currently invisible in the flat report.

## 19. Seed query layer boundary result

- Queryable levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- `G` exposed: `False`
- `H` exposed: `False`
- Status: `PASS`

## 20. Authority boundary result

- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 21. Validator results

- `validate_raz_level_discovery = PASS`
- `validate_raz_reusable_content_seed_query_layer = PASS`
- `validate_raz_downstream_discovery_drift = PASS_WITH_WARNINGS`
- `must_fix_count = 0`

## 22. Test results

- ``

## 23. QA status

- `PASS`

## 24. Decision for next stage

- `RUN_GH_WARNING_COMPARISON_QA`

## 25. Next recommended task

- `GH warning comparison or taxonomy/pattern patch planning`

