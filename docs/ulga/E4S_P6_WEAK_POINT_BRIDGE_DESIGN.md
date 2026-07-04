# E4S-P6-I6 Weak-point Bridge Design Only

## 1. Current State

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Closed Phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

Current Task:

```text
E4S-P6-I6_WeakPointBridgeDesignOnly_OperatorApprovedStart
```

Deliverable:

```text
docs/ulga/E4S_P6_WEAK_POINT_BRIDGE_DESIGN.md
```

Precondition evidence:

```text
E4S-P6-I5A_StaticRecordBuilderLocalSmokeQA_Readback -> PASS_LOCAL_RUNTIME_EVIDENCE_LOCKED
STATIC_RECORD_BUILDER -> CREATED_AND_LOCAL_SMOKE_PASS
TAGGED_RECORD_OUTPUT -> CREATED_AND_LOCAL_SMOKE_PASS
RECORDS_VALIDATION_REPORT -> CREATED_AND_LOCAL_SMOKE_PASS
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

This document is design-only. It does not implement a weak-point engine, learner-state mutation, scoring, adaptive recommendation, remediation scheduling, UI output, or runtime behavior.

---

## 2. Scope Lock

I6 may define:

```text
- evidence aggregation prerequisites
- minimum repeated-evidence rule
- boundary between diagnosis event and weak-point state
- future weak-point candidate fields
- validation prerequisites for a later bridge implementation
- stop conditions
```

I6 must not create or modify:

```text
- weak-point engine code
- learner state files
- scoring files
- adaptive recommendation logic
- remediation scheduler
- UI / dashboard files
- runtime answer capture
- source ingestion pipeline
- generated remediation exercises
```

---

## 3. Bridge Purpose

Future bridge purpose:

```text
Define how validated P6 error_diagnosis_records could later become weak-point evidence candidates without directly becoming learner weak-point state.
```

The bridge is a safety boundary between:

```text
validated error_diagnosis_record evidence
  -> candidate weak-point evidence bundle
  -> future reviewed weak-point state
```

Non-equivalence rules:

```text
learner_answer_record != weak_point
error_diagnosis_record != score
remediation_link_record != generated exercise
single wrong answer != stable weak point
```

---

## 4. Required Inputs for a Future Bridge

A future bridge may use only validated static records from:

```text
ulga/graph/e4s_p6_error_tagging_records.json
ulga/reports/e4s_p6_error_tagging_records_validation_report.json
```

Required validation conditions:

```text
validation_report.result must be PASS or explicitly approved PASS_WITH_WARNINGS.
record_shape_gate must be PASS.
link_integrity_gate must be PASS.
source_trace_gate must be PASS.
taxonomy_gate must be PASS.
compatibility_gate must be PASS.
non_generation_boundary_gate must be PASS.
```

Diagnosis safety rule:

```text
If diagnosis_safety_gate is PASS_WITH_WARNINGS, evidence may remain provisional but must not become stable weak-point state without repeated evidence or review.
```

Blocked inputs:

```text
- validator result = FAIL
- source_trace_gate = FAIL
- link_integrity_gate = FAIL
- unknown taxonomy values
- generated remediation content
- non-pseudonymous learner_ref
- missing source_evidence_ref for source-grounded Reading V1
```

---

## 5. Future Weak-point Evidence Candidate Shape

Potential future logical object:

```text
weak_point_evidence_candidate
```

Proposed fields:

| Field | Source | Rule |
|---|---|---|
| `candidate_id` | future bridge | Deterministic non-personal ID. |
| `learner_ref` | learner_answer_record | Pseudonymous only. |
| `concept_tag` | tagged_question_record.concept_tags | Controlled P6-S1 tag. |
| `skill_area` | tagged_question_record.skill_area | Controlled P6-S1 value. |
| `error_type` | error_diagnosis_record.error_type | Controlled P6-S1 value. |
| `error_detail` | error_diagnosis_record.error_detail | Controlled and compatible value. |
| `evidence_refs` | record IDs | References only. |
| `source_evidence_refs` | diagnosis records | Required for Reading V1. |
| `evidence_count` | future aggregation | Count of compatible evidence items. |
| `distinct_question_count` | future aggregation | Must exceed 1 for stable promotion. |
| `first_seen_at` | answer records | Earliest answer timestamp. |
| `last_seen_at` | answer records | Latest answer timestamp. |
| `status` | future bridge | `candidate_only`, `review_required`, or future approved state. |
| `confidence_band` | future bridge | Conservative band, not score. |
| `review_required` | future bridge | True when evidence is unsafe or insufficient. |
| `version` | future bridge | Future bridge schema version. |

I6 does not create this object or any output graph.

---

## 6. Minimum Repeated-evidence Rule

Minimum design rule:

```text
candidate_only:
  evidence_count >= 1
  distinct_question_count >= 1

review_required:
  evidence_count >= 1
  diagnosis_safety_gate = PASS_WITH_WARNINGS or REVIEW_REQUIRED

stable_weak_point_candidate:
  evidence_count >= 2
  distinct_question_count >= 2
  same learner_ref
  same or compatible concept_tag
  same or compatible error_detail
  validation gates PASS
  no generated remediation content
  no unknown taxonomy values
```

Hard stop:

```text
A single wrong answer can create evidence only. It cannot create stable weak-point state.
```

---

## 7. Diagnosis Event vs Weak-point State Boundary

`error_diagnosis_record` means:

```text
This answer produced evidence of a possible error pattern.
```

It does not mean:

```text
The learner has a stable weak point.
A score has been computed.
An adaptive path has been selected.
A remediation schedule has been assigned.
```

A future weak-point state would require a separate approved task for:

```text
- state schema
- promotion rules
- decay/recovery rules
- review policy
- exposure policy
- rollback policy
```

---

## 8. Evidence Grouping Strategy

Recommended primary grouping key:

```text
learner_ref + concept_tag + error_detail
```

Recommended secondary grouping key:

```text
learner_ref + skill_area + error_type + question_type
```

Controls:

```text
- Do not merge unrelated concept_tags.
- Do not merge grammar-only errors into reading-detail errors.
- Do not merge source_trace failures.
- Do not merge unknown_error into specific remediation paths.
- Preserve source_evidence_ref list for audit.
```

---

## 9. Confidence Bands, Not Scores

Allowed future bands:

```text
low_evidence
provisional_repeated_evidence
review_ready_candidate
```

Blocked fields:

```text
mastery_score
proficiency_score
adaptive_rank
next_best_exercise_score
learner_level_update
```

The band is for future review routing only, not learner-facing grading.

---

## 10. Remediation Boundary

Allowed:

```text
remediation_tag = practice_literal_what_questions
remediation_tag = vocabulary_food_words_review
remediation_tag = human_review_required
```

Blocked:

```text
generated_exercise_preview
auto_generated_question
assigned_next_exercise
scheduled_review_date
automatic_path_update
```

A remediation tag may be copied as a non-binding practice direction. It must not become generated content or an adaptive assignment.

---

## 11. Future Bridge Validation Gates

A future bridge implementation must pass:

```text
PASS - input validation report is PASS or approved PASS_WITH_WARNINGS.
PASS - all candidate evidence references resolve.
PASS - source_evidence_ref is preserved.
PASS - no generated remediation content appears.
PASS - learner_ref remains pseudonymous.
PASS - single evidence item is not promoted to stable weak point.
PASS - confidence band is not a score.
PASS - no learner state file is written.
PASS - no UI output is created.
PASS - no adaptive recommendation is created.
```

Blocked if:

```text
- unresolved record link exists.
- source_evidence_ref is missing for source-grounded Reading V1.
- generated content field appears.
- score field appears.
- learner state mutation is attempted.
```

---

## 12. Future Artifact Targets

I6 creates no artifacts beyond this document.

Potential future planning target, not approved by I6:

```text
docs/ulga/E4S_P6_WEAK_POINT_BRIDGE_IMPLEMENTATION_PLAN.md
```

Potential future implementation targets, not approved by I6:

```text
ulga/builders/build_e4s_p6_weak_point_candidates.py
ulga/graph/e4s_p6_weak_point_candidates.json
ulga/reports/e4s_p6_weak_point_candidates_validation_report.json
```

These require a separate operator-approved task.

---

## 13. Explicit Non-goals

I6 does not create:

```text
- weak-point engine
- weak-point candidate graph
- learner state file
- scoring artifact
- adaptive recommendation
- remediation scheduler
- UI / dashboard
- generated exercises
- runtime answer capture
- source ingestion
```

I6 does not modify runtime behavior.

---

## 14. Gate and Distance Update

Gate Metrics:

```text
PASS - I5A local smoke evidence verified as locked.
PASS - weak-point bridge design document created.
PASS - evidence aggregation prerequisites defined.
PASS - minimum repeated-evidence rule defined.
PASS - diagnosis-event versus weak-point-state boundary defined.
PASS - future weak-point candidate fields defined.
PASS - source-trace and privacy controls defined.
PASS - remediation boundary defined.
PASS - weak-point engine implementation blocked.
PASS - learner state mutation blocked.
PASS - scoring blocked.
PASS - adaptive recommendation blocked.
PASS - UI output blocked.
```

Distance Vector:

```text
E4S-P6-I6_WeakPointBridgeDesignOnly_OperatorApprovedStart -> COMPLETED
E4S-P6 -> CLOSED_AS_CONTRACT_DESIGN_READY
STATIC_VALIDATOR -> CREATED_AND_LOCAL_SMOKE_PASS
GOLDEN_SAMPLE_FIXTURE -> CREATED_AND_VALIDATED
LOCAL_RUNTIME_VALIDATION_REPORT -> CREATED_AND_LOCKED_TO_GITHUB
TAGGED_RECORD_BUILDER_PLAN -> CREATED
STATIC_RECORD_BUILDER -> CREATED_AND_LOCAL_SMOKE_PASS
TAGGED_RECORD_OUTPUT -> CREATED_AND_LOCAL_SMOKE_PASS
WEAK_POINT_BRIDGE_DESIGN -> CREATED
WEAK_POINT_ENGINE -> NOT_STARTED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
```

---

## 15. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-I7_PostImplementationTrackCloseoutReadinessCheck
```

Unique next action, if approved:

```text
Create docs/ulga/E4S_P6_POST_IMPLEMENTATION_TRACK_CLOSEOUT_READINESS_CHECK.md
```

I7 should inspect I0 through I6 and confirm whether the P6 post-closeout implementation track can close as:

```text
STATIC_ERROR_TAGGING_FOUNDATION_READY
```

I7 must not implement weak-point engine, learner state, scoring, UI, runtime answer capture, source ingestion, generated remediation exercises, or adaptive recommendation.
