# RAZ-S6K_G_DerivedBuildSmokePilot

## 1. Task Name

- `RAZ-S6K_G_DerivedBuildSmokePilot`

## 2. Objective

- Run the first `Level G`-only derived build smoke pilot.
- Convert `Level G` raw candidate artifacts into normalized and enriched derived artifacts.
- Preserve `candidate_only` authority boundaries.
- Keep reusable seed query exposure at `A-F` only.

## 3. Scope Guardrails

- Process only `Level G`.
- Do not process `H-W`.
- Do not run a full `G-W` build.
- Do not expose `G` in the seed query layer.
- Do not promote content.
- Do not implement CEFR or adaptive selection.

## 4. Change Impact Before Modification

- Affected files:
  - `tools/raz_normalized_tagging_pipeline.py`
  - `ulga/builders/build_raz_level_discovery.py`
  - `ulga/policies/raz_seed_query_layer_policy.json`
  - `tests/ulga/test_raz_level_discovery.py`
  - `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
  - `raz_output_jsons/derived/Level_G/*`
  - `raz_output_jsons/derived/reports/*`
  - `ulga/graph/raz_level_discovery_inventory.json`
  - `ulga/reports/raz_level_discovery_summary.json`
  - `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
  - `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
  - `ulga/reports/raz_downstream_discovery_drift_validation.json`
  - `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
  - `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- Risk level: `Medium`
- Real-trading impact: `None direct`; static corpus, discovery, query-layer policy, and report artifacts only.
- Restart required: `No` for static artifacts; only external caches would need reload.

## 5. Preflight

- Inspected `S6J` readiness plan and confirmed `G` was the recommended first pilot.
- Inspected `S6I` source placement recheck and confirmed `G/H/I` raw overlap issue was already cleared.
- Inspected `S6D` discovery artifacts and confirmed `Level G` raw baseline was discovery-detected.
- Inspected `S6F` drift validator and confirmed baseline `must_fix_count = 0`.
- Inspected seed query layer artifacts and active builder/query code paths.
- Checked `raz_output_jsons/derived/Level_G` before build and confirmed no pre-existing `Level G` normalized/enriched outputs were present.

## 6. Files Inspected

- `docs/ulga/RAZ_S6J_GW_DERIVED_BUILD_READINESS_PLAN.md`
- `ulga/reports/raz_gw_derived_build_readiness_plan.json`
- `docs/ulga/RAZ_S6I_GW_SOURCE_PLACEMENT_RECHECK_AFTER_OPERATOR_FIX.md`
- `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `tools/raz_normalized_tagging_pipeline.py`
- `raz_output_jsons/Level_G`
- `raz_output_jsons/derived/Level_G`

## 7. Files Created

- `ulga/policies/raz_seed_query_layer_policy.json`
- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`

## 8. Files Modified

- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/builders/build_raz_level_discovery.py`
- `tests/ulga/test_raz_level_discovery.py`
- `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 9. Build Command Used

- `python tools/raz_normalized_tagging_pipeline.py --levels G`

Implementation note:

- A minimal import-path fix was required so the expected direct command works without manual `PYTHONPATH` injection.

## 10. Pre-build Level G Baseline

- `timeline_json_count = 92`
- `sentence_candidate_count = 2336`
- `page_unit_count = 930`
- `reuse_unit_count = 801`
- `normalized_sentence_existing = 0`
- `normalized_page_unit_existing = 0`
- `normalized_reuse_unit_existing = 0`
- `enriched_sentence_existing = 0`
- `enriched_page_unit_existing = 0`
- `enriched_reuse_unit_existing = 0`

## 11. Generated Normalized / Enriched Artifacts

- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`

## 12. Post-build Level G Counts

| Family | Raw | Normalized | Enriched | Result |
| --- | ---: | ---: | ---: | --- |
| Sentence | 2336 | 2336 | 2336 | `PASS` |
| Page Unit | 930 | 930 | 930 | `PASS` |
| Reuse Unit | 801 | 801 | 801 | `PASS` |

## 13. Count Parity Result

- `sentence = PASS`
- `page_unit = PASS`
- `reuse_unit = PASS`
- No data loss, duplication, or untraceable count drift was detected.

## 14. Schema Validation Result

- Pipeline schema validation report: `PASS`
- `error_count = 0`
- JSON / JSONL parse checks passed.
- Duplicate ID checks passed.
- Traceability checks passed.
- Forbidden audio field check passed.

## 15. Warning Distribution

- `unknown_theme = 837`
- `unknown_pattern = 0`
- `unknown_grammar = 145`
- `section_heading_detected = 101`
- `dialogue / quotation warning count = 0`
- `human_review_required = 897`
- `malformed / schema warning count = 0`
- `new warning types = []`

Interpretation:

- Warning output is present, well-formed, and uses known warning families only.
- Counts are high enough to justify human review, but they do not indicate record loss or schema breakage.

## 16. Seed Query Layer Boundary Result

- Initial smoke run exposed a real integration bug: `Level G` enriched artifacts were automatically picked up by seed query discovery.
- Minimal fix applied:
  - Added a seed query policy gate file: `ulga/policies/raz_seed_query_layer_policy.json`
  - Updated discovery so `query_layer_ready` requires both enriched artifacts and explicit policy approval.
- Final seed query validator result:
  - `discovered_queryable_levels = A, B, C, D, E, F`
  - `G exposed = false`
  - Boundary status = `PASS`

## 17. S6D Rebuild Result

- `python ulga/builders/build_raz_level_discovery.py`
- `total_detected_levels = 23`
- `levels_ready_for_reuse_unit_pipeline = A-W`
- `Level G` now shows normalized/enriched artifact counts present in discovery inventory.
- `Level G query_layer_approved = false`
- `Level G query_layer_ready = false`

## 18. S6F Drift Validator Result

- `status = PASS_WITH_WARNINGS`
- `must_fix_count = 0`
- `candidate_only_invariant = PASS`
- `promotion_allowed_invariant = PASS`

## 19. Test Result

- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`
- Result: `29 passed, 8 subtests passed in 19.50s`

## 20. Authority Boundary Statement

- All generated `Level G` outputs remain `candidate_only`.
- `promotion_allowed` remains blocked.
- No promotion-like state was introduced.
- `Level G` is derived-ready but not seed-query-ready.

## 21. Smoke Pilot Status

- `PASS_WITH_WARNINGS`

Reason:

- `Level G` only was processed.
- All six derived outputs exist.
- Count parity passed for sentence, page unit, and reuse unit.
- Schema, traceability, duplicate-ID, and forbidden-audio checks passed.
- `candidate_only` and promotion guardrails passed.
- Seed query layer remained `A-F` only after the minimal policy gate fix.
- `S6D` rebuild passed.
- `S6F must_fix_count = 0`.
- pytest pack passed.
- Warning volume remains reviewable but non-trivial.

## 22. Real-Environment Risks

- `unknown_theme` and `human_review_required` counts are materially higher than zero and should be reviewed before broadening the pilot.
- Without the added policy gate, enriched artifact presence would have silently expanded the seed query layer to `G`.
- Direct script invocation was previously brittle because `tools/raz_normalized_tagging_pipeline.py` depended on implicit module path setup.
- Source PDF directories for `Level G` remain absent, so source-side reconciliation still depends on existing raw evidence only.

## 23. Next Recommended Task

- `H` may enter the second smoke pilot if:
  - the seed query policy gate remains unchanged,
  - `candidate_only` / promotion guardrails remain unchanged,
  - and the `Level G` warning clusters are accepted as review workload rather than treated as build-integrity failures.
