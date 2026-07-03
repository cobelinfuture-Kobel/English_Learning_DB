# RAZ-AW-S19 Reading Practice Output Package Implementation

## 1. Task

`RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation`

This task implements the Reading System V1 candidate practice package builder.

S19 packages S17-generated and S18-validatable Reading candidate items into a candidate package while preserving source traceability, evidence, answer models, validator gate results, and candidate-only lifecycle boundaries.

## 2. Scope

S19 implements package construction only.

It does not implement learner-facing production delivery, runtime integration, dashboard integration, app integration, adaptive sequencing, or Reading Authority promotion.

## 3. Files Created

```text
ulga/builders/build_reading_practice_package.py
tests/ulga/test_reading_practice_package_builder.py
docs/ulga/RAZ_AW_S19_READING_PRACTICE_OUTPUT_PACKAGE_IMPLEMENTATION.md
```

## 4. Generated Artifact Policy

The package builder can write generated artifacts when run locally:

```text
ulga/graph/reading_practice_package.json
ulga/reports/reading_practice_package_summary.json
```

These generated artifacts are not committed by this task.

## 5. Runtime Impact

None.

This task does not modify runtime, app code, dashboards, schedulers, learner state, APIs, or student-facing output.

## 6. Promotion Impact

None.

The package remains:

```text
candidate_only
not_promoted
not learner_facing
```

S19 does not promote candidate Reading items or candidate packages.

## 7. Builder Input

Default input:

```text
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
```

Programmatic input:

```python
build_package(items_payload=None, items_summary=None, max_items=20, write_outputs=True)
```

## 8. Builder Output

Default output:

```text
ulga/graph/reading_practice_package.json
ulga/reports/reading_practice_package_summary.json
```

Top-level output schema:

```text
READING_PRACTICE_PACKAGE_CANDIDATE_V1
```

Summary schema:

```text
READING_PRACTICE_PACKAGE_SUMMARY_V1
```

## 9. Validation Gate

S19 calls the S18 validator before packaging.

If the validation gate returns `FAIL`, S19 creates an empty candidate package and records:

```text
validation_gate_failed_no_items_packaged
```

If there are no items, S19 emits:

```text
PASS_WITH_WARNINGS
no_items_packaged
```

This allows the pipeline to remain deterministic when generated S17 artifacts are absent from the repository.

## 10. Package Contents

Each package item preserves:

```text
item_id
question_type
skill
level
source
evidence
prompt
answer_model
tags
validation
lifecycle
```

The package also emits an internal answer key copied from each item's `answer_model`.

## 11. Boundary Rules

S19 only packages items that remain:

```text
candidate_only
not_promoted
not learner_facing
source.generated_content = false
```

S19 rejects packaging for items missing prompt, evidence, source traceability, answer model, or approved question type.

## 12. Local Execution Commands

Run package builder:

```bash
python ulga/builders/build_reading_practice_package.py
```

Run without writing generated artifacts:

```bash
python ulga/builders/build_reading_practice_package.py --no-write
```

Run tests:

```bash
pytest tests/ulga/test_reading_practice_package_builder.py
```

Recommended local S17-S19 sequence:

```bash
pytest tests/ulga/test_reading_candidate_item_builder.py
pytest tests/ulga/test_reading_practice_items_validator.py
pytest tests/ulga/test_reading_practice_package_builder.py
```

If local generated artifacts are created during manual checks, remove them before commit unless explicitly approved:

```bash
git clean -fd -- ulga/graph/reading_practice_items.json ulga/reports/reading_practice_items_summary.json ulga/graph/reading_practice_package.json ulga/reports/reading_practice_package_summary.json
```

## 13. S19 Closeout Result

Status:

```text
IMPLEMENTED_ON_MAIN
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation
Task name: Reading Practice Output Package Implementation
Reading system target: Reading System V1
Stage: S19
Input source: S17 candidate item builder output; S18 item validator
Output artifact: package builder code, package builder tests, implementation report
Progress contribution: Packages validated candidate Reading items into a candidate-only practice package while preserving source traceability, evidence, answer models, validation gate result, answer key, and no-promotion/no-learner-facing boundaries
Completed stage count: 9 / 10 after S19
Remaining stage count: 1 / 10 after S19
Blocking issue: Requires local test confirmation after direct main pull
Deferred issue: S20 closeout QA, V2-V5 roadmap
Generated artifact policy: No generated artifacts committed
Runtime impact: None
Promotion impact: None
Closeout status: IMPLEMENTED_ON_MAIN_PENDING_LOCAL_CONFIRMATION
Next allowed task: RAZ-AW-S20_ReadingPracticeCloseoutQA
```

## 14. Next Allowed Task

```text
RAZ-AW-S20_ReadingPracticeCloseoutQA
```

S20 may perform V1 closeout QA. It must not implement V2-V5 scope.
