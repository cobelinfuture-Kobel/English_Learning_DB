# RAZ-S6F Downstream Discovery Drift Validator Implementation

## 1. Task Name

- `RAZ-S6F_DownstreamDiscoveryDriftValidator_Implementation`

## 2. Preflight

- Read back S6D artifacts:
  - `ulga/graph/raz_level_discovery_inventory.json`
  - `ulga/reports/raz_level_discovery_summary.json`
  - `ulga/reports/raz_level_discovery_validation.json`
- Read back S6E artifacts:
  - `docs/ulga/RAZ_S6E_LEVEL_DISCOVERY_DOWNSTREAM_INTEGRATION_QA.md`
  - `ulga/reports/raz_level_discovery_downstream_integration_qa.json`
- Re-inspected active downstream RAZ files:
  - `tools/raz_normalized_tagging_pipeline.py`
  - `tools/raz/build_raz_level_manifest.py`
  - `tools/raz/build_raz_a_reference_sentences.py`
  - `ulga/query/raz_reusable_content_seed_query_layer.py`
  - `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
  - `ulga/validators/validate_raz_level_discovery.py`
  - `tests/test_raz_normalized_tagging_pipeline.py`
  - `tests/ulga/test_raz_level_discovery.py`
  - `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
- Re-ran targeted repository search patterns for:
  - `LEVELS =`
  - `("A", "B", "C", "D", "E", "F")`
  - `["A", "B", "C", "D", "E", "F"]`
  - `Level_A` through `Level_F`
  - `Level_*`
  - `glob("Level_*")`
  - `rglob("Level_*")`
  - `raz_output_jsons/Level_`
  - `derived/Level_`
  - `READY_FOR_REUSE_UNIT_PIPELINE`
  - `READY_FOR_SENTENCE_PIPELINE`
  - `READY_FOR_PAGE_UNIT_PIPELINE`

## 3. Files Inspected

- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `docs/ulga/RAZ_S6E_LEVEL_DISCOVERY_DOWNSTREAM_INTEGRATION_QA.md`
- `ulga/reports/raz_level_discovery_downstream_integration_qa.json`
- `ulga/builders/build_raz_level_discovery.py`
- `tools/raz_normalized_tagging_pipeline.py`
- `tools/raz/build_raz_level_manifest.py`
- `tools/raz/build_raz_a_reference_sentences.py`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `tests/ulga/test_raz_level_discovery.py`
- `tests/ulga/test_raz_reusable_content_seed_query_layer.py`

## 4. Files Created

- `ulga/policies/raz_downstream_discovery_drift_allowlist.json`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tests/ulga/test_raz_downstream_discovery_drift.py`
- `docs/ulga/RAZ_S6F_DOWNSTREAM_DISCOVERY_DRIFT_VALIDATOR_IMPLEMENTATION.md`

## 5. Files Modified

- None. This task adds a dedicated validator, allowlist, report, tests, and documentation without changing runtime RAZ execution logic.

## 6. Validator Contract

- The validator is static and offline.
- It scans RAZ-related `tools/`, `ulga/`, `tests/`, and `docs/` text files.
- It classifies matches into safe, warning, risky, and must-fix buckets.
- It writes `ulga/reports/raz_downstream_discovery_drift_validation.json`.
- It exits non-zero on `FAIL`.
- It preserves `candidate_only` and `promotion_allowed=false` boundaries by checking the canonical S6D inventory.

## 7. Classification Policy

- `SAFE_DISCOVERY_CONSUMER`
  - Active file consumes `build_raz_level_discovery`, `discover_raz_levels`, `discover_queryable_levels`, or the canonical inventory.
- `SAFE_TEST_FIXTURE`
  - Test fixture intentionally creates `Level_*` paths or fixed A-F examples.
- `SAFE_HISTORICAL_DOC`
  - Historical docs may mention `Level_*`, `A-F`, or path layouts.
- `SAFE_SINGLE_LEVEL_UTILITY`
  - Explicit one-level utility where the level is user-supplied and the file does not claim readiness authority.
- `SAFE_PATH_NAMING_PATTERN`
  - File constructs a `Level_{level}` path after discovery or explicit input.
- `WARNING_LEGACY_REFERENCE`
  - Historical or legacy active file still contains a narrow static level reference and must not be reused as readiness authority.
- `RISKY_DIRECT_LEVEL_SCAN`
  - Active code uses `glob("Level_*")`, `rglob("Level_*")`, or equivalent wildcard readiness discovery.
- `RISKY_FIXED_LEVEL_UNIVERSE`
  - Active code hardcodes `A-F` as the full RAZ readiness universe.
- `RISKY_INDEPENDENT_READINESS_LOGIC`
  - Active code loses required S6D consumption or sets promotion-related flags true.
- `FAIL_MUST_USE_S6D_DISCOVERY`
  - Normalized must-fix output for every active drift finding.

## 8. Allowed Cases

- Test fixtures that create `Level_A-F` paths.
- Historical docs that describe `Level_A-F`.
- `tools/raz/build_raz_level_manifest.py` as an explicit `--level` utility.
- `tools/raz/build_raz_a_reference_sentences.py` as a legacy A-only reference builder with warning-only treatment.
- Path naming that occurs after discovery or explicit user-specified level selection.

## 9. Fail Cases

- Active builder/query/validator code uses direct `Level_*` wildcard scans to determine readiness.
- Active code hardcodes `("A", "B", "C", "D", "E", "F")` or equivalent as the queryable readiness universe.
- Known downstream discovery consumers stop referencing S6D discovery helpers.
- Active code sets `promotion_allowed=true` or `authority_promotion_allowed=true`.
- S6D inventory disappears or loses `candidate_only` / `promotion_allowed=false` invariants.

## 10. JSON Report Schema

- `task`
- `status`
- `s6d_inventory_exists`
- `s6e_report_exists`
- `files_scanned`
- `safe_discovery_consumers`
- `safe_test_fixtures`
- `safe_historical_docs`
- `safe_single_level_utilities`
- `safe_path_naming_patterns`
- `warnings`
- `risky_direct_level_scans`
- `risky_fixed_level_universes`
- `risky_independent_readiness_logic`
- `must_fix_findings`
- `candidate_only_invariant`
- `promotion_allowed_invariant`
- `summary`
- `next_recommended_task`

## 11. Validator Results

- Current expected steady state: `PASS_WITH_WARNINGS`
- Expected warnings:
  - legacy A-only builder remains present
  - historical docs still mention `Level_A-F`
- Expected must-fix findings: `0`

## 12. Test Results

- Added dedicated regression tests for:
  - safe current scan
  - fail on direct wildcard level scan
  - fail on fixed A-F readiness universe
  - pass on test fixtures
  - pass on historical docs
  - pass on explicit single-level utility
  - fail on `promotion_allowed=true`
  - report schema completeness

## 13. Risk Level

- `Low`

## 14. Residual Warnings

- Historical docs still contain `Level_A-F` wording.
- `tools/raz/build_raz_a_reference_sentences.py` remains legacy A-only code and should never become readiness authority.
- The validator is intentionally narrow. If future drift uses a brand-new bypass pattern, the validator may need one more explicit rule.

## 15. Authority Boundary Statement

- This task does not promote any RAZ content into Reading, Writing, Dialogue, Exercise, or Assessment Authority.
- The validator enforces `candidate_only` and `promotion_allowed=false` boundaries through the canonical S6D inventory check.

## 16. Next Recommended Task

- Wire this validator into the standard RAZ AUX-S6 QA run so every future downstream module must pass the same discovery-drift gate before merge.
