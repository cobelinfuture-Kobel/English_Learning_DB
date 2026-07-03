# E4S P1 Reading V1 Goal and Progress Tracker Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Current Sub-task:

```text
E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan
```

Data Sources and Ordering Basis:

```text
1. docs/status/E4S_P0_CLOSEOUT_SOURCE_AUTHORITY_FOUNDATION_READBACK.md
2. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
3. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
4. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
5. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
6. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
7. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_GOAL_AND_PROGRESS_TRACKER.md
```

This task starts Phase 1 only at the design-control level. It defines the Reading V1 goal, progress tracker, supported item types, required evidence fields, forbidden scope, milestone distance vector, and next shortest step.

This task does not create Reading questions, Reading practice HTML, generator code, validator code, learner state, adaptive recommendation, assessment expansion, writing output, dialogue output, listening output, or final content promotion.

---

## 2. Task Boundary

Task:

```text
E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan
```

Scope:

```text
Define the Phase 1 Reading V1 objective and progress-tracking contract so future P1 implementation tasks can be measured against source-grounded Reading V1 readiness instead of generic task completion.
```

Allowed files:

```text
docs/ulga/E4S_P1_READING_V1_GOAL_AND_PROGRESS_TRACKER.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
source corpus payloads
Reading question JSON
Reading practice HTML
site HTML
runtime files
generators
validators
tests for runtime or generator code
learner state files
learner profile files
adaptive scheduler files
assessment engine files
writing / dialogue / listening outputs
promotion artifacts
```

Generated artifact policy:

```text
No generated Reading practice artifacts are allowed in this sub-task.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This task defines progress tracking only and performs no content/source promotion.
```

Stop condition:

```text
Stop after the Reading V1 goal, readiness dimensions, supported item-type boundary, required trace/evidence/answer-model fields, forbidden scope, P1 task sequence, gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Reading V1 Goal

Reading V1 exists to produce source-grounded Reading practice packages from approved Reading source/query contracts.

Reading V1 must be:

```text
source-grounded
evidence-based
traceable
validator-readable
candidate-first
not learner-adaptive
not final promotion
```

Reading V1 should eventually answer:

```text
Given an approved Reading source candidate, can the system create a small practice package where every item has source trace, evidence, answer model, and validator-readable structure?
```

Reading V1 must not answer:

```text
Which learner should read this next?
What is the learner's level?
What weakness does the learner have?
Which concept should be scheduled for review?
Can this source become final Reading Authority?
Can this item become public / learner-facing without review?
```

---

## 4. Reading V1 Output Definition

The future Reading V1 output is a candidate practice package, not final authority.

Future package class:

```text
reading_practice_candidate_package
```

Future package must include:

```text
package_id
package_version
source_manifest_refs
source_trace
item_list
item_type
prompt
source_evidence
answer_model
validator_fields
review_status
promotion_status
blocked_use
```

Required default statuses:

```text
review_status = not_reviewed | validator_reviewed
promotion_status = not_promoted
learner_facing_status = blocked_until_validator_pass
```

This P1-S0 task does not create the package schema file. It only defines the goal and tracker for later P1-S1.

---

## 5. Supported Reading V1 Item Types

The first Reading V1 item-type boundary is limited to these six item types:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

### 5.1 literal_who

Purpose:

```text
Ask who is present or who performs an explicit action in the source text.
```

Required evidence:

```text
A source sentence or page unit that explicitly states the person / character.
```

Blocked behavior:

```text
Do not infer unstated identity.
Do not ask opinion or prediction questions.
```

### 5.2 literal_what

Purpose:

```text
Ask about explicitly stated objects, actions, or events.
```

Required evidence:

```text
A source sentence or page unit containing the answer span.
```

Blocked behavior:

```text
Do not require background knowledge.
Do not require multi-step inference.
```

### 5.3 literal_where

Purpose:

```text
Ask about explicitly stated location or setting.
```

Required evidence:

```text
A source sentence or page unit with a clear place expression.
```

Blocked behavior:

```text
Do not infer location from illustrations unless image evidence is explicitly available and approved.
```

### 5.4 true_false

Purpose:

```text
Check whether a statement matches the source text.
```

Required evidence:

```text
A source-supported statement and a validator-readable truth value.
```

Blocked behavior:

```text
No ambiguous true/false statements.
No statements requiring outside knowledge.
```

### 5.5 sentence_ordering

Purpose:

```text
Ask the learner to order source-grounded sentences or events.
```

Required evidence:

```text
A source page unit or passage unit with at least two ordered sentences/events.
```

Blocked behavior:

```text
No invented event ordering.
No ordering from unrelated source units.
```

### 5.6 cloze_vocabulary

Purpose:

```text
Remove one source-grounded vocabulary item from a sentence and ask the learner to restore it.
```

Required evidence:

```text
A source sentence and an answer span that appears in the source.
```

Blocked behavior:

```text
No cloze item from unreviewed generated text.
No vocabulary item outside the approved source/evidence boundary.
```

---

## 6. Required Trace / Evidence / Answer Model Fields

Every future Reading V1 item must include at least these metadata groups.

### 6.1 Source Trace

```text
source_id
source_family
source_manifest_ref
source_path_or_reference
source_level_claim
source_level_claim_status
source_unit_id
source_unit_type
source_sentence_ids
source_page_or_location
```

### 6.2 Evidence

```text
evidence_text
evidence_span
answer_span
source_sentence_quote_policy
evidence_is_direct
inference_required
```

Required defaults for V1:

```text
evidence_is_direct = true
inference_required = false
```

### 6.3 Answer Model

```text
answer_type
canonical_answer
accepted_answers
case_sensitive
order_sensitive
exact_match_required
scoring_policy
```

### 6.4 Validator Fields

```text
item_type_allowed
source_trace_present
evidence_present
answer_model_present
blocked_scope_absent
learner_state_absent
promotion_status_not_promoted
```

This task does not implement the validator. P1-S7 owns validator implementation.

---

## 7. Reading V1 Forbidden Scope

The following are explicitly out of scope for Reading V1 initial build:

```text
adaptive learning
learner state
learner placement
mastery scoring
error diagnosis
wrong-answer weak-point analysis
spaced review scheduling
AI large-scale mixed generation
Listening practice
Speaking practice
Writing practice
Cambridge assessment expansion
student account system
final content promotion
public distribution
source payload redistribution
```

Reading V1 may create candidate packages only after later P1 contracts and validators exist.

---

## 8. Reading V1 Progress Tracker

Progress is measured by Reading V1 readiness, not by raw task count alone.

### 8.1 Readiness Dimensions

| Dimension | Meaning | Current Status | Evidence / Owner |
|---|---|---:|---|
| Source Authority Foundation | P0 source governance complete | COMPLETE | P0 closeout |
| Reading V1 Goal | P1 goal and boundaries defined | COMPLETE | P1-S0 |
| Question Package Contract | package/item schema defined | NOT_STARTED | P1-S1 |
| Sample Question Package | small traceable sample exists | NOT_STARTED | P1-S2 |
| Practice HTML Renderer | renders candidate package | NOT_STARTED | P1-S3 |
| Answer Checker | checks V1 answer models | NOT_STARTED | P1-S4 |
| Evidence Display | displays source trace / evidence | NOT_STARTED | P1-S5 |
| Source-grounded Generator | creates V1 candidate items | NOT_STARTED | P1-S6 |
| Validator | blocks invalid package/items | NOT_STARTED | P1-S7 |
| Export / Test / Readback | end-to-end readback package | NOT_STARTED | P1-S8 |

### 8.2 Percentage Snapshot

P1 task-count progress after P1-S0:

```text
P1 completed tasks = 1 / 9
P1 task-count progress = 11%
```

Reading V1 implementation readiness:

```text
Question Contract ............. NOT_STARTED
Sample Package ................ NOT_STARTED
HTML Renderer ................. NOT_STARTED
Answer Checker ................ NOT_STARTED
Evidence Display .............. NOT_STARTED
Generator ..................... NOT_STARTED
Validator ..................... NOT_STARTED
Export / Test / Readback ...... NOT_STARTED

Overall implementation readiness: 0%
```

Interpretation:

```text
P1 governance has started.
P1 implementation has not started.
Reading V1 remains non-learner-facing until later gates pass.
```

---

## 9. P1 Task Sequence

P1 must run in this order unless a later approved roadmap patch changes the sequence.

| Order | Task ID | Task Type | Expected Deliverable | Gate Summary |
|---:|---|---|---|---|
| 0 | `E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan` | DesignScan | `docs/ulga/E4S_P1_READING_V1_GOAL_AND_PROGRESS_TRACKER.md` | Goal / tracker / boundary defined |
| 1 | `E4S-P1-S1_ReadingQuestionPackageContract_DesignScan` | DesignScan | `docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md` | Package/item schema defined |
| 2 | `E4S-P1-S2_ReadingSampleQuestionPackage_Implementation` | Implementation | sample candidate JSON | Small source-traced sample exists |
| 3 | `E4S-P1-S3_ReadingPracticeHTMLRenderer_Implementation` | Implementation | HTML renderer | Renders candidate package only |
| 4 | `E4S-P1-S4_ReadingAnswerChecker_Implementation` | Implementation | answer checker | Checks V1 answer model only |
| 5 | `E4S-P1-S5_ReadingEvidenceDisplay_Implementation` | Implementation | evidence display | Shows trace/evidence to reviewer |
| 6 | `E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation` | Implementation | generator | Generates only V1 item types |
| 7 | `E4S-P1-S7_ReadingV1Validator_Implementation` | Implementation | validator/tests | Invalid items fail |
| 8 | `E4S-P1-S8_ReadingV1ExportTestReadback_QA` | QA | readback report | End-to-end package passes |

---

## 10. Acceptance Gates for P1-S0

| Gate | Result | Evidence |
|---|---:|---|
| P1 current state declared | PASS | Section 1 |
| Data sources listed | PASS | Section 1 |
| P1-S0 task boundary defined | PASS | Section 2 |
| Reading V1 goal defined | PASS | Section 3 |
| Reading V1 output class defined | PASS | Section 4 |
| Supported V1 item types defined | PASS | Section 5 |
| Trace / evidence / answer model fields defined | PASS | Section 6 |
| Forbidden scope defined | PASS | Section 7 |
| Progress tracker defined | PASS | Section 8 |
| P1 task sequence defined | PASS | Section 9 |
| Runtime impact avoided | PASS | Documentation only |
| Reading questions avoided | PASS | No question artifacts |
| Reading HTML avoided | PASS | No HTML |
| Generator code avoided | PASS | No code |
| Validator code avoided | PASS | No code |
| Learner state avoided | PASS | No learner files |
| Promotion avoided | PASS | Design only |

---

## 11. Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Current Sub-task:

```text
E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan
```

Sub-task Status:

```text
E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan -> COMPLETED
```

P1 remaining distance after this sub-task:

```text
D_P1 = 8 sub-tasks left
```

Remaining P1 tasks:

```text
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
E4S-P1-S2_ReadingSampleQuestionPackage_Implementation
E4S-P1-S3_ReadingPracticeHTMLRenderer_Implementation
E4S-P1-S4_ReadingAnswerChecker_Implementation
E4S-P1-S5_ReadingEvidenceDisplay_Implementation
E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation
E4S-P1-S7_ReadingV1Validator_Implementation
E4S-P1-S8_ReadingV1ExportTestReadback_QA
```

---

## 12. Deferred Issues Register

```text
issue_id: E4S-P1-S0-DEFER-001
severity: high
affected_file_or_artifact: Reading question package schema
classification: FUTURE_WORK
why_deferred: P1-S0 defines goal and tracker only.
recommended_future_task: E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-002
severity: high
affected_file_or_artifact: Reading candidate package JSON
classification: FUTURE_WORK
why_deferred: Package creation requires the P1-S1 contract first.
recommended_future_task: E4S-P1-S2_ReadingSampleQuestionPackage_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-003
severity: high
affected_file_or_artifact: student-facing Reading HTML
classification: FUTURE_WORK
why_deferred: HTML renderer must wait until package contract and sample package exist.
recommended_future_task: E4S-P1-S3_ReadingPracticeHTMLRenderer_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-004
severity: high
affected_file_or_artifact: source-grounded question generator
classification: FUTURE_WORK
why_deferred: Generator requires package contract, sample package, and renderer/evidence assumptions.
recommended_future_task: E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-005
severity: high
affected_file_or_artifact: Reading V1 validator
classification: FUTURE_WORK
why_deferred: Validator requires package/item contract and representative invalid cases.
recommended_future_task: E4S-P1-S7_ReadingV1Validator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-006
severity: high
affected_file_or_artifact: learner state / adaptive learning / error diagnosis
classification: OUT_OF_SCOPE_FOR_P1_V1
why_deferred: Reading V1 explicitly excludes learner-adaptive behavior.
recommended_future_task: future P6/P7 tasks only after explicit approval
blocks_current_task: no
```

---

## 13. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md to define the Reading V1 package schema, item schema, source trace schema, evidence schema, answer model schema, validator-readable fields, invalid package examples, gates, and next distance update.
```

Stop condition:

```text
Stop here. Do not create sample Reading packages, HTML, generator code, validator code, or learner-facing output until P1-S1 is explicitly started and completed.
```
