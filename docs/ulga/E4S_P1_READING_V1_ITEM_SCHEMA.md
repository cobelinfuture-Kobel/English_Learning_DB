# E4S P1 Reading V1 Item Schema Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Current Middle Task:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract
```

Current Small Task:

```text
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
```

This task defines the Reading V1 item schema conceptually. It defines the candidate item boundary, source trace fields, question / answer / evidence shape, level and situation metadata, review fields, blocked-output fields, and implementation expectations for the later machine-readable schema. It does not create the machine-readable JSON schema, generate Reading questions, build query helpers, build validators, create pilot candidates, extract source payloads, create learner-facing HTML, create worksheets, create learner events, create learner state, or promote source/content authority.

---

## 2. Mandatory Governance Readback

Governance source:

```text
docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
```

Governance result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
```

Predecessor state:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate -> COMPLETED
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan -> COMPLETED
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan -> COMPLETED
```

P1 task queue authorizes the current task as:

```text
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
Type = DesignScan / SchemaDesign
Deliverable = docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
May Implement = no
```

---

## 3. Task Boundary

Task type:

```text
DesignScan / ItemSchemaDesign
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
```

Forbidden files and paths:

```text
ulga/schemas/reading_v1_candidate.schema.json
tools/query_e4s_reading_v1_sources.py
tools/build_reading_v1_pilot_candidates.py
tools/validate_reading_v1_candidates.py
ulga/reports/reading_v1_pilot_summary.json
site HTML
student-facing Reading practice HTML
worksheet exports
large generated artifacts
source corpus payloads
learner event files
learner state files
learner profile files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Generated artifact policy:

```text
No generated Reading questions, Reading candidate JSON, machine-readable schema, validators, query helpers, learner-facing files, learner events, or large JSON artifacts are allowed in P1-S3.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. P1-S3 performs no source/content authority promotion.
```

---

## 4. Reading V1 Item Boundary

A Reading V1 item is a candidate practice unit that combines:

```text
source trace
reading passage reference
question model
answer model
evidence model
level / situation / skill metadata
validation status
manual review status
blocked-output status
```

A Reading V1 item is not:

```text
source authority
publicly redistributable source content
student-facing Reading HTML
worksheet output
learner answer record
learner progress record
learner state update
adaptive recommendation
mastery score
spaced review schedule
```

P1-S3 defines the schema shape only. Actual JSON schema implementation belongs to P1-S4.

---

## 5. Top-Level Candidate Object

Future Reading V1 candidate records should use a top-level object shaped like:

```text
reading_candidate_id
schema_version
phase_id
task_id
candidate_status
source_trace
source_policy
reading_payload_ref
question_model
answer_model
evidence_model
level_metadata
situation_metadata
skill_metadata
constraint_refs
validation_state
manual_review_state
blocked_output_state
audit_trail
```

Required principle:

```text
Every generated candidate must remain traceable to an eligible source_id and must explicitly preserve why it is not source authority or learner-facing output.
```

---

## 6. Field Group: Identity and Status

Required fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `reading_candidate_id` | string | yes | Stable deterministic candidate ID. |
| `schema_version` | string | yes | Future schema version, expected first value `READING_V1_CANDIDATE_SCHEMA_V1`. |
| `phase_id` | string | yes | Must be `E4S-P1_ReadingV1SourceGroundedPractice`. |
| `task_id` | string | yes | Task that produced or last materially changed the candidate. |
| `candidate_status` | enum | yes | Candidate lifecycle state. |

Allowed `candidate_status` values:

```text
design_only
candidate_generated
validator_pending
validator_passed
validator_failed
manual_review_pending
manual_review_passed
manual_review_failed
blocked
rejected
```

P1-S3 default expectation:

```text
candidate_status = design_only
```

---

## 7. Field Group: Source Trace

Required fields under `source_trace`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `source_id` | string | yes | Must reference an eligible manifest record. |
| `source_family` | string | yes | Must match manifest. |
| `authority_role` | string | yes | Must match manifest. |
| `source_path_ref` | string | yes | Reference path only; no payload copy. |
| `source_unit_ref` | string | conditional | Book / passage / page / sentence locator if available in later tasks. |
| `source_license_status` | string | yes | Must preserve manifest license status. |
| `source_review_status` | string | yes | Must preserve manifest review status. |
| `source_trace_required` | boolean | yes | Must be true for RAZ reading source. |
| `source_payload_copied` | boolean | yes | Must be false unless a future explicit task permits payload handling. |

Source trace rule:

```text
If source_id = RAZ_READING_CORPUS_A_T_CANDIDATE, authority_role must remain reading_corpus_candidate and direct_reading_authority must remain blocked.
```

---

## 8. Field Group: Source Policy

Required fields under `source_policy`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `allowed_use_snapshot` | string[] | yes | Allowed uses copied from manifest / contract. |
| `blocked_use_snapshot` | string[] | yes | Blocked uses copied from manifest / contract. |
| `promotion_rule` | string | yes | Manifest promotion rule. |
| `risk_flags` | string[] | yes | Manifest risk flags. |
| `public_distribution_allowed` | boolean | yes | Must be false for restricted/not-redistributable sources. |
| `learner_facing_allowed` | boolean | yes | Must remain false until output gate permits. |
| `authority_promotion_allowed` | boolean | yes | Must be false in P1 candidate records. |

Hard constraints:

```text
learner_facing_allowed = false by default
public_distribution_allowed = false for restricted_reference_only sources
authority_promotion_allowed = false for all P1 generated candidates
```

---

## 9. Field Group: Reading Payload Reference

Required fields under `reading_payload_ref`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `passage_ref` | string | yes | Trace/reference to passage or passage unit, not full payload unless later permitted. |
| `passage_level_ref` | string | optional | Raw source level label such as RAZ level. |
| `passage_title_ref` | string | optional | Source title reference if allowed by source policy. |
| `passage_excerpt_allowed` | boolean | yes | Whether a candidate may include text excerpt. Default false until policy permits. |
| `passage_excerpt` | string | conditional | Only allowed if excerpt policy and source license permit. |
| `content_hash` | string | optional | Future trace/audit hash if payload is handled by approved task. |

P1-S3 rule:

```text
P1-S3 defines the field only. It does not create passage_ref values or copy source payload.
```

---

## 10. Field Group: Question Model

Required fields under `question_model`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `question_id` | string | yes | Deterministic question ID within candidate. |
| `question_type` | enum | yes | Controlled Reading V1 question type. |
| `question_text` | string | yes | Candidate question text after future generation. |
| `question_language` | enum | yes | Expected first value `en`. |
| `question_level_band` | string | optional | Future normalized difficulty label. |
| `requires_evidence` | boolean | yes | Must be true for evidence-grounded reading items. |

Initial allowed `question_type` values:

```text
literal_who
literal_what
literal_where
literal_when
literal_yes_no
literal_count
literal_color
literal_action
sequence_order
main_idea_simple
vocabulary_in_context_basic
```

Deferred question types:

```text
inference
cause_effect
compare_contrast
author_purpose
open_ended_explanation
multi_source_reasoning
```

Deferred types require later validator and review policy before use.

---

## 11. Field Group: Answer Model

Required fields under `answer_model`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `answer_type` | enum | yes | Answer structure. |
| `expected_answer` | string or string[] | yes | Expected answer content. |
| `acceptable_answers` | string[] | optional | Alternative accepted answers. |
| `distractors` | string[] | conditional | Required for multiple-choice items if used. |
| `answer_source` | enum | yes | Where answer comes from. |
| `answer_evidence_ref` | string | yes | Link to evidence model. |

Allowed `answer_type` values:

```text
short_text
single_choice
multiple_choice
true_false
ordering
number
```

Allowed `answer_source` values:

```text
explicit_text_evidence
controlled_reference
manual_review_required
```

P1-S3 rule:

```text
Every answer must be evidence-linked. Free answers without evidence are not allowed in Reading V1 pilot candidates.
```

---

## 12. Field Group: Evidence Model

Required fields under `evidence_model`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `evidence_id` | string | yes | Stable evidence reference. |
| `evidence_type` | enum | yes | Evidence form. |
| `source_trace_ref` | string | yes | Backlink to source_trace. |
| `evidence_locator` | string | yes | Passage/page/sentence locator or equivalent. |
| `evidence_text_allowed` | boolean | yes | Whether evidence text may be copied. Default false. |
| `evidence_text` | string | conditional | Only if allowed by source policy. |
| `manual_review_required` | boolean | yes | Required for uncertain evidence or restricted text use. |

Allowed `evidence_type` values:

```text
source_locator_only
short_excerpt_allowed
metadata_reference
manual_review_note
```

Hard rule:

```text
Evidence must never be replaced by model assertion. If evidence cannot be traced, the item must fail validation later.
```

---

## 13. Field Group: Level Metadata

Required fields under `level_metadata`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `level_system` | string | yes | Source level system such as RAZ / CEFR / internal band. |
| `raw_level_code` | string | conditional | Raw source label if available. |
| `normalized_level_band` | string | optional | Internal routing band, not learner placement. |
| `level_claim_status` | string | yes | Claim/review status. |
| `level_evidence_role` | string | yes | Publisher claim / metadata / review / validator output. |
| `learner_placement_allowed` | boolean | yes | Must be false in P1. |

Hard rule:

```text
Level metadata is routing metadata only. It must not become learner placement, mastery score, or adaptive recommendation.
```

---

## 14. Field Group: Situation and Skill Metadata

Required fields under `situation_metadata`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `situation_domain` | string | yes | Domain/context family. |
| `situation_context` | string | optional | More specific context. |
| `communicative_function` | string | yes | Reading function or task intent. |
| `interaction_mode` | string | yes | Expected mode, usually `solo_reading`. |
| `situation_claim_status` | string | yes | Review status of situation label. |

Required fields under `skill_metadata`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `skill_fit` | string | yes | Expected value `reading_candidate`. |
| `target_phase` | string | yes | Expected value `E4S-P1_ReadingV1SourceGroundedPractice`. |
| `multi_skill_expansion_allowed` | boolean | yes | Must be false in P1 candidate records. |

---

## 15. Field Group: Constraint References

Required fields under `constraint_refs`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `wordlist_evidence_ref` | string | optional | Non-authority RAZ wordlist evidence reference. |
| `grammar_reference_ref` | string | optional | EGP reference metadata link. |
| `vocabulary_reference_ref` | string | optional | EVP reference metadata link. |
| `frequency_reference_ref` | string | optional | NGSL reference metadata link. |
| `chunk_reference_ref` | string | optional | Chunk reference metadata link. |

Hard rules:

```text
RAZ wordlist evidence cannot directly generate questions.
Reference-only sources cannot override primary reading source trace.
Constraint refs are not authority promotion.
```

---

## 16. Field Group: Validation and Review State

Required fields under `validation_state`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `schema_validation_status` | enum | yes | Schema validation result. |
| `source_trace_validation_status` | enum | yes | Source trace validation result. |
| `evidence_validation_status` | enum | yes | Evidence validation result. |
| `blocked_output_validation_status` | enum | yes | Confirms blocked outputs remain blocked. |
| `validator_version` | string | optional | Future validator version. |

Allowed validation status values:

```text
not_run
pass
pass_with_warnings
fail
blocked
```

Required fields under `manual_review_state`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `manual_review_required` | boolean | yes | Whether human review is required. |
| `manual_review_status` | enum | yes | Manual review state. |
| `review_notes` | string[] | optional | Notes for reviewer. |

Allowed `manual_review_status` values:

```text
not_required
pending
passed
failed
blocked
```

---

## 17. Field Group: Blocked Output State

Required fields under `blocked_output_state`:

| Field | Type | Required | Required Value in P1 Candidate |
|---|---|---:|---|
| `learner_facing_output_created` | boolean | yes | false until output gate permits |
| `student_html_created` | boolean | yes | false until S15/S16 permits |
| `worksheet_created` | boolean | yes | false until S15/S17 permits |
| `learner_event_created` | boolean | yes | false |
| `learner_state_updated` | boolean | yes | false |
| `adaptive_recommendation_created` | boolean | yes | false |
| `authority_promotion_performed` | boolean | yes | false |
| `large_scale_generation_performed` | boolean | yes | false |

Hard rule:

```text
Any true value in a blocked output field before its gate must fail future validation.
```

---

## 18. Audit Trail

Required fields under `audit_trail`:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `created_by_task` | string | yes | Task that created candidate. |
| `created_from_contracts` | string[] | yes | Contracts used. |
| `source_manifest_version_ref` | string | optional | Manifest version or hash reference. |
| `validator_report_ref` | string | optional | Future validator report reference. |
| `manual_review_ref` | string | optional | Future manual review reference. |
| `warnings` | string[] | yes | Candidate warnings. |
| `deferred_issues` | string[] | yes | Candidate deferred issues. |

---

## 19. Minimal Future Candidate Example Shape

This is an illustrative shape only, not a generated artifact:

```json
{
  "reading_candidate_id": "example_only_not_generated",
  "schema_version": "READING_V1_CANDIDATE_SCHEMA_V1",
  "phase_id": "E4S-P1_ReadingV1SourceGroundedPractice",
  "task_id": "future_task_id",
  "candidate_status": "design_only",
  "source_trace": {
    "source_id": "RAZ_READING_CORPUS_A_T_CANDIDATE",
    "source_family": "raz_reading_corpus",
    "authority_role": "reading_corpus_candidate",
    "source_trace_required": true,
    "source_payload_copied": false
  },
  "question_model": {
    "question_id": "example_question",
    "question_type": "literal_what",
    "question_language": "en",
    "requires_evidence": true
  },
  "blocked_output_state": {
    "learner_facing_output_created": false,
    "student_html_created": false,
    "worksheet_created": false,
    "learner_state_updated": false,
    "adaptive_recommendation_created": false,
    "authority_promotion_performed": false
  }
}
```

This example must not be copied as production data. P1-S4 must produce the actual machine-readable schema separately.

---

## 20. Blocked Outputs in P1-S3

P1-S3 explicitly blocks:

```text
machine-readable schema implementation
Reading V1 question generation
Reading candidate JSON generation
student-facing Reading HTML
worksheet generation
source payload extraction
large generated JSON artifacts
query helper implementation
validator implementation
pilot candidate builder implementation
learner event creation
learner state creation
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority promotion
```

---

## 21. Acceptance Gates for P1-S3

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in task queue | PASS | Section 2 |
| P1-M0 completion checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Forbidden files listed | PASS | Section 3 |
| Reading item boundary defined | PASS | Section 4 |
| Top-level candidate object shape defined | PASS | Section 5 |
| Identity/status fields defined | PASS | Section 6 |
| Source trace fields defined | PASS | Section 7 |
| Source policy fields defined | PASS | Section 8 |
| Reading payload reference fields defined | PASS | Section 9 |
| Question model fields defined | PASS | Section 10 |
| Answer model fields defined | PASS | Section 11 |
| Evidence model fields defined | PASS | Section 12 |
| Level metadata fields defined | PASS | Section 13 |
| Situation/skill metadata fields defined | PASS | Section 14 |
| Constraint refs defined | PASS | Section 15 |
| Validation/review state fields defined | PASS | Section 16 |
| Blocked output state defined | PASS | Section 17 |
| Audit trail defined | PASS | Section 18 |
| Example marked illustrative only | PASS | Section 19 |
| Blocked outputs recorded | PASS | Section 20 |
| Runtime impact avoided | PASS | Documentation only |
| Machine-readable schema avoided | PASS | No schema file |
| Query implementation avoided | PASS | No Python query helper |
| Pilot generation avoided | PASS | No candidate JSON |
| Validator implementation avoided | PASS | No validator code |
| Source payload extraction avoided | PASS | No payload copied |
| Learner state avoided | PASS | No learner files |
| Student-facing output avoided | PASS | No HTML / worksheet output |
| Promotion avoided | PASS | Design only |

---

## 22. Warning Register

```text
warning_id: E4S-P1-S3-WARN-001
severity: medium
classification: SCHEMA_NOT_IMPLEMENTED
message: This task defines schema design only. Machine-readable schema implementation belongs to P1-S4.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S3-WARN-002
severity: medium
classification: QUESTION_TYPES_INITIAL_ONLY
message: Initial question_type enum intentionally excludes inference and complex reasoning until later validator and review policy exist.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S3-WARN-003
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 23. Deferred Issues Register

```text
issue_id: E4S-P1-S3-DEFER-001
severity: high
affected_file_or_artifact: ulga/schemas/reading_v1_candidate.schema.json
classification: FUTURE_WORK
why_deferred: P1-S3 defines design only. P1-S4 must implement the machine-readable schema.
recommended_future_task: E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S3-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 validator contract
classification: FUTURE_WORK
why_deferred: Validator rules belong to P1-S5 after schema design and schema implementation are reconciled.
recommended_future_task: E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S3-DEFER-003
severity: high
affected_file_or_artifact: Reading V1 pilot candidate generation
classification: FUTURE_WORK
why_deferred: Pilot generation is blocked until source eligibility, item schema, machine-readable schema, validator contract, query design, and pilot policy exist.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation after required gates
blocks_current_task: no
```

---

## 24. Distance Vector

P0 state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0
```

P1 state after this task:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_SCHEMA_DESIGN_READY
```

Current task status:

```text
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan -> COMPLETED
```

P1-M1 remaining tasks:

```text
D_P1_M1 = 2 small tasks left
```

P1 remaining small-task distance:

```text
D_P1 = 15 small tasks left
```

Remaining P1-M1 tasks:

```text
E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation
E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan
```

---

## 25. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M1 = 2; D_P1 = 15
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation
DRIFT_RISK = low
DRIFT_REASON = Item schema is now designed, but machine-readable schema and all generation remain blocked until P1-S4/P1-S5/P1-S9 gates.
REQUIRED_ACTION = continue with P1-S4 only
```

---

## 26. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation
```

Only next allowed action:

```text
Create ulga/schemas/reading_v1_candidate.schema.json and any necessary schema tests, implementing only the machine-readable Reading V1 candidate schema from this design. Do not generate Reading questions, pilot candidates, source payloads, learner-facing output, learner events, learner state, adaptive recommendations, or authority promotion.
```

Stop here until the operator explicitly starts P1-S4.
