# RAZ-AW-S14 Reading Practice Item Contract Design Scan

## 1. Task

`RAZ-AW-S14_ReadingPracticeItemContract_DesignScan`

This task defines the canonical Reading practice item contract for Reading System V1.

The task is documentation-only. It defines the item schema, source model, evidence model, answer model, validation requirements, and closeout tracker needed before any Reading item builder may be implemented.

## 2. Scope

This design scan defines:

1. Canonical Reading practice item schema.
2. Required and optional item fields.
3. Source traceability model.
4. Evidence model.
5. Prompt model.
6. Answer model.
7. Tagging model.
8. Validation model.
9. V1 candidate-only and no-promotion boundaries.
10. Builder/validator requirements for later S17/S18 tasks.

This task does not generate Reading items and does not implement code.

## 3. Allowed Files

This task may create or modify only:

```text
docs/ulga/RAZ_AW_S14_READING_PRACTICE_ITEM_CONTRACT_DESIGN_SCAN.md
```

## 4. Forbidden Files

This task must not modify:

```text
ulga/builders/*
ulga/validators/*
ulga/audits/*
tests/*
ulga/graph/*
ulga/reports/*
site/*
runtime/*
learner_state/*
dashboard/*
```

## 5. Current-task Blockers

S14 is blocked if it fails to define any of the following:

1. Canonical top-level item fields.
2. Required source traceability fields.
3. Required evidence fields.
4. Required answer model fields.
5. Candidate-only / no-promotion fields.
6. Validation requirements for later S18 enforcement.
7. Explicit boundary that S14 does not generate items.

## 6. Warning Policy

Allowed warnings:

```text
question-type-specific rules deferred to S16
source-selection rules deferred to S15
builder implementation deferred to S17
validator implementation deferred to S18
output packaging deferred to S19
closeout QA deferred to S20
```

Blocking warnings:

```text
schema cannot preserve source traceability
schema cannot represent evidence support
schema cannot represent answer model
schema allows learner-facing promotion by default
schema implies unsourced item generation
schema requires generated artifacts in S14
```

## 7. Generated Artifact Policy

No generated artifacts are allowed in this task.

This task must not create, rebuild, commit, or move:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
ulga/reports/raz_reading_authority_intake_query_index_summary.json
ulga/reports/raz_reading_authority_intake_query_index_readback_qa.json
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
reading_practice_items.json
reading_practice_package_summary.json
```

## 8. Runtime Impact

None.

This task does not affect runtime, app code, dashboards, APIs, schedulers, learner state, adaptive planner state, or student-facing output.

## 9. Promotion Impact

None.

All future items following this contract remain:

```text
candidate_generated
candidate_only
not_promoted
not learner_facing
```

No item may become final Reading Authority or learner-facing content through S14.

## 10. Stop Condition

S14 passes when this document defines:

1. `READING_PRACTICE_ITEM_V1` schema.
2. Required top-level fields.
3. Required source traceability object.
4. Required evidence object.
5. Required prompt object.
6. Required answer model object.
7. Required tags object.
8. Required validation object.
9. Required lifecycle/status fields.
10. A minimal valid item example.
11. Invalid item examples that later validators must reject.
12. Handoff requirements for S15, S16, S17, and S18.

S14 must stop after this contract is defined. It must not write a builder, validator, test, generated JSON, runtime output, or learner-facing artifact.

## 11. Deferred Issues Register

| Issue ID | Classification | Why deferred | Recommended future task | Blocks S14? |
|---|---|---|---|---|
| `S15-SOURCE-SELECTOR` | `FUTURE_WORK` | Source selection depends on query-index sampling rules and should not be embedded in item schema | `RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan` | No |
| `S16-QUESTION-TYPES` | `FUTURE_WORK` | Per-question-type generation rules require a separate contract | `RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan` | No |
| `S17-ITEM-BUILDER` | `FUTURE_WORK` | Builder implementation is forbidden in S14 | `RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation` | No |
| `S18-VALIDATOR` | `FUTURE_WORK` | Validator implementation is forbidden in S14 | `RAZ-AW-S18_ReadingItemValidator_Implementation` | No |
| `S19-OUTPUT-PACKAGE` | `FUTURE_WORK` | Quiz/worksheet package structure belongs after item generation and validation | `RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation` | No |
| `READING-V2-ASSESSMENT-PATTERNS` | `FUTURE_WORK` | Cambridge/KET pattern expansion is outside V1 item core | Reading System V2 | No |
| `READING-V3-ERROR-TAGS` | `FUTURE_WORK` | Learner error diagnosis requires answer-attempt data and error-tag schema | Reading System V3 | No |

## 12. Source References

S14 follows the project governance rule that each task must declare scope, allowed files, forbidden files, generated artifact policy, runtime impact, promotion impact, stop condition, and deferred issues.

S14 also follows S13, which made Reading System V1 the active target and identified S14 as the stage that defines the canonical Reading practice item schema, answer model, evidence model, and validator requirements.

S13 also established that Reading System V1 must remain source-grounded, traceable, candidate-only, non-promoted, non-learner-facing by default, and safe for downstream inspection.

## 13. Schema Name

Canonical schema version:

```text
READING_PRACTICE_ITEM_V1
```

Canonical skill:

```text
reading
```

Canonical lifecycle status values:

```text
candidate_draft
candidate_generated
candidate_validated
candidate_rejected
blocked
```

V1 generated items should normally start as:

```text
candidate_generated
```

and become:

```text
candidate_validated
```

only after S18 validator acceptance.

## 14. Canonical Top-level Item Shape

A V1 Reading practice item must use this top-level shape:

```json
{
  "item_id": "READING_ITEM_000001",
  "schema_version": "READING_PRACTICE_ITEM_V1",
  "generation_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
  "status": "candidate_generated",
  "skill": "reading",
  "question_type": "literal_who",
  "level": {
    "source_level": "RAZ_A",
    "cefr_estimate": "preA1",
    "level_confidence": "source_declared"
  },
  "source": {},
  "evidence": {},
  "prompt": {},
  "answer_model": {},
  "tags": {},
  "validation": {},
  "lifecycle": {}
}
```

## 15. Required Top-level Fields

| Field | Required | Type | Purpose |
|---|---:|---|---|
| `item_id` | Yes | string | Stable deterministic Reading item ID |
| `schema_version` | Yes | string | Must equal `READING_PRACTICE_ITEM_V1` |
| `generation_task` | Yes | string | Task that generated or defined the item |
| `status` | Yes | string | Candidate lifecycle status |
| `skill` | Yes | string | Must equal `reading` |
| `question_type` | Yes | string | V1 question-type family ID/name |
| `level` | Yes | object | RAZ/CEFR level metadata |
| `source` | Yes | object | Source traceability |
| `evidence` | Yes | object | Textual evidence supporting the answer |
| `prompt` | Yes | object | Learner-facing prompt fields, still candidate-only |
| `answer_model` | Yes | object | Correct answer and scoring contract |
| `tags` | Yes | object | Reading skill, vocabulary, grammar, theme, reuse tags |
| `validation` | Yes | object | Validation flags and validator results |
| `lifecycle` | Yes | object | Candidate-only, promotion, learner-facing boundaries |

## 16. Level Object

Required shape:

```json
{
  "source_level": "RAZ_A",
  "cefr_estimate": "preA1",
  "level_confidence": "source_declared"
}
```

Required fields:

| Field | Required | Allowed values / rule |
|---|---:|---|
| `source_level` | Yes | RAZ level or approved source level label |
| `cefr_estimate` | Yes | `preA1`, `A1`, `A1+`, `A2`, or `unknown` for V1 |
| `level_confidence` | Yes | `source_declared`, `derived`, `estimated`, `unknown` |

V1 should prefer source-declared RAZ level over inferred level.

`unknown` is allowed only when the source itself has no reliable level and the item is still useful for structural testing. S17/S18 should count and report unknown levels.

## 17. Source Traceability Object

Required shape:

```json
{
  "source_system": "RAZ",
  "source_intake_id": "RAZ_READING_INTAKE_000001",
  "source_record_id": "RAZ_A_BOOK001_P003",
  "source_type": "page_unit",
  "source_level": "A",
  "book_id": "RAZ_A_BOOK001",
  "page_number": 3,
  "source_path": "raz_output_jsons/derived/Level_A/...",
  "generated_content": false,
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted"
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `source_system` | Yes | `RAZ` for current V1 RAZ line |
| `source_intake_id` | Yes | Must reference S11 intake item when available |
| `source_record_id` | Yes | Must preserve original/source record ID when available |
| `source_type` | Yes | Source category from approved source selector |
| `source_level` | Yes | Source level label |
| `book_id` | Conditional | Required when source has book metadata |
| `page_number` | Conditional | Required when source has page metadata |
| `source_path` | Conditional | Required when source path is available |
| `generated_content` | Yes | Must be `false` for V1 source material |
| `authority_status` | Yes | Must be `candidate_only` |
| `promotion_status` | Yes | Must be `not_promoted` |

S18 must reject any item whose source object cannot prove traceability back to an approved source record.

## 18. Approved V1 Source Types

S14 recognizes these source types as schema-compatible:

```text
sentence_candidate
page_unit
reuse_unit_candidate
normalized_reading_unit
enriched_reading_unit
```

S15 must decide which source types are eligible for each question type.

S14 does not decide sampling, ranking, or source selection priority.

## 19. Evidence Object

Required shape:

```json
{
  "evidence_text": "The boy runs.",
  "evidence_sentences": [
    "The boy runs."
  ],
  "sentence_count": 1,
  "evidence_span": {
    "start_char": 0,
    "end_char": 13
  },
  "supports_answer": true,
  "evidence_source": "source_text"
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `evidence_text` | Yes | Non-empty text from approved source |
| `evidence_sentences` | Yes | Array of source-grounded sentences |
| `sentence_count` | Yes | Integer >= 1 |
| `evidence_span` | Conditional | Required when char offsets are available |
| `supports_answer` | Yes | Must be `true` after validator acceptance |
| `evidence_source` | Yes | `source_text`, `source_sentence`, or `source_page_unit` |

The evidence object must contain the text needed to justify the correct answer. It must not contain invented text that is absent from the source.

## 20. Prompt Object

Required shape:

```json
{
  "stem": "Who runs?",
  "instructions": "Choose the correct answer.",
  "choices": [
    {
      "choice_id": "A",
      "text": "The boy"
    },
    {
      "choice_id": "B",
      "text": "The dog"
    },
    {
      "choice_id": "C",
      "text": "The teacher"
    }
  ],
  "display_text": "The boy runs."
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `stem` | Yes | Non-empty question stem |
| `instructions` | Yes | Non-empty task instruction |
| `choices` | Conditional | Required for choice-based items |
| `display_text` | Conditional | Required when the item shows source text to the learner |

S14 does not require all items to be multiple choice. The prompt shape must support V1 answer types defined below.

## 21. Answer Model Object

Required shape:

```json
{
  "answer_type": "single_choice",
  "correct_answer": "The boy",
  "correct_choice_id": "A",
  "acceptable_answers": [
    "The boy"
  ],
  "distractor_policy": "same_level_or_source_supported",
  "scoring": {
    "mode": "exact_match",
    "points": 1
  }
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `answer_type` | Yes | Must be one of approved V1 answer types |
| `correct_answer` | Yes | Must be supported by evidence |
| `correct_choice_id` | Conditional | Required for choice-based items |
| `acceptable_answers` | Yes | Array; includes canonical answer |
| `distractor_policy` | Conditional | Required when choices are present |
| `scoring` | Yes | Scoring mode and points |

## 22. Approved V1 Answer Types

S14 approves these generic answer model types:

```text
single_choice
true_false
ordered_sequence
cloze_text
```

Mapping to V1 question-type families:

| Answer type | Compatible question-type families |
|---|---|
| `single_choice` | `literal_who`, `literal_what`, `literal_where` |
| `true_false` | `true_false` |
| `ordered_sequence` | `sentence_ordering` |
| `cloze_text` | `cloze_vocabulary` |

S16 must define exact per-type prompt and answer rules.

## 23. Scoring Object

Required shape:

```json
{
  "mode": "exact_match",
  "points": 1,
  "case_sensitive": false,
  "trim_whitespace": true
}
```

Allowed scoring modes for V1:

```text
exact_match
choice_id_match
boolean_match
sequence_exact_match
```

V1 does not support partial-credit writing rubrics, speaking rubrics, pronunciation scoring, or free-form semantic grading.

## 24. Tags Object

Required shape:

```json
{
  "reading_skill": [
    "literal_comprehension"
  ],
  "grammar": [],
  "vocabulary": [],
  "theme": [],
  "reusability": [
    "exercise_seed"
  ],
  "source_tags": []
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `reading_skill` | Yes | At least one reading skill tag |
| `grammar` | Yes | Array, may be empty |
| `vocabulary` | Yes | Array, may be empty |
| `theme` | Yes | Array, may be empty |
| `reusability` | Yes | Array, may be empty |
| `source_tags` | Yes | Array, may be empty |

Tag arrays must contain strings only. Dict-shaped metadata must not be stringified into tags.

## 25. Validation Object

Required shape:

```json
{
  "source_traceability_required": true,
  "source_traceability_passed": false,
  "answer_must_be_supported_by_evidence": true,
  "answer_support_passed": false,
  "no_unsourced_generation": true,
  "no_unsourced_generation_passed": false,
  "candidate_only_required": true,
  "candidate_only_passed": false,
  "validator_status": "not_run",
  "validator_errors": [],
  "validator_warnings": []
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `source_traceability_required` | Yes | Must be `true` |
| `source_traceability_passed` | Yes | Initially false until S18 validates |
| `answer_must_be_supported_by_evidence` | Yes | Must be `true` |
| `answer_support_passed` | Yes | Initially false until S18 validates |
| `no_unsourced_generation` | Yes | Must be `true` |
| `no_unsourced_generation_passed` | Yes | Initially false until S18 validates |
| `candidate_only_required` | Yes | Must be `true` |
| `candidate_only_passed` | Yes | Initially false until S18 validates |
| `validator_status` | Yes | `not_run`, `pass`, `pass_with_warnings`, or `fail` |
| `validator_errors` | Yes | Array |
| `validator_warnings` | Yes | Array |

S17 may emit `validator_status = not_run`. S18 is responsible for changing validation status.

## 26. Lifecycle Object

Required shape:

```json
{
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "learner_facing": false,
  "generated_item": true,
  "generated_content": false,
  "requires_review": true
}
```

Required fields:

| Field | Required | Rule |
|---|---:|---|
| `authority_status` | Yes | Must be `candidate_only` |
| `promotion_status` | Yes | Must be `not_promoted` |
| `learner_facing` | Yes | Must be `false` in V1 |
| `generated_item` | Yes | `true` for item generated from source |
| `generated_content` | Yes | `false` for source content; generated question/prompt remains item-level derived data |
| `requires_review` | Yes | Must be `true` unless a later promotion task changes policy |

Important distinction:

```text
generated_item = true
```

means the exercise item was generated from source material.

```text
generated_content = false
```

means the underlying Reading source text is not generated content.

## 27. Minimal Valid Item Example

```json
{
  "item_id": "READING_ITEM_RAZ_A_000001",
  "schema_version": "READING_PRACTICE_ITEM_V1",
  "generation_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
  "status": "candidate_generated",
  "skill": "reading",
  "question_type": "literal_who",
  "level": {
    "source_level": "RAZ_A",
    "cefr_estimate": "preA1",
    "level_confidence": "source_declared"
  },
  "source": {
    "source_system": "RAZ",
    "source_intake_id": "RAZ_READING_INTAKE_A_000001",
    "source_record_id": "RAZ_A_BOOK001_P003",
    "source_type": "sentence_candidate",
    "source_level": "A",
    "book_id": "RAZ_A_BOOK001",
    "page_number": 3,
    "source_path": "raz_output_jsons/derived/Level_A/example.json",
    "generated_content": false,
    "authority_status": "candidate_only",
    "promotion_status": "not_promoted"
  },
  "evidence": {
    "evidence_text": "The boy runs.",
    "evidence_sentences": [
      "The boy runs."
    ],
    "sentence_count": 1,
    "evidence_span": {
      "start_char": 0,
      "end_char": 13
    },
    "supports_answer": true,
    "evidence_source": "source_sentence"
  },
  "prompt": {
    "stem": "Who runs?",
    "instructions": "Choose the correct answer.",
    "choices": [
      {
        "choice_id": "A",
        "text": "The boy"
      },
      {
        "choice_id": "B",
        "text": "The dog"
      },
      {
        "choice_id": "C",
        "text": "The teacher"
      }
    ],
    "display_text": "The boy runs."
  },
  "answer_model": {
    "answer_type": "single_choice",
    "correct_answer": "The boy",
    "correct_choice_id": "A",
    "acceptable_answers": [
      "The boy"
    ],
    "distractor_policy": "same_level_or_source_supported",
    "scoring": {
      "mode": "choice_id_match",
      "points": 1,
      "case_sensitive": false,
      "trim_whitespace": true
    }
  },
  "tags": {
    "reading_skill": [
      "literal_comprehension"
    ],
    "grammar": [],
    "vocabulary": [
      "boy",
      "run"
    ],
    "theme": [],
    "reusability": [
      "exercise_seed"
    ],
    "source_tags": []
  },
  "validation": {
    "source_traceability_required": true,
    "source_traceability_passed": false,
    "answer_must_be_supported_by_evidence": true,
    "answer_support_passed": false,
    "no_unsourced_generation": true,
    "no_unsourced_generation_passed": false,
    "candidate_only_required": true,
    "candidate_only_passed": false,
    "validator_status": "not_run",
    "validator_errors": [],
    "validator_warnings": []
  },
  "lifecycle": {
    "authority_status": "candidate_only",
    "promotion_status": "not_promoted",
    "learner_facing": false,
    "generated_item": true,
    "generated_content": false,
    "requires_review": true
  }
}
```

## 28. Invalid Item Examples Later Validators Must Reject

### 28.1 Missing source traceability

Reject if:

```json
{
  "source": {
    "source_system": "RAZ"
  }
}
```

Reason:

```text
missing source_intake_id / source_record_id
```

### 28.2 Unsupported answer

Reject if:

```json
{
  "evidence": {
    "evidence_text": "The boy runs."
  },
  "answer_model": {
    "correct_answer": "The dog"
  }
}
```

Reason:

```text
answer not supported by evidence
```

### 28.3 Promoted item in V1

Reject if:

```json
{
  "lifecycle": {
    "authority_status": "final_authority",
    "promotion_status": "promoted",
    "learner_facing": true
  }
}
```

Reason:

```text
V1 generated items must remain candidate-only and non-learner-facing
```

### 28.4 Dict-shaped tags

Reject if:

```json
{
  "tags": {
    "reusability": [
      {
        "tag": "exercise_seed"
      }
    ]
  }
}
```

Reason:

```text
tag arrays must contain strings only
```

## 29. Handoff to S15

S15 must define source selection rules, including:

1. Eligible source types per question-type family.
2. Level filters.
3. Sentence count filters.
4. Reusability tag filters.
5. Source traceability minimums.
6. Candidate-only and generated-content exclusions.
7. Sampling/ranking policy.

S15 must not change the S14 item schema unless a schema defect blocks source selection.

## 30. Handoff to S16

S16 must define exact question-type contracts for:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

For each type, S16 must define:

1. Required source features.
2. Prompt construction rules.
3. Answer construction rules.
4. Distractor policy.
5. Evidence support rule.
6. Validation rule.

S16 must not generate items.

## 31. Handoff to S17

S17 may implement the candidate item builder only after S14-S16 are complete.

S17 builder must:

1. Read approved source candidates.
2. Emit `READING_PRACTICE_ITEM_V1` candidate items.
3. Preserve source traceability.
4. Mark validator status as `not_run` unless validation is explicitly included in S17 scope.
5. Keep items candidate-only.
6. Write only approved generated outputs.

## 32. Handoff to S18

S18 validator must reject items that violate:

1. Required field presence.
2. Schema version.
3. Source traceability.
4. Evidence support.
5. Answer model validity.
6. Tag shape.
7. Candidate-only/no-promotion/no-learner-facing boundary.
8. Generated artifact policy.
9. Question-type compatibility.

## 33. S14 Closeout Result

Status:

```text
PASS
```

Files changed:

```text
docs/ulga/RAZ_AW_S14_READING_PRACTICE_ITEM_CONTRACT_DESIGN_SCAN.md
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S14_ReadingPracticeItemContract_DesignScan
Task name: Reading Practice Item Contract Design Scan
Reading system target: Reading System V1
Stage: S14
Input source: S13 Reading Practice System Goal and Progress Tracker Design Scan; S11/S12 intake query-index boundary; Project Task Expansion Control Policy
Output artifact: S14 design scan markdown
Progress contribution: Defines READING_PRACTICE_ITEM_V1 schema, source traceability model, evidence model, prompt model, answer model, tags model, validation model, lifecycle boundary, invalid-item rejection requirements, and S15-S18 handoff rules
Completed stage count: 4 / 10 after S14
Remaining stage count: 6 / 10 after S14
Blocking issue: None
Deferred issue: S15 source selector, S16 question type contract, S17 builder, S18 validator, S19 output package, V2-V5 roadmap
Generated artifact policy: No generated artifacts created or committed
Runtime impact: None
Promotion impact: None
Closeout status: PASS
Next allowed task: RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan
```

## 34. Next Allowed Task

```text
RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan
```

S15 may define how V1 reads and filters candidate sources from S11/S12 outputs.

S15 must not generate Reading items.
