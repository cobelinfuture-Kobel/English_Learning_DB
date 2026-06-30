# RAZ-S6I_GW_SourcePlacementRecheck_AfterOperatorFix

## 1. Task Name

- `RAZ-S6I_GW_SourcePlacementRecheck_AfterOperatorFix`

## 2. Objective

- Recheck `G-W` source/raw timeline placement after the operator fixed the prior `G-I / G-H` source placement issue.
- Reconfirm that `G/H/I` no longer present as full-overlap raw placements.
- Rebuild `S6D` discovery inventory only.
- Keep all evidence `candidate_only`.

## 3. Scope Guardrails

- Do not rebuild derived artifacts.
- Do not promote content.
- Do not change tagging policy.
- Do not hardcode `G-W` as a permanent universe.

## 4. Change Impact Before Modification

- Affected files:
  - `ulga/graph/raz_level_discovery_inventory.json`
  - `ulga/reports/raz_level_discovery_summary.json`
  - `ulga/reports/raz_level_discovery_validation.json`
  - `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
  - `ulga/reports/raz_downstream_discovery_drift_validation.json`
  - `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`
  - `docs/ulga/RAZ_S6I_GW_SOURCE_PLACEMENT_RECHECK_AFTER_OPERATOR_FIX.md`
- Risk level: `Low-Medium`
- Real-trading impact: `None direct`; this task only refreshes discovery and audit artifacts.
- Restart required: `No` for static artifacts; only a downstream process that caches these JSON files would need reload.

## 5. Files Inspected

- `raz_output_jsons/Level_G` through `raz_output_jsons/Level_W`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `docs/ulga/RAZ_S6G_LEVEL_EXPANSION_GHI_READINESS_PILOT.md`
- `docs/ulga/RAZ_S6H_GW_SOURCE_ARTIFACT_INTAKE_PREFLIGHT.md`

## 6. Files Created

- `docs/ulga/RAZ_S6I_GW_SOURCE_PLACEMENT_RECHECK_AFTER_OPERATOR_FIX.md`
- `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`

## 7. Files Modified

- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 8. Commands Run

- `python ulga/builders/build_raz_level_discovery.py`
- `python ulga/validators/validate_raz_level_discovery.py`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `python ulga/validators/validate_raz_downstream_discovery_drift.py`
- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`

## 9. Raw Timeline Recheck Summary

| Level | Timeline JSON | Book IDs | Titles | Filenames | Discovery Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `G` | 92 | 92 | 92 | 92 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `H` | 84 | 84 | 84 | 84 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `I` | 88 | 88 | 88 | 88 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `J` | 83 | 83 | 83 | 83 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `K` | 83 | 83 | 83 | 83 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `L` | 67 | 67 | 67 | 67 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `M` | 73 | 73 | 73 | 73 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `N` | 74 | 74 | 74 | 74 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `O` | 77 | 77 | 77 | 77 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `P` | 75 | 75 | 74 | 75 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `Q` | 64 | 64 | 64 | 64 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `R` | 67 | 67 | 67 | 67 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `S` | 100 | 100 | 100 | 100 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `T` | 90 | 90 | 89 | 90 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `U` | 77 | 77 | 77 | 77 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `V` | 99 | 99 | 98 | 99 | `READY_FOR_REUSE_UNIT_PIPELINE` |
| `W` | 100 | 100 | 99 | 100 | `READY_FOR_REUSE_UNIT_PIPELINE` |

Notes:

- No malformed raw JSON was found under `G-W`.
- No metadata-level mismatch was found under `G-W`.
- Full per-level `book_id/title/filename` sets and the full pairwise overlap matrix were written to `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`.

## 10. G/H/I Overlap Verification

| Pair | Dimension | Intersection | A Overlap | B Overlap | Full Overlap |
| --- | --- | ---: | ---: | ---: | --- |
| `G/H` | `book_id` | 0 | 0.00% | 0.00% | `false` |
| `G/H` | `title` | 0 | 0.00% | 0.00% | `false` |
| `G/H` | `filename` | 0 | 0.00% | 0.00% | `false` |
| `H/I` | `book_id` | 0 | 0.00% | 0.00% | `false` |
| `H/I` | `title` | 0 | 0.00% | 0.00% | `false` |
| `H/I` | `filename` | 0 | 0.00% | 0.00% | `false` |
| `G/I` | `book_id` | 0 | 0.00% | 0.00% | `false` |
| `G/I` | `title` | 0 | 0.00% | 0.00% | `false` |
| `G/I` | `filename` | 0 | 0.00% | 0.00% | `false` |

Result:

- `G/H`, `H/I`, and `G/I` are no longer `100%` overlap.
- Across the full computed `G-W` matrix, there are no `book_id`, `title`, or `filename` pairs with full overlap.

## 11. S6D Rebuild Result

- `python ulga/builders/build_raz_level_discovery.py`
- `total_detected_levels = 23`
- `ready_level_count = 23`
- `levels_ready_for_reuse_unit_pipeline = A-W`
- `G-W` are detected from present artifacts through discovery, not by hardcoded universe expansion.

## 12. Validator Results

- `python ulga/validators/validate_raz_level_discovery.py`
  - `PASS`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
  - `PASS`
- `python ulga/validators/validate_raz_downstream_discovery_drift.py`
  - `PASS_WITH_WARNINGS`
  - `must_fix_count = 0`
  - `candidate_only = PASS`
  - `promotion_allowed = PASS`

Important interpretation:

- The reusable seed query layer still reports discovered queryable levels `A-F`.
- That is expected in this task because `G-W` derived enriched artifacts are still absent and this task explicitly did not rebuild derived artifacts.
- This is not evidence of a raw placement regression.

## 13. Test Result

- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`
- Result: `27 passed, 8 subtests passed in 16.83s`

## 14. Status

- `PASS_WITH_WARNINGS`

Reason:

- The operator fix is reflected in raw source placement.
- `G/H/I` no longer show full overlap.
- `S6D` rebuild and all required validators remain stable.
- Downstream boundary checks remain intact with `must_fix_count = 0`.
- Warnings remain because source PDF directories and `G-W` derived normalized/enriched artifacts are still absent by design for this task.

## 15. Real-Environment Risks

- If any later derived build consumes stale assumptions from the previous `H/I` duplication incident, focused tagging QA is still required after derived build.
- `G-W` remain raw-only today, so the seed query layer and any enriched-content consumers still cannot exercise these levels.
- `PASS_WITH_WARNINGS` from the drift validator is currently historical/legacy-warning only, not a live blocker.

## 16. Authority Boundary Statement

- No content was promoted.
- `candidate_only` remains `PASS`.
- `promotion_allowed` remains `PASS`.
- No tagging policy was changed.
- No permanent `G-W` hardcode was introduced.

## 17. Next Recommended Task

- Plan derived build readiness for `G-W`, then run normalized/enriched build plus focused tagging QA while preserving discovery-driven selection and `candidate_only` boundaries.
