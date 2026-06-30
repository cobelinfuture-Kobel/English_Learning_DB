# ULGA-S10K Rerun Static Candidate Query Layer QA

## 1. Scope

Full S10K QA gate rerun only.

- no rebuild
- no legacy destructive tests
- no query-layer implementation patch
- no builder or validator patch

## 2. Baseline Repair Carryover

- baseline source: `ULGA-S10_BLOCKED_StaticOnlyIntegrityRepair`
- repair route: `CONTROLLED_BASELINE_REBUILD`
- postbuild baseline established: `true`
- blocking findings count from repair: `0`
- repair recommended next task: `ULGA-S10K_Rerun_StaticCandidateQueryLayer_QA`

## 3. Files Inspected

- `docs/ulga/ULGA_S10_BLOCKED_STATIC_ONLY_INTEGRITY_REPAIR.md`
- `ulga/reports/static_only_integrity_repair_report.json`
- `ulga/reports/static_only_integrity_repair_postbuild_snapshot.json`
- `docs/ulga/ULGA_S10K1_STATIC_CANDIDATE_QUERY_LAYER_QAFIX.md`
- `ulga/reports/static_candidate_query_layer_safe_test_plan.json`
- `ulga/reports/static_candidate_query_layer_qafix_report.json`
- `ulga/reports/static_candidate_query_layer_qafix_mutation_snapshot.json`
- `docs/ulga/ULGA_S10K_STATIC_CANDIDATE_QUERY_LAYER_QA.md`
- `docs/ulga/ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10I_STATIC_CANDIDATE_QUERY_LAYER_DESIGN_SCAN.md`
- `ulga/query/static_candidate_query_layer.py`
- `ulga/validators/validate_static_candidate_query_layer.py`
- `ulga/audits/audit_static_candidate_query_layer_qa.py`
- `tests/ulga/test_static_candidate_query_layer.py`
- `tests/ulga/test_static_candidate_query_layer_qa.py`
- `tests/ulga/test_static_candidate_query_layer_qafix.py`
- protected static artifacts and reports listed in the S10K rerun task

## 4. Files Created

- `ulga/reports/static_candidate_query_layer_qa_rerun_pre_snapshot.json`
- `ulga/reports/static_candidate_query_layer_qa_rerun_post_snapshot.json`
- `ulga/reports/static_candidate_query_layer_qa_rerun_report.json`
- `docs/ulga/ULGA_S10K_RERUN_STATIC_CANDIDATE_QUERY_LAYER_QA.md`

## 5. Files Modified

- `ulga/reports/static_candidate_query_layer_validation.json`
- `ulga/reports/static_candidate_query_layer_qa_audit.json`

## 6. Postbuild Baseline Confirmation

- `static_only_integrity_repair_report.json` exists
- `static_only_integrity_repair_postbuild_snapshot.json` exists
- `repair_route = CONTROLLED_BASELINE_REBUILD`
- postbuild baseline confirmed: `true`
- blocking findings count: `0`
- recommended next task matches rerun task

## 7. Pre-Rerun Snapshot

- snapshot file: `ulga/reports/static_candidate_query_layer_qa_rerun_pre_snapshot.json`
- hash algorithm: `sha256`
- protected files snapshotted: `6`

## 8. Validator Results

- `python ulga\validators\validate_static_candidate_query_layer.py` -> `PASS`

## 9. Mutation-Safe Test Results

- `python -m pytest tests\ulga\test_static_candidate_query_layer.py -q` -> `25 passed`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qa.py -q` -> `27 passed`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qafix.py -q` -> `12 passed`

## 10. Mutation-Safe Audit Result

- audit command: `python ulga\audits\audit_static_candidate_query_layer_qa.py`
- audit result: `PASS_WITH_WARNINGS`
- audit script was rerun through the fixed mutation-safe path

## 11. Post-Rerun Snapshot

- snapshot file: `ulga/reports/static_candidate_query_layer_qa_rerun_post_snapshot.json`
- mutated protected files: `[]`

## 12. Mutation Integrity

- `MUTATION_INTEGRITY = PASS`
- protected artifacts remained unchanged across the rerun

## 13. Static-only Integrity

- forbidden adaptive scan result: no matches
- `ADAPTIVE_DEPENDENCY_COUNT = 0`
- `STATIC_ONLY_INTEGRITY = PASS`

## 14. Query Layer QA Gate Result

- `query_function_count = 9`
- `required_query_functions_missing = []`
- `success_response_schema = PASS`
- `error_response_schema = PASS`
- `candidate_schema = PASS`
- `explanation_schema = PASS`
- `warning_registry_complete = true`
- `multi_level_coverage_present = true`
- `derived_fields_valid = true`
- `score_policy_integrity = PASS`
- `static_only_guardrails = PASS`
- `raw_ranking_curriculum_use_blocked = true`
- downstream readiness remains:
  - `Reading Authority = READY_WITH_WARNINGS`
  - `Dialogue Authority = READY_WITH_WARNINGS`
  - `Worksheet / Exercise Builder = READY_WITH_WARNINGS`
  - `Assessment Authority = NOT_READY`
  - `Future Adaptive Planner = FORBIDDEN_FOR_NOW`

## 15. Remaining Warnings

- derived fields remain derived, not upstream source truth
- `theme_scoped_view` remains heuristic
- `reading_bridge_view` needs tuning
- `dialogue_bridge_view` needs tuning
- `view_score` is policy-adjusted
- plus bands require internal band mapping
- `B2` / `C1` downstream coverage remains partial
- `C2` downstream coverage is a known gap
- full-suite `pytest` remains excluded from mutation-safe S10K evidence

## 16. Blocking Findings

- none

## 17. Decision

`S10K_RERUN_RESULT = PASS_WITH_WARNINGS`

All mutation-safe validator, tests, and audit commands passed against the controlled rebuild baseline. Protected artifacts did not change during the rerun, static-only integrity remained intact, and the remaining warnings are known non-blocking carryover items.

## 18. Recommended Next Task

`ULGA-S10Z_StaticCandidateQueryLayer_Closeout`
