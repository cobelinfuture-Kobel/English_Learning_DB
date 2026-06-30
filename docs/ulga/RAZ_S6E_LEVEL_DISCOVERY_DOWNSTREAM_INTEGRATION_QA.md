# RAZ-S6E_LevelDiscoveryDownstreamIntegration_QA

## 1. Task Name

- `RAZ-S6E_LevelDiscoveryDownstreamIntegration_QA`

## 2. Preflight

- Read back S6D artifacts:
  - `ulga/graph/raz_level_discovery_inventory.json`
  - `ulga/reports/raz_level_discovery_summary.json`
  - `ulga/reports/raz_level_discovery_validation.json`
- Inspected active downstream code paths:
  - `tools/raz_normalized_tagging_pipeline.py`
  - `tools/raz/build_raz_level_manifest.py`
  - `tools/raz/build_raz_a_reference_sentences.py`
  - `ulga/query/raz_reusable_content_seed_query_layer.py`
  - `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
  - `ulga/validators/validate_raz_level_discovery.py`
  - `tests/test_raz_normalized_tagging_pipeline.py`
  - `tests/ulga/test_raz_level_discovery.py`
  - `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
- Repository search was executed for:
  - `LEVELS =`
  - `("A", "B", "C", "D", "E", "F")`
  - `Level_A` through `Level_F`
  - `raz_output_jsons/Level_`
  - `derived/Level_`

## 3. Files Inspected

- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `tools/raz/build_raz_level_manifest.py`
- `tools/raz/build_raz_a_reference_sentences.py`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `tests/ulga/test_raz_level_discovery.py`
- `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
- `docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md`
- `docs/raz/RAZ_S6B_REUSABLE_CONTENT_SEED_QUERY_LAYER_QA.md`
- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`

## 4. Files Modified

- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`

## 5. Files Created

- `docs/ulga/RAZ_S6E_LEVEL_DISCOVERY_DOWNSTREAM_INTEGRATION_QA.md`
- `ulga/reports/raz_level_discovery_downstream_integration_qa.json`

## 6. S6D Artifact Readback

- inventory exists: `true`
- summary exists: `true`
- validation exists: `true`
- detected levels: `A B C D E F`
- current S6D readiness:
  - sentence pipeline: `A-F`
  - page-unit pipeline: `A-F`
  - reuse-unit pipeline: `A-F`
- inventory still keeps:
  - `authority_status = candidate_only`
  - `promotion_allowed = false`

## 7. Downstream Integration Matrix

| module_path | module_type | reads_discovery_inventory | performs_own_level_scan | has_hardcoded_level_universe | hardcoding_status | candidate_only_safe | recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ulga/query/raz_reusable_content_seed_query_layer.py` | query_layer | true | false | false | none | true | keep as discovery-driven source consumer |
| `ulga/validators/validate_raz_reusable_content_seed_query_layer.py` | validator | true | false | false | none | true | keep validator aligned with discovered queryable levels |
| `ulga/validators/validate_raz_level_discovery.py` | validator | true | false | false | none | true | keep as authority-boundary and discovery invariant validator |
| `tools/raz_normalized_tagging_pipeline.py` | builder | true | false | false | none | true | fixed in S6E so default selection now follows discovery |
| `tools/raz/build_raz_level_manifest.py` | utility_builder | false | false | false | acceptable_path_pattern | true | keep as explicit single-level utility, not readiness authority |
| `tools/raz/build_raz_a_reference_sentences.py` | historical_builder | false | false | true | acceptable_static_level_reference | true | keep marked historical / A-only reference utility |
| `tests/ulga/test_raz_level_discovery.py` | test | true | false | false | acceptable_fixture | true | keep fixture-scoped |
| `tests/ulga/test_raz_reusable_content_seed_query_layer.py` | test | false | false | true | acceptable_fixture | true | keep fixture-scoped |
| `tests/test_raz_normalized_tagging_pipeline.py` | test | true | false | true | acceptable_fixture | true | added regression for discovery-driven default level selection |

## 8. Hardcoded Level Assumption Audit

Classified as acceptable historical documentation:

- `docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md`
  - contains `Load all Level_A-F...`
- `docs/raz/RAZ_S6B_REUSABLE_CONTENT_SEED_QUERY_LAYER_QA.md`
  - contains `derived Level_A-F ...`
- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`
  - explicitly marked temporary smoke test across `A/B/C/D/E/F`

Classified as acceptable static utility or fixture:

- `tools/raz/build_raz_level_manifest.py`
  - explicit `--level` utility, no readiness claim
- `tools/raz/build_raz_a_reference_sentences.py`
  - historical A-only extraction builder, not active S6 readiness logic
- `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
  - fixture references by design
- `tests/test_raz_normalized_tagging_pipeline.py`
  - fixture uses `Level_F`

Classified as active readiness logic and fixed in this task:

- `tools/raz_normalized_tagging_pipeline.py`
  - pre-S6E default path scanned `Level_*` directly
  - post-S6E default selection now resolves levels via S6D discovery and only includes levels with `can_build_sentence_candidates = true`

No remaining must-fix downstream readiness duplication was found in active S6 query / validator paths.

## 9. Query Layer Verification

- `ulga/query/raz_reusable_content_seed_query_layer.py` imports `build_raz_level_discovery`
- enriched file loading now iterates over `discover_queryable_levels(...)`
- seed coverage matrix falls back to discovered queryable levels when needed
- validator also checks discovered queryable levels instead of fixed `A-F`
- query-layer guardrails remain:
  - `static_only = true`
  - `authority_promotion_allowed = false`
  - `generated_content_returned = false`

## 10. Validator Verification

- `validate_raz_level_discovery.py`
  - validates summary/inventory consistency
  - validates `candidate_only`
  - validates `promotion_allowed = false`
  - rejects `C/D/E/F`-only hardcoding in the new discovery module
- `validate_raz_reusable_content_seed_query_layer.py`
  - validates discovered queryable levels have coverage
  - validates seed cards remain `candidate_only`
  - validates `authority_promotion_allowed = false`

## 11. Test Results

Executed:

- `python ulga/builders/build_raz_level_discovery.py`
- `python ulga/validators/validate_raz_level_discovery.py`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `python -m pytest tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`

Observed:

- discovery rebuild: `PASS`
- discovery validator: `PASS`
- reusable seed validator: `PASS`
- pytest: `19 passed, 8 subtests passed`

## 12. Findings

- S6D artifacts are present and internally consistent.
- Active S6 query and validator code paths already consume discovery.
- One active downstream integration issue existed in `tools/raz_normalized_tagging_pipeline.py` because default level selection still scanned folders directly.
- That issue was fixed with a minimal change so default tagging-pipeline level selection now routes through S6D discovery.
- Remaining A-only or `A-F` references are historical docs, explicit utilities, or tests rather than active readiness authority.

## 13. Risk Level

- `Medium-Low`

Residual risks:

- historical docs still mention `Level_A-F`; they are not executable logic but can mislead future maintainers
- `tools/raz/build_raz_a_reference_sentences.py` remains intentionally A-only and should not be reused as a readiness authority
- if future modules begin scanning `Level_*` directly again, a dedicated downstream integration validator would catch drift earlier than docs review alone

## 14. Authority Boundary Statement

This task did not promote any RAZ content into Reading, Writing, Dialogue, Exercise, or Assessment Authority.

All checked downstream paths continue to preserve candidate-only handling, and promotion remains blocked through `promotion_allowed = false` / `authority_promotion_allowed = false`.

## 15. Next Recommended Task

- Add a dedicated downstream integration validator or audit script that asserts active RAZ AUX-S6 modules consume S6D discovery rather than reintroducing direct `Level_*` readiness scans.
