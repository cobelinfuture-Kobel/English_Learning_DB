# RAZ-S6L_H_DerivedBuildSecondSmokePilot

## 1. Task name

- `RAZ-S6L_H_DerivedBuildSecondSmokePilot`

## 2. Objective

- Run the second derived build smoke pilot for `Level H` only.
- Convert `Level H` raw candidate artifacts into normalized and enriched derived artifacts.
- Preserve `candidate_only` authority boundaries and keep seed query exposure at `A-F` only.
- Compare `Level H` warning behavior against the approved `Level G` baseline from `S6K` and `S6K1`.

## 3. Scope guardrails

- Process only `Level H`.
- Do not rebuild `Level G`.
- Do not process `Level I-W`.
- Do not expose `G` or `H` in the seed query layer.
- Do not promote content into any authority layer.
- Do not implement CEFR projection, adaptive selection, or learner-state behavior.

## 4. Change impact before modification

- Affected files:
  - `raz_output_jsons/derived/Level_H/normalized/raz_H_sentence_normalized.jsonl`
  - `raz_output_jsons/derived/Level_H/normalized/raz_H_page_unit_normalized.json`
  - `raz_output_jsons/derived/Level_H/normalized/raz_H_reuse_unit_normalized.json`
  - `raz_output_jsons/derived/Level_H/enriched/raz_H_sentence_enriched.jsonl`
  - `raz_output_jsons/derived/Level_H/enriched/raz_H_page_unit_enriched.json`
  - `raz_output_jsons/derived/Level_H/enriched/raz_H_reuse_unit_enriched.json`
  - `raz_output_jsons/derived/reports/raz_tagging_summary.json`
  - `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
  - `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
  - `ulga/graph/raz_level_discovery_inventory.json`
  - `ulga/reports/raz_level_discovery_summary.json`
  - `ulga/reports/raz_level_discovery_validation.json`
  - `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
  - `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
  - `ulga/reports/raz_downstream_discovery_drift_validation.json`
  - `docs/ulga/RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md`
  - `ulga/reports/raz_h_derived_build_second_smoke_pilot.json`
- Risk level: `Medium`
- Real-trading impact: `None direct`; static corpus, discovery, query-layer, and validator artifacts only.
- Restart required: `No` for static artifacts; only external long-running caches would need reload.

## 5. Preflight

- Inspected `S6K` smoke-pilot artifacts and confirmed `Level G` passed with warnings while preserving count parity, schema, traceability, duplicate ID, forbidden audio, `candidate_only`, and seed-query boundaries.
- Inspected `S6K1` warning-cluster QA and confirmed decision `ALLOW_H_SECOND_PILOT`.
- Inspected `S6J` readiness plan, `S6D` discovery artifacts, `S6F` downstream drift validator, seed query policy/gate artifacts, and the active normalized tagging pipeline.
- Confirmed `raz_output_jsons/Level_H` contains `84` raw timeline JSON files.
- Confirmed `raz_output_jsons/derived/Level_H` did not exist before build, so this run is a first build and not a rerun/refresh.
- Confirmed seed query approved/discovered levels remained `A-F` before build.
- Confirmed direct pipeline dry-run needed UTF-8 console output on Windows because `cp950` console encoding can raise `UnicodeEncodeError` when titles contain non-ASCII characters.

## 6. Files inspected

- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `ulga/reports/raz_g_warning_cluster_qa.json`
- `docs/ulga/RAZ_S6J_GW_DERIVED_BUILD_READINESS_PLAN.md`
- `ulga/reports/raz_gw_derived_build_readiness_plan.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `tools/raz_normalized_tagging_pipeline.py`
- `raz_output_jsons/Level_H`
- `raz_output_jsons/derived/Level_H`

## 7. Files created

- `raz_output_jsons/derived/Level_H/normalized/raz_H_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_reuse_unit_enriched.json`
- `docs/ulga/RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md`
- `ulga/reports/raz_h_derived_build_second_smoke_pilot.json`

## 8. Files modified

- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 9. Build command used

- `python tools/raz_normalized_tagging_pipeline.py --levels H`

Execution note:

- The command was run with `PYTHONIOENCODING=utf-8` in PowerShell to avoid a Windows console `cp950` output failure unrelated to artifact integrity.

## 10. Pre-build Level H baseline

- `timeline_json_count = 84`
- `sentence_candidate_count = 2654`
- `page_unit_count = 1015`
- `reuse_unit_count = 879`
- `normalized_sentence_existing = 0`
- `normalized_page_unit_existing = 0`
- `normalized_reuse_unit_existing = 0`
- `enriched_sentence_existing = 0`
- `enriched_page_unit_existing = 0`
- `enriched_reuse_unit_existing = 0`

## 11. Generated normalized / enriched artifacts

- `normalized_sentence_count = 2654`
- `normalized_page_unit_count = 1015`
- `normalized_reuse_unit_count = 879`
- `enriched_sentence_count = 2654`
- `enriched_page_unit_count = 1015`
- `enriched_reuse_unit_count = 879`

## 12. Count parity result

- Sentence: `PASS`
- Page unit: `PASS`
- Reuse unit: `PASS`
- Raw-to-normalized parity held exactly.
- Normalized-to-enriched parity held exactly.

## 13. Schema validation result

- `raz_tagging_schema_validation.json` status: `PASS`
- Checked counts:
  - `sentence_enriched = 2654`
  - `page_unit_enriched = 1015`
  - `reuse_unit_enriched = 879`
- `error_count = 0`

## 14. Traceability / duplicate ID / content-boundary checks

- Required IDs present: `PASS`
- Duplicate IDs: `0` across normalized/enriched sentence/page/reuse outputs
- Source trace present: `PASS`
  - `source_tags.raz_level`, `book_id`, `book_title`, and `raw_file_path` were present for sampled and bulk-checked records
- Forbidden audio fields in derived outputs: `PASS`
  - `audio_url`, `audio_trace`, `section_audio`, `cue_start_ms`, `cue_end_ms` absent
- Generated teaching content: `PASS`
  - `generated_content = false` in source traceability
- Learner/adaptive/runtime fields: `PASS`
  - no learner-state or adaptive fields found in enriched outputs

## 15. Warning distribution

- Warning report counts from `raz_tagging_warnings.json`:
  - `unknown_theme = 734`
  - `unknown_pattern = 0` in the report file
  - `unknown_grammar = 175`
  - `section_heading_detected = 167`
  - `dialogue_or_quotation_warning = 0`
  - `human_review_required = 0` in the report file
  - `malformed_or_schema_warning = 0`
- QA warning counts recovered from enriched `qa_tags`:
  - `unknown_theme = 734`
  - `unknown_pattern = 660`
  - `unknown_grammar = 175`
  - `section_heading_detected = 167`
  - `human_review_required = 832`
- New warning family versus `Level G` baseline:
  - `unknown_pattern`
- Top books by warning count:
  - `1879 | Dr. King's Memorial = 50`
  - `2977 | Rapunzel = 49`
  - `2652 | Abigail Adams = 47`
  - `1365 | Our Five Senses = 42`
  - `2892 | The Grand Canyon = 41`
  - `3047 | The Empty Pot = 40`
  - `1148 | Nami's Gifts = 37`
  - `1821 | Statues in the Sand = 37`
  - `262 | Club Monster = 37`
  - `3567 | The Stonecutter = 37`
- Top page units by warning count:
  - `RAZ_H_1365_P015 = 9`
  - `RAZ_H_1744_P006 = 9`
  - `RAZ_H_3047_P014 = 9`
  - `RAZ_H_1879_P012 = 8`
  - `RAZ_H_2652_P013 = 8`
  - `RAZ_H_2977_P003 = 8`
  - `RAZ_H_1879_P004 = 7`
  - `RAZ_H_2134_P012 = 7`
  - `RAZ_H_2892_P006 = 7`
  - `RAZ_H_2933_P003 = 7`
- Top repeated warning text patterns in the warning report:
  - `Theme could not be confidently mapped.`
  - `No specific grammar tag was inferred by S4 rule-based tagger.`
  - `Text looks like a nonfiction heading and is not sentence authority eligible by default.`

## 16. G-vs-H warning comparison

- `total_h_enriched_records = 4548`
- `unknown_theme_rate = 734 / 4548 = 16.14%`
- `human_review_rate = 832 / 4548 = 18.29%`
- `section_heading_rate = 167 / 2654 = 6.29%`
- `unknown_grammar_rate = 175 / 2654 = 6.59%`

`Level G` baseline:

- `unknown_theme_rate = 20.58%`
- `human_review_rate = 22.06%`
- `section_heading_rate = 4.32%`
- `unknown_grammar_rate = 6.21%`

Assessment:

- `unknown_theme_rate`: better than `G`
- `human_review_rate`: better than `G`
- `unknown_grammar_rate`: slightly higher than `G` but still inside the suggested pass band
- `section_heading_rate`: slightly above the suggested `6%` comparable threshold
- `unknown_pattern`: new non-severe warning family present in `qa_tags`, absent from the flat warning report, so H is not a clean comparable copy of G

Comparison status:

- `PASS_WITH_WARNINGS_HIGHER_THAN_G`

## 17. Seed query layer boundary result

- Seed policy approved levels remained `A-F`
- Validator `discovered_queryable_levels` after build:
  - `A`
  - `B`
  - `C`
  - `D`
  - `E`
  - `F`
- `G` exposed: `false`
- `H` exposed: `false`
- Boundary result: `PASS`

## 18. S6D rebuild result

- `build_raz_level_discovery.py`: `PASS`
- `validate_raz_level_discovery.py`: `PASS`
- `total_detected_levels = 23`
- `levels_query_layer_ready = [A, B, C, D, E, F]`
- Interpretation:
  - `H` is discovery-detected and derived artifacts now exist
  - discovery rebuild did not expand query-layer readiness

## 19. S6F drift validator result

- `status = PASS_WITH_WARNINGS`
- `must_fix_count = 0`
- `candidate_only_invariant = PASS`
- `promotion_allowed_invariant = PASS`

## 20. Test result

- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`
- Result: `29 passed, 8 subtests passed in 19.37s`

## 21. Authority boundary statement

- `authority_status = candidate_only`: `PASS`
- `promotion_status = not_promoted`: `PASS`
- `promotion_allowed = false` equivalent boundary preserved through `promotion_status = not_promoted` and seed/query validators
- No evidence of automatic authority promotion, generated teaching content, or learner/adaptive state expansion

## 22. Smoke pilot status

- `PASS_WITH_WARNINGS`

## 23. Risk level

- `Medium`

Primary risks:

- `unknown_pattern = 660` appears in enriched `qa_tags` and was not present in the `Level G` baseline.
- `section_heading_rate = 6.29%` is slightly above the suggested comparable threshold.
- `raz_tagging_warnings.json` does not surface `unknown_pattern` or `human_review_required`, so the flat warning report is incomplete relative to enriched QA state.
- Direct console execution on Windows can fail without UTF-8 output configuration because of title encoding.

## 24. Decision for I / GH next task

- `RUN_H_WARNING_CLUSTER_QA`

## 25. Next recommended task

- Run targeted `Level H` warning-cluster QA focused on:
  - `unknown_pattern` distribution and whether it is a rule-coverage gap or a report-generation omission
  - `section_heading_detected` concentration in nonfiction title/heading books
  - whether warning-report generation should be aligned with enriched `qa_tags` so `human_review_required` and `unknown_pattern` are not silently underreported
