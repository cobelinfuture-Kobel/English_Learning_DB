# ULGA-S10K1 Static Candidate Query Layer QA Fix

## 1. Scope

Full fix for the S10K QA boundary only.

- no query-layer feature changes
- no ranking/view rebuild
- no adaptive behavior
- no upstream builder or validator modification

## 2. S10K Failure Carryover

- S10K blocked on mutation integrity
- root cause pointed to legacy ranking/view tests that rebuild artifacts
- S10J query layer was not proven to mutate protected artifacts

## 3. Root Cause

`LEGACY_BUILDER_TEST_MUTATION`

Confirmed cause:

- `tests/ulga/test_static_candidate_ranking.py` runs `build_static_candidate_ranking.py`
- `tests/ulga/test_static_candidate_ranking_views.py` runs `build_static_candidate_ranking_views.py`
- those tests are therefore not mutation-safe evidence for S10K closeout

## 4. Protected Artifact Restoration / Cleanliness

- preflight confirmed this workspace is not a Git repository
- `git status --short` failed with `not a git repository`
- `git restore` is therefore unavailable
- previously mutated protected artifacts cannot be legally restored through Git in this workspace

Status:

- `restore_status = PROTECTED_ARTIFACT_RESTORE_BLOCKED`

## 5. Safe vs Destructive Test Boundary

Created:

- `ulga/reports/static_candidate_query_layer_safe_test_plan.json`

Classification:

- mutation-safe:
  - `tests/ulga/test_static_candidate_query_layer.py`
  - `tests/ulga/test_static_candidate_query_layer_qa.py`
  - `tests/ulga/test_static_candidate_query_layer_qafix.py`
- destructive rebuild:
  - `tests/ulga/test_static_candidate_ranking.py`
  - `tests/ulga/test_static_candidate_ranking_views.py`
- unknown side effect:
  - none

## 6. Files Created

- `tests/ulga/test_static_candidate_query_layer_qafix.py`
- `docs/ulga/ULGA_S10K1_STATIC_CANDIDATE_QUERY_LAYER_QAFIX.md`
- `ulga/reports/static_candidate_query_layer_safe_test_plan.json`
- `ulga/reports/static_candidate_query_layer_qafix_mutation_snapshot.json`
- `ulga/reports/static_candidate_query_layer_qafix_report.json`

## 7. Files Modified

- `ulga/audits/audit_static_candidate_query_layer_qa.py`
- `tests/ulga/test_static_candidate_query_layer_qa.py`
- `ulga/reports/static_candidate_query_layer_qa_audit.json`

## 8. Audit Script Fix

The audit script now:

- snapshots protected files before and after mutation-safe QA commands
- runs validator only
- runs mutation-safe query-layer tests only
- runs mutation-safe QA tests only
- runs mutation-safe QAFix tests only
- excludes builders, legacy ranking/view tests, and full-suite pytest from closeout evidence

## 9. QA Test Fix

`tests/ulga/test_static_candidate_query_layer_qafix.py` verifies:

- safe test plan exists
- destructive tests are excluded
- audit script does not invoke builders
- audit script does not invoke legacy ranking/view tests
- mutation snapshot exists
- full-fix report exists

## 10. Mutation Snapshot

- `ulga/reports/static_candidate_query_layer_qafix_mutation_snapshot.json`
- hash algorithm: `sha256`
- compares protected files before and after safe commands

## 11. Commands Executed

- `git status --short`
- `git diff -- ulga/graph/static_candidate_ranking.json ulga/graph/static_candidate_ranking_views.json ulga/reports/static_candidate_ranking_views_summary.json`
- `python ulga\validators\validate_static_candidate_query_layer.py`
- `python -m pytest tests\ulga\test_static_candidate_query_layer.py -q`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qa.py -q`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qafix.py -q`
- `python ulga\audits\audit_static_candidate_query_layer_qa.py`

## 12. Test Results

- validator: PASS
- targeted query tests: PASS
- S10K QA tests: PASS
- S10K1 QAFix tests: PASS

## 13. Audit Result

- `ulga/reports/static_candidate_query_layer_qa_audit.json`
- audit status: `PASS_WITH_WARNINGS`
- mutation integrity: `PASS`
- root cause category: `LEGACY_BUILDER_TEST_MUTATION`
- recommendation: `BLOCK_S10Z_CLOSEOUT`

## 14. Remaining Warnings

- derived fields remain derived
- theme / reading / dialogue warnings remain
- plus-band mapping remains required
- B2 / C1 remain partial support
- C2 remains known gap
- full-suite pytest remains excluded from mutation-safe closeout evidence
- protected artifact restoration is blocked without Git tracking

## 15. Blocking Findings

- `PROTECTED_ARTIFACT_RESTORE_BLOCKED`

## 16. Decision

`S10K1_RESULT = BLOCKED`

`FIX_COMPLETENESS = FULLFIX`

`MUTATION_INTEGRITY = PASS`

`PROTECTED_ARTIFACTS_CLEAN = false`

`PROTECTED_ARTIFACTS_RESTORED = false`

## 17. Recommended Next Task

`ULGA-S10_BLOCKED_StaticOnlyIntegrityRepair`
