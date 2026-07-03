# RAZ-AW-V1 Real Data Smoke Validation

## 1. Task

`RAZ-AW-V1_RealDataSmokeValidation`

This task adds a post-closeout smoke validator for Reading System V1 using a real S11 generated intake query index when it is available locally.

## 2. Scope

This task validates the real-data path:

```text
S11 generated intake query index
→ S17 candidate item builder
→ S18 item validator
→ S19 practice package builder
```

It does not implement V2-V5, new question types, learner-facing production delivery, Reading Authority promotion, runtime integration, dashboard integration, API integration, or adaptive sequencing.

## 3. Files Created

```text
ulga/audits/audit_reading_practice_v1_real_data_smoke.py
tests/ulga/test_reading_practice_v1_real_data_smoke.py
docs/ulga/RAZ_AW_V1_REAL_DATA_SMOKE_VALIDATION.md
```

## 4. Generated Artifact Policy

No generated JSON artifacts are committed by this task.

The smoke validator reads the following local generated artifacts when available:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
ulga/reports/raz_reading_authority_intake_query_index_summary.json
```

Optional smoke report output is also generated-only:

```text
ulga/reports/reading_practice_v1_real_data_smoke_report.json
```

Do not commit these generated artifacts unless a later explicit artifact-persistence task approves it.

## 5. Runtime Impact

None.

This task does not modify runtime, app code, dashboards, schedulers, learner state, APIs, or student-facing output.

## 6. Promotion Impact

None.

The smoke validator checks that generated items and packages remain:

```text
candidate_only
not_promoted
not learner_facing
```

## 7. Smoke Validator Behavior

If the S11 generated index or summary is absent, the smoke validator returns:

```text
status = BLOCKED_INPUT_ABSENT
decision = REAL_DATA_SMOKE_NOT_RUN
```

This is not a code failure. It means the real generated S11 input artifacts have not been restored locally.

If the S11 generated index and summary are present, the smoke validator requires:

```text
generated_items > 0
validated_items > 0
package_items > 0
S18 validation does not FAIL
S19 package does not FAIL
promoted_count = 0
learner_facing_count = 0
```

If real data produces zero Reading items, the smoke validator returns:

```text
status = FAIL
error = real_data_generated_items_zero
```

## 8. Local Execution Commands

First restore S11 generated artifacts locally:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
ulga/reports/raz_reading_authority_intake_query_index_summary.json
```

Run real-data smoke:

```bash
python ulga/audits/audit_reading_practice_v1_real_data_smoke.py
```

Run with full JSON output:

```bash
python ulga/audits/audit_reading_practice_v1_real_data_smoke.py --json
```

Write a local smoke report:

```bash
python ulga/audits/audit_reading_practice_v1_real_data_smoke.py --write-report
```

Run tests:

```bash
pytest tests/ulga/test_reading_practice_v1_real_data_smoke.py
```

## 9. Expected Outcomes

Without restored S11 generated input:

```text
Reading System V1 real-data smoke: BLOCKED_INPUT_ABSENT
Decision: REAL_DATA_SMOKE_NOT_RUN
Generated items: 0
Package items: 0
```

With restored real S11 generated input and successful pipeline:

```text
Reading System V1 real-data smoke: PASS
Decision: REAL_DATA_SMOKE_PASS
Generated items: > 0
Package items: > 0
```

## 10. Closeout Status

```text
Task ID: RAZ-AW-V1_RealDataSmokeValidation
Task name: Reading System V1 Real Data Smoke Validation
Reading system target: Reading System V1 post-closeout verification
Input source: local S11 generated intake query index and summary
Output artifact: smoke audit, tests, smoke validation report doc
Progress contribution: Verifies whether the completed V1 candidate pipeline can produce, validate, and package Reading practice items from real generated S11 data
Blocking issue: Requires local S11 generated artifacts for real-data PASS
Generated artifact policy: No generated artifacts committed
Runtime impact: None
Promotion impact: None
Closeout status: IMPLEMENTED_ON_MAIN_PENDING_LOCAL_CONFIRMATION
```
