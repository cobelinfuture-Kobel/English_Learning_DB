# E4S P1 Reading V1 Manual Review Queue Design Scan

## 1. Current State

```text
Epic: E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
Phase: E4S-P1_ReadingV1SourceGroundedPractice
Middle Task: E4S-P1-M4_ReadingValidatorAndQA
Small Task: E4S-P1-S14_ReadingV1_ManualReviewQueue_DesignScan
Deliverable: docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md
```

This task defines manual review queue expectations for Reading V1 validated pilot candidates. It is design-only. It does not create a machine-readable queue artifact, does not modify validator code, does not change candidate records, does not create learner-facing output, does not create learner state, does not create adaptive recommendations, does not create worksheet export, and does not upgrade source/content authority.

---

## 2. Governance and Queue Readback

Task queue evidence:

```text
E4S-P1-S12_ReadingV1_CandidateValidator_Implementation -> Implementation / ValidatorOnly
E4S-P1-S13_ReadingV1_CandidateValidationReport_ReadbackQA -> QA / Readback
E4S-P1-S14_ReadingV1_ManualReviewQueue_DesignScan -> DesignScan / ReviewQueue
```

P1-M4 exit gate:

```text
P1-M4 exits only when candidate validation exists and manual review expectations are defined.
```

Predecessor readback:

```text
candidate validation exists = PASS
validation report exists = PASS
validation report has no blocking issues = PASS
manual review expectations defined = this task
```

Readback result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
```

---

## 3. Task Boundary

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md
```

Files explicitly not changed by this task:

```text
tools/validate_reading_v1_candidates.py
ulga/reports/reading_v1_validation_report.json
ulga/reports/reading_v1_pilot_candidates.json
ulga/reports/reading_v1_manual_review_queue.json
student HTML
worksheet output
learner event files
learner state files
adaptive path files
source/content authority files
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE
```

---

## 4. Manual Review Queue Purpose

The manual review queue exists to decide whether each validated Reading V1 pilot candidate is suitable to move to the next review/output decision gate.

It may decide:

```text
candidate can remain in reviewed internal pilot pool
candidate requires source locator correction
candidate requires level metadata correction
candidate requires question/answer/evidence correction
candidate requires rejection from pilot pool
candidate may be considered by the later learner-facing output gate
```

It must not decide:

```text
candidate becomes learner-facing automatically
candidate becomes worksheet automatically
candidate becomes source/content authority
candidate updates learner state
candidate drives adaptive recommendations
candidate changes learner placement or mastery
candidate can copy restricted source text
```

---

## 5. Queue Item Shape

A future machine-readable manual review queue item should use this conceptual shape:

```text
review_queue_item_id
phase_id
task_id
candidate_id
candidate_artifact_ref
validation_report_ref
validator_status
validator_issue_refs
validator_warning_refs
review_priority
review_status
reviewer_fields
source_trace_review
payload_policy_review
question_review
answer_review
evidence_review
level_review
situation_skill_review
blocked_output_review
decision
handoff_gate
review_audit
```

P1-S14 does not create this JSON artifact. It defines the expected shape only.

---

## 6. Required Reviewer Fields

Future queue item reviewer fields:

| Field | Required | Meaning |
|---|---:|---|
| `reviewer_id` | conditional | Reviewer identity or operator handle if review has started. |
| `review_started_at` | conditional | Timestamp when manual review begins. |
| `review_completed_at` | conditional | Timestamp when review completes. |
| `review_round` | yes | Review iteration number. |
| `review_notes` | yes | Human-readable review notes. |
| `review_decision_reason` | conditional | Required when decision is not pending. |
| `review_evidence_refs` | yes | References to validation report, candidate artifact, and source trace. |

Privacy rule:

```text
Reviewer fields must not include learner private data or learner answer history.
```

---

## 7. Allowed Review Status Values

Allowed `review_status` values:

```text
not_started
pending
in_review
needs_revision
passed_internal_review
failed_review
blocked_by_policy
rejected
```

Initial queue status for current tiny pilot candidates:

```text
pending
```

No `review_status` value authorizes learner-facing output by itself.

---

## 8. Allowed Decision Values

Allowed `decision` values:

```text
pending
approve_for_internal_validated_pool
needs_metadata_revision
needs_evidence_locator_revision
needs_level_review
needs_question_answer_revision
reject_candidate
block_candidate
```

Meaning:

| Decision | Meaning | May go to learner-facing output? |
|---|---|---:|
| `approve_for_internal_validated_pool` | Candidate may remain in internal reviewed pool. | no |
| `needs_metadata_revision` | Source/situation/skill metadata needs correction. | no |
| `needs_evidence_locator_revision` | Evidence locator is insufficient. | no |
| `needs_level_review` | Level band/source level needs review. | no |
| `needs_question_answer_revision` | Question/answer/evidence linkage needs correction. | no |
| `reject_candidate` | Candidate should be removed from pilot pool. | no |
| `block_candidate` | Candidate is blocked by policy. | no |

Only P1-S15 can decide whether learner-facing output remains blocked or becomes explicitly approved.

---

## 9. Allowed Status Transitions

Allowed transitions:

```text
not_started -> pending
pending -> in_review
in_review -> needs_revision
in_review -> passed_internal_review
in_review -> failed_review
in_review -> blocked_by_policy
needs_revision -> pending
failed_review -> rejected
blocked_by_policy -> rejected
passed_internal_review -> output_gate_pending
```

`output_gate_pending` is not learner-facing approval. It only means the item may be considered by P1-S15.

Forbidden transitions:

```text
pending -> learner_facing_approved
passed_internal_review -> learner_facing_approved
passed_internal_review -> worksheet_approved
passed_internal_review -> authority_promoted
any_status -> learner_state_updated
any_status -> adaptive_recommendation_created
```

---

## 10. Review Dimensions

Every candidate must be reviewed across these dimensions:

```text
source trace correctness
source policy preservation
payload policy compliance
question type compliance
question text suitability
answer model suitability
evidence locator sufficiency
manual review warning resolution
level metadata review
situation and skill metadata review
blocked output state review
audit trail completeness
```

Current P1-S12 warnings that must be handled by queue:

```text
READING_V1_MANUAL_REVIEW_PENDING
READING_V1_LEVEL_BAND_UNKNOWN
```

---

## 11. Blocking Criteria

Manual review must block or reject a candidate if any of the following are found:

```text
source trace is missing or incorrect
source_id is not eligible for Reading V1
source payload was copied
passage excerpt is present without policy
evidence text is present without policy
evidence locator is missing or unusable
answer is not linked to evidence
question type is outside allowed Reading V1 list
question text depends on unavailable source payload
RAZ wordlist is treated as vocabulary authority
level metadata is used as learner placement
candidate expands beyond Reading skill
learner-facing output is created or implied
worksheet output is created or implied
learner event/state is created or implied
adaptive recommendation is created or implied
source/content authority upgrade is created or implied
audit trail is insufficient
```

Blocking review result:

```text
review_status = blocked_by_policy or failed_review
decision = block_candidate or reject_candidate
handoff_gate = blocked_before_output_gate
```

---

## 12. Pass Criteria

Manual review may pass a candidate into the internal validated pool only if:

```text
validator status is PASS or PASS_WITH_WARNINGS
no blocking validation issues exist
source trace is preserved
source policy remains conservative
source_payload_copied = false
passage_excerpt_allowed = false
evidence_text_allowed = false
evidence locator is sufficient for internal traceability
manual review notes explain remaining metadata-only limitations
level metadata is not used for learner placement
blocked_output_state fields remain false
audit trail is complete
```

Pass result:

```text
review_status = passed_internal_review
decision = approve_for_internal_validated_pool
handoff_gate = output_gate_pending
```

This still does not authorize learner-facing output.

---

## 13. Review Priority Rules

Priority values:

```text
P0_blocking_policy_risk
P1_evidence_or_source_trace_risk
P2_level_or_metadata_review
P3_normal_manual_review
```

Current tiny pilot priority expectation:

```text
P2_level_or_metadata_review
```

Reason:

```text
Validation report has no blocking issues, but candidates have manual review pending and unknown level band warnings.
```

---

## 14. Future Queue Output Contract

A future implementation may create a manual review queue artifact only if explicitly authorized by a later implementation task.

Expected path if authorized later:

```text
ulga/reports/reading_v1_manual_review_queue.json
```

Expected summary fields:

```text
schema_version
phase_id
task_id
source_validation_report_ref
candidate_count
queue_item_count
pending_count
in_review_count
passed_internal_review_count
failed_review_count
blocked_count
rejected_count
learner_facing_allowed
authority_upgrade_allowed
next_shortest_step
```

Required values:

```text
learner_facing_allowed = false
authority_upgrade_allowed = false
next_shortest_step = E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan
```

---

## 15. P1-M4 Exit Rule

P1-M4 exit gate requires:

```text
candidate validation exists
validation report exists
validator readback QA exists
manual review expectations are defined
```

After this task:

```text
E4S-P1-M4_ReadingValidatorAndQA -> COMPLETED
```

P1-M4 does not approve learner-facing output. It only confirms that validation and manual review expectations exist.

---

## 16. Acceptance Gates for P1-S14

| Gate | Result | Evidence |
|---|---:|---|
| Governance/task queue checked | PASS | Section 2 |
| P1-S13 validation readback inspected | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Manual review queue purpose defined | PASS | Section 4 |
| Queue item shape defined | PASS | Section 5 |
| Reviewer fields defined | PASS | Section 6 |
| Review status values defined | PASS | Section 7 |
| Decision values defined | PASS | Section 8 |
| Allowed transitions defined | PASS | Section 9 |
| Forbidden transitions defined | PASS | Section 9 |
| Review dimensions defined | PASS | Section 10 |
| Blocking criteria defined | PASS | Section 11 |
| Pass criteria defined | PASS | Section 12 |
| Review priority rules defined | PASS | Section 13 |
| Future queue output contract defined | PASS | Section 14 |
| P1-M4 exit rule defined | PASS | Section 15 |
| Actual queue artifact avoided | PASS | No queue JSON created |
| Learner-facing output avoided | PASS | Documentation only |
| Learner state avoided | PASS | Documentation only |
| Adaptive output avoided | PASS | Documentation only |
| Worksheet output avoided | PASS | Documentation only |
| Source/content authority upgrade avoided | PASS | Documentation only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 17. Known Warnings

```text
warning_id: E4S-P1-S14-WARN-001
severity: medium
classification: QUEUE_ARTIFACT_NOT_IMPLEMENTED
message: This task defines manual review queue expectations only. No machine-readable queue artifact is created.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S14-WARN-002
severity: medium
classification: LEARNER_FACING_OUTPUT_STILL_BLOCKED
message: Manual review design does not approve learner-facing output. P1-S15 must decide output gate status.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S14-WARN-003
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local unittest or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 18. Distance Vector

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0

E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_OUTPUT_GATE_READY
E4S-P1-S14_ReadingV1_ManualReviewQueue_DesignScan -> COMPLETED
E4S-P1-M4_ReadingValidatorAndQA -> COMPLETED

D_P1_M4 = 0 small tasks left
D_P1 = 4 small tasks left
```

Next middle task:

```text
E4S-P1-M5_LearnerFacingOutputDecisionGate
```

Next small task:

```text
E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan
```

---

## 19. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M4 = 0; D_P1 = 4
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Validation and manual review expectations are now defined, but learner-facing output remains blocked until P1-S15 decides the output gate.
REQUIRED_ACTION = continue with P1-S15 only
```

---

## 20. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_LEARNER_FACING_OUTPUT_GATE.md to decide whether learner-facing output remains blocked or receives explicit limited approval. Do not implement HTML, worksheet export, learner state, adaptive recommendations, or source/content authority upgrade in P1-S15.
```

Stop here until the operator explicitly starts P1-S15.
