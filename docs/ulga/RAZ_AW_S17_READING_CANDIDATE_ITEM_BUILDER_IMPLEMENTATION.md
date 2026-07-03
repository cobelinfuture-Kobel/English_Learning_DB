# RAZ-AW-S17 Reading Candidate Item Builder Implementation

## 1. Task

`RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation`

This task implements the first Reading System V1 candidate item builder.

The builder reads the S11 Reading Authority intake query index, applies the S15 source selector boundary and the S16 question-type contracts, and emits `READING_PRACTICE_ITEM_V1` candidate items.

## 2. Scope

S17 implements candidate generation only.

It does not implement S18 validation, S19 output packaging, learner-facing delivery, runtime integration, or Reading Authority promotion.

## 3. Files Created

```text
ulga/builders/build_reading_candidate_items.py
tests/ulga/test_reading_candidate_item_builder.py
docs/ulga/RAZ_AW_S17_READING_CANDIDATE_ITEM_BUILDER_IMPLEMENTATION.md
```

## 4. Generated Artifact Policy

The builder can write generated artifacts when run locally:

```text
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
```

These generated artifacts are not committed by this task.

## 5. Runtime Impact

None.

This task does not modify runtime, app code, dashboards, schedulers, learner state, or APIs.

## 6. Promotion Impact

None.

Generated items remain:

```text
candidate_generated
candidate_only
not_promoted
not learner_facing
validator_status = not_run
```

## 7. Builder Input

Default input:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
```

If the index is unavailable, the builder writes an empty candidate output with `PASS_WITH_WARNINGS`.

## 8. Builder Output

Default output:

```text
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
```

Top-level output schema:

```text
READING_PRACTICE_ITEMS_CANDIDATE_OUTPUT_V1
```

Item schema:

```text
READING_PRACTICE_ITEM_V1
```

## 9. Supported Question Types

S17 supports exactly the six V1 question-type families approved by S16:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

## 10. Boundary Rules Implemented

The builder rejects a source item if:

```text
source_type is not approved
source_intake_id is missing
source_record_id is missing
clean_text is empty
sentence_count is invalid
generated_content is true
authority_status is not candidate_only
promotion_status is not not_promoted
text appears abnormal or noisy
```

The builder also checks question-type/source compatibility before generating each item.

## 11. S14 Contract Mapping

Each generated item includes:

```text
item_id
schema_version
generation_task
status
skill
question_type
level
source
evidence
prompt
answer_model
tags
validation
lifecycle
```

The builder maps source traceability into the S14 `source` object without inventing source metadata.

## 12. S15 Contract Mapping

S17 applies S15 source-selection boundaries:

```text
approved source types
candidate-only source status
not-promoted source status
non-generated source text
sentence-count limits
source/question-type compatibility
stable deterministic selection order
```

## 13. S16 Contract Mapping

S17 generates only question types with compatible answer models:

| Question type | Answer model |
|---|---|
| `literal_who` | `single_choice` |
| `literal_what` | `single_choice` |
| `literal_where` | `single_choice` |
| `true_false` | `true_false` |
| `sentence_ordering` | `ordered_sequence` |
| `cloze_vocabulary` | `cloze_text` |

## 14. Validation Boundary

S17 intentionally does not implement S18 validator logic.

Each item is emitted with:

```text
validation.validator_status = not_run
validation.source_traceability_passed = false
validation.answer_support_passed = false
validation.no_unsourced_generation_passed = false
validation.candidate_only_passed = false
```

S18 must later validate source traceability, answer support, question-type compatibility, and lifecycle boundary.

## 15. Local Execution Commands

Run builder:

```bash
python ulga/builders/build_reading_candidate_items.py
```

Run builder without writing generated artifacts:

```bash
python ulga/builders/build_reading_candidate_items.py --no-write
```

Limit output size:

```bash
python ulga/builders/build_reading_candidate_items.py --limit-per-question-type 10
```

Run tests:

```bash
pytest tests/ulga/test_reading_candidate_item_builder.py
```

## 16. S17 Closeout Result

Status:

```text
PASS_AS_DRAFT_PR
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation
Task name: Reading Candidate Item Builder Implementation
Reading system target: Reading System V1
Stage: S17
Input source: S11 Reading intake query index; S14 item contract; S15 source selector contract; S16 question type contract
Output artifact: candidate item builder code, builder unit tests, implementation report
Progress contribution: Implements candidate Reading item generation for the six V1 question types while preserving source traceability, candidate-only lifecycle, no-promotion boundary, and S18 validation handoff
Completed stage count: 7 / 10 after S17
Remaining stage count: 3 / 10 after S17
Blocking issue: None identified in code-level draft
Deferred issue: S18 validator, S19 output package, S20 closeout QA, V2-V5 roadmap
Generated artifact policy: Builder can write generated artifacts locally, but generated JSON is not committed in this task
Runtime impact: None
Promotion impact: None
Closeout status: PASS_AS_DRAFT_PR
Next allowed task: RAZ-AW-S18_ReadingItemValidator_Implementation
```

## 17. Next Allowed Task

```text
RAZ-AW-S18_ReadingItemValidator_Implementation
```

S18 may validate S17-generated candidate items. It must not implement S19 output packaging or learner-facing delivery.
