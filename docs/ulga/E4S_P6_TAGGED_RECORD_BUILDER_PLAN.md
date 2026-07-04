# E4S-P6-I4 Tagged Record Builder Planning

## 1. Current State

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Closed Phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

Current Post-closeout Task:

```text
E4S-P6-I4_TaggedRecordBuilderPlanning_OperatorApprovedStart
```

Deliverable:

```text
docs/ulga/E4S_P6_TAGGED_RECORD_BUILDER_PLAN.md
```

Precondition evidence:

```text
E4S-P6-I3B_LocalRuntimeValidatorSmokeQA_Readback = PASS_LOCAL_RUNTIME_EVIDENCE_LOCKED
STATIC_VALIDATOR = CREATED_AND_LOCAL_SMOKE_PASS
GOLDEN_SAMPLE_FIXTURE = CREATED_AND_VALIDATED
LOCAL_RUNTIME_VALIDATION_REPORT = CREATED_AND_LOCKED_TO_GITHUB
I4_TAGGED_RECORD_BUILDER_PLANNING = UNBLOCKED_FOR_OPERATOR_APPROVED_START
```

This deliverable is a planning document only. It does not implement a builder, ingest source data, produce graph/output JSON, mutate runtime learner state, modify UI, aggregate weak points, or create adaptive recommendations.

---

## 2. Scope Lock

I4 may define:

```text
- approved future builder purpose
- input assumptions from Reading V1 question packages
- mapping from question package fields to tagged_question_record
- mapping from answer events to learner_answer_record
- conservative path to error_diagnosis_record
- remediation_link_record mapping strategy
- validation handoff to the existing P6 static validator
- I5 implementation boundary
```

I4 must not create or modify:

```text
- ulga/builders/build_e4s_p6_error_tagging_records.py
- ulga/graph/e4s_p6_error_tagging_records.json
- source-ingestion logic
- learner answer capture runtime
- UI / dashboard
- learner mastery score
- weak-point summary
- generated remediation exercises
- adaptive recommendation path
```

---

## 3. Builder Purpose

Future builder purpose:

```text
Convert approved, source-grounded Reading V1 question packages plus externally supplied answer-event records into P6-S2-compatible records that can be validated by the P6 static validator.
```

The future builder should emit these logical records:

```text
tagged_question_record
learner_answer_record
error_diagnosis_record
remediation_link_record
```

The future builder is not a runtime answer collector. It only transforms approved offline/static input artifacts into validator-ready records.

---

## 4. Input Assumptions

### 4.1 Approved Question Package Input

A future I5 builder may consume only approved, static question-package records that already contain source-grounded evidence.

Expected minimal question package fields:

```text
question_id
source_type
source_unit_id
level
question_type
skill_area
concept_tags
cognitive_skill
correct_answer
source_evidence_ref
taxonomy_version
schema_version
```

Allowed Reading V1 question_type values:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

Rules:

```text
- question_type must be active for Reading V1.
- skill_area must use P6-S1 controlled values.
- concept_tags must use P6-S1 controlled values.
- cognitive_skill must use P6-S1 controlled values.
- source_evidence_ref must remain an ID reference, not a long source-text quote.
- correct_answer may be a normalized answer model or reference, but must not duplicate long copyrighted text.
```

### 4.2 Approved Answer Event Input

The future builder may consume externally supplied static answer-event records.

Expected minimal answer event fields:

```text
question_id
learner_ref
attempt_id
attempt_index
learner_answer
answer_format
is_correct
scoring_method
answered_at
```

Rules:

```text
- learner_ref must be pseudonymous.
- answer events must already be collected outside P6.
- I5 builder must not capture learner answers directly.
- I5 builder must not mutate learner state.
- A wrong answer is evidence only, not a mastery conclusion.
```

---

## 5. Output Record Mapping Plan

### 5.1 tagged_question_record Mapping

Future mapping:

| Output Field | Source | Rule |
|---|---|---|
| `tagged_question_id` | builder-generated | Deterministic `TQ_` ID from question_id or stable counter. |
| `question_id` | question package | Preserve exactly. |
| `source_type` | question package | Preserve exactly. |
| `source_unit_id` | question package | Preserve when available. Required for Reading V1 when source-grounded. |
| `level` | question package | Preserve exactly. |
| `question_type` | question package | Must be active Reading V1 type. |
| `skill_area` | question package | Must use P6-S1 controlled value. |
| `concept_tags` | question package | Must be non-empty controlled array. |
| `cognitive_skill` | question package | Must use P6-S1 controlled value. |
| `correct_answer` | question package | Use normalized answer model/reference. |
| `source_evidence_ref` | question package | Preserve exactly. Must not expand to long source text. |
| `taxonomy_version` | constant/input | Default `p6_s1_v1`. |
| `schema_version` | constant | Default `p6_s2_v1`. |

Acceptance rule:

```text
tagged_question_record must validate through record_shape_gate, source_trace_gate, taxonomy_gate, and compatibility_gate.
```

### 5.2 learner_answer_record Mapping

Future mapping:

| Output Field | Source | Rule |
|---|---|---|
| `learner_answer_id` | builder-generated | Deterministic `LA_` ID from attempt_id or stable counter. |
| `tagged_question_id` | tagged_question_record | Must link to generated tagged_question_id. |
| `question_id` | answer event | Must match question package question_id. |
| `learner_ref` | answer event | Pseudonymous only. |
| `attempt_id` | answer event | Preserve exactly. |
| `attempt_index` | answer event | Preserve exactly. |
| `learner_answer` | answer event | Preserve normalized answer value; do not include private notes. |
| `answer_format` | answer event | Preserve if available. |
| `is_correct` | answer event | Preserve boolean. |
| `scoring_method` | answer event | Preserve if available. |
| `answered_at` | answer event | Preserve timestamp if available. |
| `schema_version` | constant | Default `p6_s2_v1`. |

Acceptance rule:

```text
learner_answer_record must validate through record_shape_gate and link_integrity_gate.
```

### 5.3 error_diagnosis_record Mapping

Future mapping must stay conservative.

| Output Field | Source | Rule |
|---|---|---|
| `error_diagnosis_id` | builder-generated | Deterministic `ED_` ID from learner_answer_id or stable counter. |
| `learner_answer_id` | learner_answer_record | Must link to generated learner_answer_id. |
| `tagged_question_id` | tagged_question_record | Must link to generated tagged_question_id. |
| `question_id` | linked records | Must match linked question_id. |
| `is_correct` | learner_answer_record | Preserve. |
| `error_type` | rule/manual diagnosis | Controlled P6-S1 value. |
| `error_detail` | rule/manual diagnosis | Controlled P6-S1 value and P6-S3 compatible. |
| `diagnosis_confidence` | rule/manual diagnosis | Conservative; high only when safe. |
| `diagnosis_basis` | rule/manual diagnosis | Must explain basis using short operational references. |
| `source_evidence_ref` | tagged_question_record | Required for Reading V1 source-grounded diagnosis. |
| `taxonomy_version` | constant/input | Default `p6_s1_v1`. |
| `schema_version` | constant | Default `p6_s2_v1`. |

Conservative diagnosis rules:

```text
- If is_correct is true, do not create specific error diagnosis unless a future contract explicitly allows diagnostic notes.
- If is_correct is false but evidence is insufficient, use unknown_error + not_enough_evidence or route to human_review_required.
- Do not infer stable weak points from one wrong answer.
- Do not create mastery_score.
- Do not aggregate repeated errors in I5.
- Do not over-promote concept_error to high confidence without repeated_same_error or human confirmation.
```

Acceptance rule:

```text
error_diagnosis_record must validate through record_shape_gate, link_integrity_gate, source_trace_gate, taxonomy_gate, compatibility_gate, and diagnosis_safety_gate.
```

### 5.4 remediation_link_record Mapping

Future mapping:

| Output Field | Source | Rule |
|---|---|---|
| `remediation_link_id` | builder-generated | Deterministic `RL_` ID from error_diagnosis_id or stable counter. |
| `error_diagnosis_id` | error_diagnosis_record | Must link to generated error_diagnosis_id. |
| `learner_answer_id` | learner_answer_record | Must link to generated learner_answer_id. |
| `tagged_question_id` | tagged_question_record | Must link to generated tagged_question_id. |
| `remediation_tag` | compatibility mapping/manual review | Controlled P6-S1 value. |
| `remediation_priority` | mapping/manual review | Informational only; not adaptive ranking. |
| `remediation_basis` | mapping/manual review | Must be short and operational. |
| `schema_version` | constant | Default `p6_s2_v1`. |

Rules:

```text
- remediation_link_record points to a practice direction only.
- remediation_link_record must not contain generated exercise content.
- remediation_link_record must not create learner-facing output.
- remediation_link_record must not update weak-point summaries.
- human_review_required is mandatory when diagnosis is unsafe.
```

Acceptance rule:

```text
remediation_link_record must validate through record_shape_gate, link_integrity_gate, taxonomy_gate, compatibility_gate, diagnosis_safety_gate, and non_generation_boundary_gate.
```

---

## 6. Future Builder Flow

A future I5 builder should use this offline/static flow:

```text
1. Load approved question package input.
2. Load approved static answer-event input.
3. Join answer events to question packages by question_id.
4. Emit tagged_question_record for each source question.
5. Emit learner_answer_record for each answer event.
6. Emit conservative error_diagnosis_record only when the answer is wrong and diagnosis rules are satisfied.
7. Emit remediation_link_record only as a non-generative practice-direction link.
8. Write ulga/graph/e4s_p6_error_tagging_records.json.
9. Run ulga/validators/validate_e4s_p6_error_tagging.py against the output.
10. Do not proceed if validator result is not PASS or approved PASS_WITH_WARNINGS.
```

Blocked in the flow:

```text
- source crawling
- PDF extraction
- source text ingestion
- runtime answer capture
- learner profile mutation
- UI rendering
- weak-point aggregation
- remediation exercise generation
- adaptive path selection
```

---

## 7. Planned I5 Artifacts

Future implementation source target:

```text
ulga/builders/build_e4s_p6_error_tagging_records.py
```

Future output target:

```text
ulga/graph/e4s_p6_error_tagging_records.json
```

Future validation report target:

```text
ulga/reports/e4s_p6_error_tagging_records_validation_report.json
```

I5 should create only the builder and static output/report required to prove P6-S2 record emission. I5 must not become a runtime learner-answer system.

---

## 8. I5 Readiness Gates

I5 may start only if all are true:

```text
PASS - I3B local runtime validator smoke QA is locked.
PASS - I4 builder plan exists.
PASS - approved static question package input is identified.
PASS - approved static answer-event input is identified.
PASS - no source ingestion is required.
PASS - no runtime answer capture is required.
PASS - no UI work is required.
```

I5 acceptance gates:

```text
PASS - builder emits tagged_question_record.
PASS - builder emits learner_answer_record.
PASS - builder emits conservative error_diagnosis_record when allowed.
PASS - builder emits remediation_link_record without generated content.
PASS - output validates against P6 static validator.
PASS - source_evidence_ref is preserved.
PASS - no learner state mutation.
PASS - no weak-point aggregation.
PASS - no adaptive recommendation.
```

I5 must stop if:

```text
- approved input shape is missing or ambiguous.
- source_evidence_ref cannot be preserved.
- answer event input is not static.
- learner identity is not pseudonymous.
- validator result is FAIL.
- generated exercise content appears in remediation_link_record.
```

---

## 9. Risks and Controls

| Risk | Control |
|---|---|
| Builder accidentally becomes source ingestion | Require pre-approved static input only. |
| Question type activates future values | Block deferred question types unless separately approved. |
| Wrong answer becomes mastery conclusion | Keep answer record and error diagnosis separate from weak-point summary. |
| Remediation becomes generated exercise | Remediation links carry tags only, not content. |
| Source trace lost | Require source_evidence_ref from question package to diagnosis record. |
| Learner privacy leakage | Use pseudonymous learner_ref and deterministic non-personal IDs. |
| Validator output misread as runtime system | Keep I5 offline/static and non-mutating. |

---

## 10. Explicit Non-goals

I4 does not create:

```text
- builder code
- graph/output JSON
- validation report JSON
- source ingestion pipeline
- learner answer capture runtime
- UI / dashboard
- learner mastery score
- weak-point summary
- generated remediation exercises
- adaptive recommendation
```

I4 does not change any existing runtime behavior.

---

## 11. Gate and Distance Update

Gate Metrics:

```text
PASS - I3B runtime smoke evidence verified as locked.
PASS - builder planning document created.
PASS - source_evidence_ref preservation strategy defined.
PASS - P6-S1 taxonomy usage strategy defined.
PASS - P6-S2 record mapping strategy defined.
PASS - future validator handoff strategy defined.
PASS - I5 artifact targets defined.
PASS - builder implementation deferred.
PASS - source ingestion remains blocked.
PASS - runtime learner answer capture remains blocked.
PASS - UI remains blocked.
PASS - weak-point aggregation remains out of scope.
PASS - adaptive recommendation remains out of scope.
```

Distance Vector:

```text
E4S-P6-I4_TaggedRecordBuilderPlanning_OperatorApprovedStart -> COMPLETED
E4S-P6 -> CLOSED_AS_CONTRACT_DESIGN_READY
STATIC_VALIDATOR -> CREATED_AND_LOCAL_SMOKE_PASS
GOLDEN_SAMPLE_FIXTURE -> CREATED_AND_VALIDATED
LOCAL_RUNTIME_VALIDATION_REPORT -> CREATED_AND_LOCKED_TO_GITHUB
TAGGED_RECORD_BUILDER_PLAN -> CREATED
TAGGED_RECORD_BUILDER_IMPLEMENTATION -> NOT_STARTED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 12. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-I5_StaticRecordBuilderImplementation_OperatorApprovedStart
```

Unique next action, if approved:

```text
Create ulga/builders/build_e4s_p6_error_tagging_records.py
Create ulga/graph/e4s_p6_error_tagging_records.json
Create ulga/reports/e4s_p6_error_tagging_records_validation_report.json
```

I5 must use only approved static input records. I5 must not ingest source data, capture runtime learner answers, modify UI, mutate learner state, aggregate weak points, generate remediation exercises, or create adaptive recommendations.
