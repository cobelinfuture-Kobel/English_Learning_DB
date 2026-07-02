# RAZ-AW-S13 Reading Practice System Goal and Progress Tracker Design Scan

## 1. Task

`RAZ-AW-S13_ReadingPracticeSystemGoalAndProgressTracker_DesignScan`

This task defines the first implementation target for the Reading System after the S11/S12 Reading Authority intake query-index closeout.

The active target is:

```text
Reading System V1 = source-grounded, candidate-only Reading practice item generation
```

This task does not generate questions, does not write builders, does not write validators, does not rebuild the S11 index, and does not promote any Reading candidate into final authority.

## 2. Scope

This design scan defines:

1. Reading System V1 goal and completion standard.
2. Reading System V1 stage map from S11/S12 through S20.
3. Source requirements for all Reading practice items.
4. Initial supported Reading question-type families.
5. Per-task progress tracking format.
6. Completed / incomplete / blocked / deferred classification rules.
7. Explicit V1 boundaries and V2-V5 roadmap placeholders.

## 3. Allowed Files

This task may create or modify only:

```text
docs/ulga/RAZ_AW_S13_READING_PRACTICE_SYSTEM_GOAL_AND_PROGRESS_TRACKER_DESIGN_SCAN.md
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

## 5. Generated Artifact Policy

No generated artifacts are allowed in this task.

This task must not create, rebuild, commit, or move:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
ulga/reports/raz_reading_authority_intake_query_index_summary.json
ulga/reports/raz_reading_authority_intake_query_index_readback_qa.json
reading_practice_items.json
reading_practice_package_summary.json
```

Large generated JSON remains excluded from GitHub unless a later artifact persistence task explicitly approves it.

## 6. Runtime Impact

None.

This task does not affect runtime, app code, dashboards, APIs, schedulers, learner state, adaptive planner state, or student-facing output.

## 7. Promotion Impact

None.

Reading candidates remain:

```text
candidate_only
not_promoted
not learner-facing
not final authority
```

V1 may later produce candidate practice items, but those items remain non-learner-facing until a separate promotion/readiness task approves them.

## 8. Source References

This task uses the following existing project contracts as its authority boundary:

1. `docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md`
2. `docs/ulga/RAZ_AW_S11_READING_AUTHORITY_INTAKE_QUERY_INDEX_BUILDER_IMPLEMENTATION.md`
3. `docs/ulga/RAZ_AW_S12_READING_AUTHORITY_INTAKE_QUERY_INDEX_READBACK_QA.md`

The governance policy requires every task to define scope, allowed files, forbidden files, generated artifact policy, runtime impact, promotion impact, stop condition, and deferred issues. S13 adopts that format as the baseline task-control contract.

S11 established the deterministic offline intake query index for RAZ-derived reading candidates. It explicitly did not promote content into final Reading Authority. It created a static intake layer for later Reading Authority, Content Query Layer, ULGA, Antigravity, and Learning Opportunity Binding stages to query.

S11 output items preserve deterministic intake IDs, source type, RAZ level, book/page metadata when available, clean text, sentence count, sentence candidate links when available, source traceability, query tags, and candidate-only authority boundary.

S12 performed readback QA against the S11 query index and summary artifacts. It verified the need to inspect level coverage, source traceability, tag normalization, warning distribution, and candidate-only / no-promotion / no-generated-content boundaries before downstream consumers rely on the index.

## 9. Problem Statement

S11/S12 made Reading source material queryable and auditable, but they did not create a Reading practice or quiz system.

The project currently has:

```text
Reading source candidates
Reading intake query index
Readback QA
Source traceability rules
Candidate-only boundary
```

The project does not yet have:

```text
Reading practice item schema
Reading source selector contract
Reading question-type contract
Reading item builder
Reading item validator
Reading practice output package
Reading closeout QA
```

Therefore, S12 closeout does not imply that Reading exercises, quizzes, worksheets, or learner-facing assessments can already be generated.

## 10. Reading System V1 Goal

Reading System V1 must produce source-grounded, candidate-only Reading practice items from approved Reading source candidates.

V1 is complete only when the system can perform this chain:

```text
RAZ / Reading source
→ S11 intake query index
→ source selector
→ question type contract
→ candidate Reading item builder
→ answer model
→ validator
→ output package
→ closeout QA
```

V1 must produce practice items that are:

1. Source-grounded.
2. Traceable to intake/source records.
3. Validated against question-type and answer-model contracts.
4. Candidate-only.
5. Non-promoted.
6. Non-learner-facing by default.
7. Safe for downstream inspection.

## 11. Reading System V1 Non-Goals

V1 must not implement:

```text
Listening practice system
Speaking practice system
Writing practice system
Final Reading Authority promotion
Learner-facing app or web UI
Adaptive planner
Learner state integration
Dashboard integration
Scheduler integration
API integration
ASR / pronunciation scoring
Audio timeline exercise generation
Open-ended writing rubric
Full Cambridge/KET pattern coverage
```

These may be future roadmap targets, but they are not V1 implementation scope.

## 12. Reading System Version Roadmap

Only V1 is active.

| Version | Status | Purpose | Implementation status |
|---|---|---|---|
| V1 | Active | Source-grounded Reading practice generation | S13-S20 |
| V2 | Deferred | Assessment pattern expansion | Not active |
| V3 | Deferred | Error tagging and weak-point diagnosis | Not active |
| V4 | Deferred | Adaptive Reading path | Not active |
| V5 | Deferred | Reading-to-Listening/Speaking/Writing bridge | Not active |

V2-V5 are roadmap placeholders only. They must not be implemented, patched, scaffolded, or partially introduced during V1 unless explicitly approved as a new task.

## 13. Reading System V1 Stage Map

| Stage | Task | Purpose | Status |
|---|---|---|---|
| S11 | `RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation` | Build deterministic offline Reading intake query index | Complete |
| S12 | `RAZ-AW-S12_ReadingAuthorityIntake_QueryIndexReadbackQA` | Read back S11 index quality and boundary conditions | Complete |
| S13 | `RAZ-AW-S13_ReadingPracticeSystemGoalAndProgressTracker_DesignScan` | Define Reading V1 goal, stage map, and progress tracker | Active |
| S14 | `RAZ-AW-S14_ReadingPracticeItemContract_DesignScan` | Define Reading item schema, evidence model, answer model, and validation requirements | Not started |
| S15 | `RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan` | Define how candidate sources are selected from S11/S12 outputs | Not started |
| S16 | `RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan` | Define V1 question-type families and per-type rules | Not started |
| S17 | `RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation` | Build candidate Reading practice items | Not started |
| S18 | `RAZ-AW-S18_ReadingItemValidator_Implementation` | Validate generated candidate Reading items | Not started |
| S19 | `RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation` | Package validated candidate items into quiz/worksheet JSON output | Not started |
| S20 | `RAZ-AW-S20_ReadingPracticeCloseoutQA` | Verify Reading V1 can produce a stable source-grounded practice package | Not started |

Reading System V1 target completion is S20.

## 14. Progress Accounting

Current progress at S13 start:

```text
Completed stages: S11, S12
Active stage: S13
Remaining stages: S14, S15, S16, S17, S18, S19, S20
Reading System V1 completion target: S20
```

Progress ratio:

```text
Completed: 2 / 10 stages
Active: 1 / 10 stages
Remaining after S13: 7 / 10 stages
```

A stage counts as complete only when:

1. Its allowed files are the only files changed.
2. Its closeout status is recorded.
3. Its generated artifact policy is satisfied.
4. Its runtime and promotion impacts remain within declared boundaries.
5. Any out-of-scope issues are classified and deferred.
6. Its output is usable by the next declared stage.

## 15. Reading Practice Item Minimum Contract Preview

S14 will define the canonical schema, but V1 already requires every future Reading practice item to include these conceptual fields:

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
```

Minimum source fields:

```text
source_system
source_intake_id
source_record_id
source_type
source_level
book_id
page_number
generated_content
```

Minimum evidence fields:

```text
evidence_text
sentence_count
evidence_span
```

Minimum answer-model fields:

```text
answer_type
correct_answer
acceptable_answers
distractor_policy
```

S14 must decide exact field names, required/optional status, schemas, and validation rules.

## 16. Data Source Requirements

V1 Reading items must be generated only from source records that satisfy all of the following:

1. Source is discoverable through the S11 intake query index or another explicitly approved Reading source index.
2. Source has traceability to an intake/source record.
3. Source has non-empty clean text or validated text content.
4. Source has a candidate-only boundary.
5. Source does not contain generated content.
6. Source can support the target question type with evidence.

V1 item generation must not use free-floating LLM-generated passages or questions without source evidence.

## 17. Initial Reading Question-Type Families

V1 should support a small deterministic-compatible set first:

| ID | Question type family | Purpose | Source requirement |
|---|---|---|---|
| `RQT-01` | `literal_who` | Identify who is doing or receiving an action | Sentence/page evidence with a person/character noun phrase |
| `RQT-02` | `literal_what` | Identify action/object/event from text | Sentence/page evidence with explicit action/object |
| `RQT-03` | `literal_where` | Identify location from text | Sentence/page evidence with explicit place/prepositional phrase |
| `RQT-04` | `true_false` | Verify literal statement against evidence | Evidence text supports true statement and safe false variant |
| `RQT-05` | `sentence_ordering` | Reorder sentence sequence | Multi-sentence page/reuse unit with stable order |
| `RQT-06` | `cloze_vocabulary` | Fill a missing word from source text | Sentence evidence with removable vocabulary token |

S16 must define exact contracts for these types before S17 can build items.

## 18. Question Types Explicitly Deferred from V1

The following are deferred:

```text
inference questions
main idea questions
author purpose questions
open-ended short answer
written summary
speaking retell
listening dictation
image-based questions
multi-modal audio/image reading questions
full Cambridge/KET part mapping
```

These require additional rubric, pattern, media, or learner-scoring contracts and must not be introduced during V1 unless explicitly approved.

## 19. Per-Task Reading Progress Tracker Format

Every S13-S20 task must include this tracker in its closeout report:

```text
Reading System Progress Tracker
Task ID:
Task name:
Reading system target:
Stage:
Input source:
Output artifact:
Progress contribution:
Completed stage count:
Remaining stage count:
Blocking issue:
Deferred issue:
Generated artifact policy:
Runtime impact:
Promotion impact:
Closeout status:
Next allowed task:
```

A valid tracker must answer:

1. What part of Reading System V1 did this task advance?
2. What artifact did it create or verify?
3. What remains blocked or deferred?
4. Whether it changed runtime or promotion state.
5. Whether generated artifacts were created, committed, moved, or intentionally excluded.
6. Which next task is allowed.

## 20. Completion Classification Rules

Use these status values:

```text
NOT_STARTED
ACTIVE
PASS
PASS_WITH_WARNINGS
BLOCKED
DEFERRED
CLOSED_AS_FOUNDATION
```

Rules:

1. `PASS` means the stage satisfied its declared stop condition without unresolved current-task blockers.
2. `PASS_WITH_WARNINGS` means warnings exist but are classified and do not block the current stage.
3. `BLOCKED` means the next stage cannot safely use the output.
4. `DEFERRED` means the work is valid but outside active V1 scope.
5. `CLOSED_AS_FOUNDATION` means the stage is sufficient foundation for V1 but not sufficient for final authority or learner-facing promotion.

## 21. Stop Conditions by Remaining Stage

### S14 stop condition

S14 passes when the Reading practice item schema, evidence model, source traceability model, answer model, and validation requirements are fully defined for V1.

S14 must not write a builder.

### S15 stop condition

S15 passes when source selection rules from S11/S12 index are defined by level, source type, sentence count, reusability tags, traceability, and candidate-only boundary.

S15 must not generate items.

### S16 stop condition

S16 passes when V1 question-type contracts are defined for the six approved question-type families.

S16 must not generate items.

### S17 stop condition

S17 passes when a deterministic candidate item builder can produce candidate Reading practice items from approved sources and write only approved generated outputs.

S17 must not promote items or create learner-facing output.

### S18 stop condition

S18 passes when a validator can reject malformed, unsourced, unsupported, promoted, or invalid-answer Reading items.

S18 must not alter generation logic beyond explicitly approved current-task blockers.

### S19 stop condition

S19 passes when validated candidate items can be packaged into a practice/quiz output structure with summary metadata.

S19 must not create web UI, runtime integration, or student delivery.

### S20 stop condition

S20 passes when Reading System V1 closeout confirms that the system can produce a stable, source-grounded, candidate-only Reading practice package and that all generated artifacts follow the approved artifact policy.

S20 must not promote V1 outputs into final Reading Authority.

## 22. Blocking Criteria for Reading V1

The following block the current or next stage:

1. Item has no source traceability.
2. Item evidence does not support the answer.
3. Question type has no contract.
4. Answer model is missing or ambiguous.
5. Source is generated content but not marked as such.
6. Candidate-only boundary is missing.
7. Generated artifact policy is violated.
8. Runtime or learner-facing output is introduced before approval.
9. V2-V5 features are implemented during V1 without explicit approval.

## 23. Deferred Issues Register

| Issue ID | Classification | Why deferred | Recommended future task | Blocks S13? |
|---|---|---|---|---|
| `READING-V2-ASSESSMENT-PATTERNS` | `FUTURE_WORK` | Cambridge/KET-style pattern expansion requires its own pattern contract | Reading System V2 assessment pattern expansion | No |
| `READING-V3-ERROR-TAGS` | `FUTURE_WORK` | Error diagnosis requires learner response data and error-tag schema | Reading System V3 error tagging | No |
| `READING-V4-ADAPTIVE-PATH` | `FUTURE_WORK` | Adaptive path requires learner state and sequencing policy | Reading System V4 adaptive path | No |
| `READING-V5-MULTISKILL-BRIDGE` | `FUTURE_WORK` | Listening/speaking/writing bridge requires media/rubric contracts | Reading System V5 multi-skill bridge | No |
| `GENERATED-ARTIFACT-PERSISTENCE` | `FUTURE_WORK` | Large generated JSON persistence policy remains separate from Reading V1 goal tracking | Generated artifact persistence policy design | No |
| `LOCAL-STASH-CLEANUP` | `FUTURE_WORK` | Existing local stashes are outside this design-only task | Local stash inventory review | No |

## 24. S13 Closeout Criteria

S13 can close when:

1. Reading System V1 is the only active implementation target.
2. V2-V5 are declared deferred roadmap placeholders.
3. S11/S12 are recorded as completed foundation stages.
4. S13-S20 stage map is defined.
5. Every future Reading V1 task has a required progress tracker format.
6. Source-grounding requirements are defined.
7. Initial V1 question-type families are identified but not implemented.
8. Runtime impact remains none.
9. Promotion impact remains none.
10. No generated artifacts are created.
11. Only this document is changed.

## 25. S13 Result

Status:

```text
PASS
```

Files changed:

```text
docs/ulga/RAZ_AW_S13_READING_PRACTICE_SYSTEM_GOAL_AND_PROGRESS_TRACKER_DESIGN_SCAN.md
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S13_ReadingPracticeSystemGoalAndProgressTracker_DesignScan
Task name: Reading Practice System Goal and Progress Tracker Design Scan
Reading system target: Reading System V1
Stage: S13
Input source: S11/S12 Reading intake query-index documentation and project task expansion control policy
Output artifact: S13 design scan markdown
Progress contribution: Defines V1 target, S13-S20 stage map, source requirements, V1 question-type boundary, progress tracker, deferred roadmap policy
Completed stage count: 3 / 10 after S13
Remaining stage count: 7 / 10 after S13
Blocking issue: None
Deferred issue: V2-V5 roadmap, generated artifact persistence, local stash cleanup
Generated artifact policy: No generated artifacts created or committed
Runtime impact: None
Promotion impact: None
Closeout status: PASS
Next allowed task: RAZ-AW-S14_ReadingPracticeItemContract_DesignScan
```

## 26. Next Allowed Task

```text
RAZ-AW-S14_ReadingPracticeItemContract_DesignScan
```

S14 may define the canonical Reading practice item schema, answer model, evidence model, and validator requirements.

S14 must not write a builder or generate Reading items.
