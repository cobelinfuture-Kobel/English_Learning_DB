# RAZ-AW-S18 Reading Item Validator Implementation

## 1. Task

`RAZ-AW-S18_ReadingItemValidator_Implementation`

This task implements the Reading System V1 item validator for S17-generated candidate Reading practice items.

## 2. Scope

S18 validates candidate item structure, source traceability, answer model compatibility, evidence support, question-type/source compatibility, and candidate-only lifecycle boundaries.

S18 does not implement S19 output packaging, learner-facing delivery, runtime integration, or Reading Authority promotion.

## 3. Files Created

```text
ulga/validators/validate_reading_practice_items.py
tests/ulga/test_reading_practice_items_validator.py
docs/ulga/RAZ_AW_S18_READING_ITEM_VALIDATOR_IMPLEMENTATION.md
```

## 4. Generated Artifact Policy

No generated JSON artifacts are committed by this task.

The validator reads local generated artifacts when present:

```text
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
```

These remain generated outputs and must not be committed unless a later task explicitly approves artifact persistence.

## 5. Runtime Impact

None.

This task does not modify runtime, app code, dashboards, schedulers, learner state, or APIs.

## 6. Promotion Impact

None.

S18 validates that generated items remain:

```text
candidate_only
not_promoted
not learner_facing
```

S18 does not promote candidate Reading items.

## 7. Validator Input

Default input:

```text
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
```

Programmatic input:

```python
validate_payload(payload, summary_payload=None)
```

## 8. Validator Coverage

The validator checks:

```text
top-level output schema
item schema version
required S14 item keys
approved S16 question types
question_type to answer_model compatibility
question_type to source_type compatibility
source traceability fields
source generated_content false
candidate-only/no-promotion source boundary
evidence object shape
evidence sentence count consistency
evidence.supports_answer true
prompt stem/instructions/choices
correct_choice_id membership
answer support against evidence text
ordered_sequence reconstruction
scoring mode compatibility
lifecycle candidate_only/not_promoted/not learner_facing
summary file consistency when supplied
```

## 9. Supported Question Types

S18 validates exactly the six V1 question-type families:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

## 10. Local Execution Commands

Run validator against local generated output:

```bash
python ulga/validators/validate_reading_practice_items.py
```

Run tests:

```bash
pytest tests/ulga/test_reading_practice_items_validator.py
```

Recommended S18 local sequence:

```bash
pytest tests/ulga/test_reading_candidate_item_builder.py
pytest tests/ulga/test_reading_practice_items_validator.py
```

If local generated artifacts are created during manual checks, remove them before commit unless explicitly approved:

```bash
git clean -fd -- ulga/graph/reading_practice_items.json ulga/reports/reading_practice_items_summary.json
```

## 11. S18 Closeout Result

Status:

```text
IMPLEMENTED_ON_MAIN
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S18_ReadingItemValidator_Implementation
Task name: Reading Item Validator Implementation
Reading system target: Reading System V1
Stage: S18
Input source: S14 item contract; S15 source selector contract; S16 question type contract; S17 candidate item builder output
Output artifact: validator code, validator unit tests, implementation report
Progress contribution: Validates S17-generated Reading candidate items for schema, traceability, evidence support, answer model compatibility, source/question-type compatibility, and candidate-only lifecycle boundaries
Completed stage count: 8 / 10 after S18
Remaining stage count: 2 / 10 after S18
Blocking issue: Requires local test confirmation after direct main pull
Deferred issue: S19 output package, S20 closeout QA, V2-V5 roadmap
Generated artifact policy: No generated artifacts committed
Runtime impact: None
Promotion impact: None
Closeout status: IMPLEMENTED_ON_MAIN_PENDING_LOCAL_CONFIRMATION
Next allowed task: RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation
```

## 12. Next Allowed Task

```text
RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation
```

S19 may package validated candidate Reading items. It must not implement learner-facing production delivery or promotion.
