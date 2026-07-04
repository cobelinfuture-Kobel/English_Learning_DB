# E4S-P6-S2 Error Tagging Record Schema Contract

## 1. Current State

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

Current Sub-task:

```text
E4S-P6-S2_ErrorTaggingRecordSchemaContract_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
- 重點任務排程.txt
- RAZ-AW-V1 Status Snapshot.txt
- 標籤化錯題分析.txt
```

External Permission:

```text
GitHub: APPROVED - read/write project files by API
Google Drive: APPROVED - read reference files/specs/datasets
```

Deliverable:

```text
docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
```

This deliverable defines record schemas only. It does not implement builders, validators, generated data, UI, learner mastery scoring, weak-point engine, or adaptive recommendation.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S2 defines the record contracts required to carry P6-S1 taxonomy values through the Phase 6 diagnostic chain:

```text
Question -> Question Tags -> Answer Record -> Error Tags -> Weak-point Summary -> Remediation Tags
```

P6-S2 defines these records:

```text
tagged_question_record
learner_answer_record
error_diagnosis_record
remediation_link_record
```

P6-S2 may define:

```text
- required fields
- optional fields
- field meanings
- controlled-value references
- id naming rules
- cross-record key links
- source trace requirements
- evidence and confidence boundaries
```

P6-S2 must not implement:

```text
- Python builder
- Python validator
- JSON output generation
- learner profile update
- weak-point aggregation engine
- remediation content generator
- UI / HTML
- adaptive recommendation
```

### 2.2 Record Design Principles

The record schema must preserve separation between:

```text
1. what the question tests
2. how the learner answered
3. why the answer may be wrong
4. what practice direction is linked
```

A wrong answer is an evidence item, not a final mastery conclusion.

Therefore:

```text
learner_answer_record != weak_point
error_diagnosis_record != mastery_score
remediation_link_record != generated exercise
```

### 2.3 Canonical ID Rules

All generated IDs must use stable prefixes and zero-padded counters or deterministic source-derived suffixes.

Recommended prefixes:

| Record | Prefix |
|---|---|
| tagged_question_record | `TQ_` |
| learner_answer_record | `LA_` |
| error_diagnosis_record | `ED_` |
| remediation_link_record | `RL_` |

Examples:

```text
TQ_RV1_000001
LA_RV1_000001
ED_RV1_000001
RL_RV1_000001
```

Rules:

```text
- IDs must not contain learner names.
- IDs must not encode private personal information.
- IDs must be stable enough for cross-file linking.
- If source-derived IDs are used, the derivation rule must be documented by a later implementation task.
```

---

## 3. Record Schemas

### 3.1 tagged_question_record

Purpose:

```text
Represent a question after it has been tagged with controlled taxonomy values.
```

Required fields:

| Field | Type | Rule |
|---|---|---|
| `tagged_question_id` | string | Required. Prefix `TQ_`. |
| `question_id` | string | Required. Links to source question package. |
| `source_type` | string | Required. Example: `raz`, `cambridge`, `school_exam`, `workbook`, `custom_generated`. |
| `source_unit_id` | string | Required when available. Links to reading/source unit. |
| `level` | string | Required. Example: `pre_a1`, `a1`, `a2`, `raz_a`, `raz_b`. |
| `question_type` | string | Required. Must use P6-S1 controlled values. |
| `skill_area` | string | Required. Must use P6-S1 controlled values. |
| `concept_tags` | array[string] | Required. At least one controlled concept tag. |
| `cognitive_skill` | string | Required. Must use P6-S1 controlled values. |
| `correct_answer` | string or array | Required. Canonical answer model reference or expected answer. |
| `source_evidence_ref` | string or array | Required for source-grounded Reading V1. |
| `taxonomy_version` | string | Required. Example: `p6_s1_v1`. |
| `schema_version` | string | Required. Example: `p6_s2_v1`. |

Optional fields:

| Field | Type | Rule |
|---|---|---|
| `secondary_skill_areas` | array[string] | Optional. Future use only. |
| `difficulty_hint` | string | Optional. Informational only, not mastery scoring. |
| `answer_format` | string | Optional. Example: `single_word`, `sentence`, `choice_id`, `ordered_list`. |
| `evidence_sentence_ids` | array[string] | Optional. For sentence-level evidence trace. |
| `notes` | array[string] | Optional. Non-canonical notes only. |

Example:

```json
{
  "tagged_question_id": "TQ_RV1_000001",
  "question_id": "Q_RV1_HOME_000001",
  "source_type": "raz",
  "source_unit_id": "RAZ_A_PAGE_UNIT_000001",
  "level": "raz_a",
  "question_type": "literal_what",
  "skill_area": "reading",
  "concept_tags": ["literal_comprehension", "detail_finding", "what_reference"],
  "cognitive_skill": "locate_information",
  "correct_answer": "dog",
  "source_evidence_ref": "RAZ_A_SENT_000001",
  "taxonomy_version": "p6_s1_v1",
  "schema_version": "p6_s2_v1"
}
```

Rules:

```text
- A tagged_question_record does not include learner answer data.
- A tagged_question_record does not include diagnosis.
- It only describes the question and what it tests.
```

### 3.2 learner_answer_record

Purpose:

```text
Represent one learner answer attempt against one tagged question.
```

Required fields:

| Field | Type | Rule |
|---|---|---|
| `learner_answer_id` | string | Required. Prefix `LA_`. |
| `tagged_question_id` | string | Required. Links to tagged_question_record. |
| `question_id` | string | Required. Redundant link for traceability. |
| `learner_ref` | string | Required. Pseudonymous learner reference, not real name. |
| `attempt_id` | string | Required. Groups one practice session or package attempt. |
| `attempt_index` | integer | Required. 1-based attempt count for the same question within the attempt scope. |
| `learner_answer` | string or array | Required. Raw or normalized learner answer. |
| `answer_format` | string | Required. Must match expected answer format when available. |
| `is_correct` | boolean | Required. Result from answer model or review. |
| `scoring_method` | string | Required. Example: `exact_match`, `normalized_match`, `human_review`, `manual_import`. |
| `answered_at` | string | Required if available. ISO-like timestamp or source timestamp. |
| `schema_version` | string | Required. Example: `p6_s2_v1`. |

Optional fields:

| Field | Type | Rule |
|---|---|---|
| `normalized_learner_answer` | string or array | Optional. Used by later validators. |
| `response_time_ms` | integer | Optional. Not used for diagnosis in P6-S2. |
| `attempt_context_ref` | string | Optional. Links to practice package/session. |
| `review_status` | string | Optional. Example: `auto_scored`, `human_reviewed`, `needs_review`. |
| `reviewer_note` | string | Optional. Non-canonical note. |

Example:

```json
{
  "learner_answer_id": "LA_RV1_000001",
  "tagged_question_id": "TQ_RV1_000001",
  "question_id": "Q_RV1_HOME_000001",
  "learner_ref": "learner_001",
  "attempt_id": "ATTEMPT_RV1_20260704_000001",
  "attempt_index": 1,
  "learner_answer": "cat",
  "answer_format": "single_word",
  "is_correct": false,
  "scoring_method": "exact_match",
  "answered_at": "2026-07-04T00:00:00+08:00",
  "schema_version": "p6_s2_v1"
}
```

Rules:

```text
- A learner_answer_record records what happened.
- It does not decide the reason for the error.
- It must not store the learner's real name.
- It must be linkable to one tagged_question_record.
```

### 3.3 error_diagnosis_record

Purpose:

```text
Represent the diagnosis attached to an incorrect or review-needed learner answer.
```

Required fields:

| Field | Type | Rule |
|---|---|---|
| `error_diagnosis_id` | string | Required. Prefix `ED_`. |
| `learner_answer_id` | string | Required. Links to learner_answer_record. |
| `tagged_question_id` | string | Required. Links to tagged_question_record. |
| `question_id` | string | Required. Redundant traceability link. |
| `is_correct` | boolean | Required. Usually false; if true, diagnosis should normally not exist. |
| `error_type` | string | Required for incorrect or review-needed answers. Must use P6-S1 controlled values. |
| `error_detail` | string | Required. Must use P6-S1 controlled values. |
| `diagnosis_confidence` | string | Required. Controlled value: `low`, `medium`, `high`, `human_confirmed`. |
| `diagnosis_basis` | array[string] | Required. Evidence basis for the diagnosis. |
| `source_evidence_ref` | string or array | Required for Reading V1. |
| `taxonomy_version` | string | Required. Example: `p6_s1_v1`. |
| `schema_version` | string | Required. Example: `p6_s2_v1`. |

Optional fields:

| Field | Type | Rule |
|---|---|---|
| `conflicting_signals` | array[string] | Optional. Records why confidence is not high. |
| `requires_human_review` | boolean | Optional. Required true when error_detail is `needs_human_review`. |
| `diagnosed_at` | string | Optional. Timestamp. |
| `diagnosis_method` | string | Optional. Example: `rule_based`, `human_review`, `manual_import`. |

Allowed `diagnosis_basis` values:

```text
tagged_question_taxonomy
learner_answer_mismatch
source_evidence_mismatch
answer_format_mismatch
repeated_same_error
human_review_note
not_enough_evidence
```

Example:

```json
{
  "error_diagnosis_id": "ED_RV1_000001",
  "learner_answer_id": "LA_RV1_000001",
  "tagged_question_id": "TQ_RV1_000001",
  "question_id": "Q_RV1_HOME_000001",
  "is_correct": false,
  "error_type": "reading_detail_error",
  "error_detail": "missed_explicit_detail",
  "diagnosis_confidence": "medium",
  "diagnosis_basis": ["tagged_question_taxonomy", "learner_answer_mismatch", "source_evidence_mismatch"],
  "source_evidence_ref": "RAZ_A_SENT_000001",
  "taxonomy_version": "p6_s1_v1",
  "schema_version": "p6_s2_v1"
}
```

Rules:

```text
- `concept_error` should not be assigned with high confidence from one wrong answer.
- `unknown_error` + `needs_human_review` is valid when evidence is insufficient.
- Diagnosis is attached to an answer event, not directly to a learner profile.
- Aggregated weak-point state belongs to a later task.
```

### 3.4 remediation_link_record

Purpose:

```text
Represent the practice direction linked to an error diagnosis.
```

Required fields:

| Field | Type | Rule |
|---|---|---|
| `remediation_link_id` | string | Required. Prefix `RL_`. |
| `error_diagnosis_id` | string | Required. Links to error_diagnosis_record. |
| `learner_answer_id` | string | Required. Links to learner_answer_record. |
| `tagged_question_id` | string | Required. Links to tagged_question_record. |
| `remediation_tag` | string | Required. Must use P6-S1 controlled values. |
| `remediation_priority` | string | Required. Controlled value: `low`, `normal`, `high`, `review_required`. |
| `remediation_basis` | array[string] | Required. Why this remediation was selected. |
| `schema_version` | string | Required. Example: `p6_s2_v1`. |

Optional fields:

| Field | Type | Rule |
|---|---|---|
| `suggested_content_query` | object | Optional. Query hint only; not generated content. |
| `blocked_reason` | string | Optional. Required when no remediation can be assigned. |
| `review_status` | string | Optional. Example: `auto_linked`, `human_review_required`, `deferred`. |

Allowed `remediation_basis` values:

```text
error_type_mapping
error_detail_mapping
concept_tag_mapping
question_type_mapping
human_review
fallback_no_safe_mapping
```

Example:

```json
{
  "remediation_link_id": "RL_RV1_000001",
  "error_diagnosis_id": "ED_RV1_000001",
  "learner_answer_id": "LA_RV1_000001",
  "tagged_question_id": "TQ_RV1_000001",
  "remediation_tag": "practice_reading_detail_questions",
  "remediation_priority": "normal",
  "remediation_basis": ["error_type_mapping", "error_detail_mapping"],
  "schema_version": "p6_s2_v1"
}
```

Rules:

```text
- A remediation_link_record does not create the remedial exercise.
- It only links diagnosis to a practice direction.
- If diagnosis is unsafe, use `human_review_required` or `no_remediation_assigned` from P6-S1.
```

---

## 4. Cross-record Link Contract

### 4.1 Required Link Chain

The minimal valid link chain is:

```text
tagged_question_record.tagged_question_id
  -> learner_answer_record.tagged_question_id
  -> error_diagnosis_record.learner_answer_id
  -> remediation_link_record.error_diagnosis_id
```

### 4.2 Source Trace Chain

For Reading V1, the trace chain must preserve:

```text
source_unit_id
source_evidence_ref
question_id
tagged_question_id
learner_answer_id
error_diagnosis_id
remediation_link_id
```

### 4.3 Required Cardinality

```text
One tagged_question_record may have many learner_answer_records.
One learner_answer_record may have zero or one error_diagnosis_record.
One error_diagnosis_record may have zero or one remediation_link_record in P6-S2.
```

Future versions may allow multiple remediation links, but P6-S2 keeps one primary remediation link to avoid over-expansion.

---

## 5. Schema Compatibility Rules

### 5.1 Incorrect Answer Minimum

For an incorrect answer to be P6-compatible, the system must be able to produce or carry:

```text
learner_answer_id
tagged_question_id
question_id
learner_answer
is_correct = false
error_type
error_detail
remediation_tag
source_evidence_ref
```

### 5.2 Correct Answer Minimum

For a correct answer, P6-S2 requires only:

```text
learner_answer_record
```

No error_diagnosis_record is required.

### 5.3 Review-needed Answer Minimum

If the answer cannot be classified safely:

```text
error_type = unknown_error
error_detail = needs_human_review
remediation_tag = human_review_required
diagnosis_confidence = low
requires_human_review = true
```

### 5.4 Version Fields

Every record must include:

```text
schema_version = p6_s2_v1
```

Records using taxonomy values must include:

```text
taxonomy_version = p6_s1_v1
```

---

## 6. Explicit Non-goals

P6-S2 does not create:

```text
- actual JSON data files
- validators
- scripts
- UI forms
- weak-point summaries
- learner state updates
- remediation exercise generation
- adaptive recommendations
```

Any future implementation must treat this file as a contract, not as executed runtime behavior.

---

## 7. Gate and Distance Update

Gate Metrics:

```text
PASS - tagged_question_record schema defined
PASS - learner_answer_record schema defined
PASS - error_diagnosis_record schema defined
PASS - remediation_link_record schema defined
PASS - cross-record link chain defined
PASS - source trace chain defined
PASS - versioning requirement defined
PASS - runtime/code untouched
PASS - validator implementation deferred
PASS - adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 6 sub-tasks left after P6-S2
E4S-P6-S2_ErrorTaggingRecordSchemaContract_DesignScan -> COMPLETED
E4S-P6 -> RECORD_SCHEMA_CONTRACT_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 8. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S3_ErrorTaggingCompatibilityMatrix_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md
```

P6-S3 should define compatibility rules between:

```text
- question_type
- skill_area
- concept_tags
- cognitive_skill
- error_type
- error_detail
- remediation_tag
```

P6-S3 must not implement builders, validators, UI, generated data, learner mastery scoring, weak-point aggregation, or adaptive recommendation.
