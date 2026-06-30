# ULGA-S10 BLOCKED Static-Only Integrity Repair

## 1. Scope

Controlled baseline rebuild for the blocked S10 static artifact integrity state only.

- static-only repair route
- no adaptive builders
- no learner-state features
- no query-layer implementation changes

## 2. Blocked State Carryover

- `S10K1_RESULT = BLOCKED`
- `FIX_COMPLETENESS = FULLFIX`
- `ROOT_CAUSE_CATEGORY = LEGACY_BUILDER_TEST_MUTATION`
- `PROTECTED_ARTIFACTS_CLEAN = false`
- `PROTECTED_ARTIFACTS_RESTORED = false`
- `RESTORE_STATUS = PROTECTED_ARTIFACT_RESTORE_BLOCKED`
- `MUTATION_SAFE_TEST_PLAN_CREATED = true`
- `AUDIT_SCRIPT_FIXED = true`
- `DESTRUCTIVE_TESTS_EXCLUDED = true`
- `MUTATION_INTEGRITY = PASS`
- `AUDIT_RESULT = PASS_WITH_WARNINGS`
- `ADAPTIVE_DEPENDENCY_COUNT = 0`

## 3. Repair Route

- `REPAIR_ROUTE = CONTROLLED_BASELINE_REBUILD`
- Git restore was unavailable because the workspace is not a Git repository
- trusted protected-artifact baseline was unavailable from Git
- protected artifacts were intentionally rebuilt and re-hashed to establish a new controlled static baseline

## 4. Prebuild Snapshot

- snapshot file: `ulga/reports/static_only_integrity_repair_prebuild_snapshot.json`
- hash algorithm: `sha256`
- protected files snapshotted:
  - `ulga/graph/static_candidate_ranking.json`
  - `ulga/graph/static_candidate_ranking_views.json`
  - `ulga/reports/static_candidate_ranking_summary.json`
  - `ulga/reports/static_candidate_ranking_quality_audit.json`
  - `ulga/reports/static_candidate_ranking_views_summary.json`
  - `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- missing before rebuild: none

## 5. Controlled Baseline Rebuild

Builders executed:

- `python ulga\builders\build_static_candidate_ranking.py`
- `python ulga\builders\build_static_candidate_ranking_views.py`

Result:

- raw ranking rebuild completed: `11997 active / 8703 blocked`
- ranking views rebuild completed: `PASS`
- no unrelated builder was executed

## 6. Postbuild Snapshot

- snapshot file: `ulga/reports/static_only_integrity_repair_postbuild_snapshot.json`
- changed artifacts:
  - `ulga/graph/static_candidate_ranking.json`
  - `ulga/graph/static_candidate_ranking_views.json`
- unchanged artifacts:
  - `ulga/reports/static_candidate_ranking_summary.json`
  - `ulga/reports/static_candidate_ranking_quality_audit.json`
  - `ulga/reports/static_candidate_ranking_views_summary.json`
  - `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- missing after rebuild: none

## 7. Rebuilt Artifacts

- `ulga/graph/static_candidate_ranking.json`
- `ulga/graph/static_candidate_ranking_views.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `ulga/reports/static_candidate_ranking_quality_audit.json`
- `ulga/reports/static_candidate_ranking_views_summary.json`
- `ulga/reports/static_candidate_ranking_views_quality_audit.json`

## 8. Validation Results

- `python ulga\validators\validate_static_candidate_ranking.py` -> `PASS`
- `python ulga\validators\validate_static_candidate_ranking_views.py` -> `PASS`
- `python ulga\validators\validate_static_candidate_query_layer.py` -> `PASS`

## 9. Query Layer Validation

Mutation-safe commands executed:

- `python -m pytest tests\ulga\test_static_candidate_query_layer.py -q` -> `25 passed`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qa.py -q` -> `27 passed`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qafix.py -q` -> `12 passed`

Result:

- query layer contract remains valid after controlled rebuild
- no direct evidence of S10J implementation defect was found
- `ULGA-S10J1_StaticCandidateQueryLayer_ImplementationPatch` is not required

## 10. Mutation-Safe QA Audit

- audit command: `python ulga\audits\audit_static_candidate_query_layer_qa.py`
- audit result: `PASS_WITH_WARNINGS`
- mutation integrity: `PASS`
- blocking findings: none
- recommendation: `BLOCK_S10Z_CLOSEOUT`

## 11. Static-only Integrity Result

- forbidden adaptive scan result: no forbidden strings detected in rebuilt protected artifacts
- `ADAPTIVE_DEPENDENCY_COUNT = 0`
- `STATIC_ONLY_INTEGRITY = PASS`

## 12. Remaining Warnings

- derived fields remain derived, not upstream source truth
- theme-scoped view remains heuristic
- reading bridge view needs tuning
- dialogue bridge view needs tuning
- view score is policy-adjusted
- plus bands require internal band mapping
- B2 / C1 downstream view coverage remains partial
- C2 downstream view coverage is a known gap
- full-suite pytest remains excluded from mutation-safe S10K closeout evidence

## 13. Blocking Findings

- none for this controlled rebuild repair

## 14. Decision

`S10_STATIC_ONLY_INTEGRITY_REPAIR_RESULT = PASS_WITH_WARNINGS`

- controlled rebuild succeeded
- all protected artifacts exist after rebuild
- all required validators passed
- mutation-safe tests passed
- mutation-safe audit passed with warnings
- static-only scan found no adaptive leakage
- postbuild baseline was established
- S10Z closeout remains blocked until S10K is rerun against the rebuilt baseline

## 15. Recommended Next Task

`ULGA-S10K_Rerun_StaticCandidateQueryLayer_QA`
