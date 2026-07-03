# E4S P1 Reading Question Package Contract Design Scan

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
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
```

Preceding Gate:

```text
E4S-P1-S0_ReadingV1GoalAndProgressTracker_DesignScan -> COMPLETED
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P1_READING_V1_GOAL_AND_PROGRESS_TRACKER.md
2. docs/status/E4S_P0_CLOSEOUT_SOURCE_AUTHORITY_FOUNDATION_READBACK.md
3. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
4. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
5. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
6. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
7. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
8. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
```

This task defines the Reading V1 question package contract only. It does not create a real sample package, source extraction, Reading HTML, answer checker, evidence display runtime, generator code, validator code, learner state, adaptive recommendation, student-facing output, or promotion artifact.

---

## 2. Task Boundary

Task:

```text
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
```

Scope:

```text
Define the contract for a Reading V1 candidate question package so later P1 tasks can create, render, check, display evidence for, generate, validate, and read back the package without changing the package semantics.
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md
```

Forbidden outputs in this sub-task:

```text
sample Reading package JSON
student-facing Reading HTML
site HTML
runtime code
answer checker code
evidence display code
generator code
validator code
test code
source corpus payload extraction
source payload redistribution
learner state
learner profile
adaptive scheduler
assessment expansion
writing output
dialogue output
listening output
promotion artifact
```

Artifact class:

```text
design_contract_only
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This file is a contract, not authority promotion and not learner-facing publication.
```

Stop condition:

```text
Stop after package schema, item schema, source trace schema, evidence schema, answer model schema, validator-readable fields, invalid examples, acceptance gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Contract Goal

Reading V1 question packages must be small, source-grounded, traceable, validator-readable, and blocked from learner-facing use until later gates pass.

The contract exists to answer:

```text
Can a future Reading V1 package represent a bounded set of source-grounded reading items with explicit source trace, evidence, answer model, and validation fields?
```

The contract must not answer:

```text
Can the package be shown to a learner?
Can the package be auto-promoted?
Can the package diagnose learner weakness?
Can the package select a learner's next lesson?
Can the package redistribute restricted source text?
```

---

## 4. Package Contract Overview

Canonical package class:

```text
reading_practice_candidate_package
```

Canonical schema version:

```text
E4S_READING_QUESTION_PACKAGE_V1
```

Minimum object shape:

```json
{
  "schema_version": "E4S_READING_QUESTION_PACKAGE_V1",
  "package_id": "string",
  "package_version": "string",
  "package_class": "reading_practice_candidate_package",
  "target_phase": "E4S-P1_ReadingV1SourceGroundedPractice",
  "created_by_task": "string",
  "source_manifest_refs": [],
  "package_scope": {},
  "items": [],
  "review_status": "not_reviewed",
  "promotion_status": "not_promoted",
  "learner_facing_status": "blocked_until_validator_pass",
  "blocked_use": [],
  "validator_summary": {},
  "audit": {}
}
```

This JSON is a contract example only. It is not a real package artifact.

---

## 5. Package Required Fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `schema_version` | string | yes | Must equal `E4S_READING_QUESTION_PACKAGE_V1`. |
| `package_id` | string | yes | Stable package identifier. |
| `package_version` | string | yes | Contract-compatible package version. |
| `package_class` | string | yes | Must equal `reading_practice_candidate_package`. |
| `target_phase` | string | yes | Must equal `E4S-P1_ReadingV1SourceGroundedPractice`. |
| `created_by_task` | string | yes | Task ID that created the package. |
| `source_manifest_refs` | array | yes | References to approved manifest source records. |
| `package_scope` | object | yes | Level, skill, item-type, and source boundary. |
| `items` | array | yes | Reading item list. |
| `review_status` | enum | yes | Human / validator review status. |
| `promotion_status` | enum | yes | Must default to `not_promoted`. |
| `learner_facing_status` | enum | yes | Must default to blocked. |
| `blocked_use` | array | yes | Explicit prohibited use list. |
| `validator_summary` | object | yes | Validator-readable summary, even before validator implementation. |
| `audit` | object | yes | Build / review / trace metadata. |

---

## 6. Package Field Rules

### 6.1 schema_version

Allowed value:

```text
E4S_READING_QUESTION_PACKAGE_V1
```

Invalid values:

```text
empty string
unknown version
future version without migration contract
```

### 6.2 package_id

Required pattern:

```text
reading_pkg_[source_family]_[level_or_band]_[sequence]
```

Example pattern only:

```text
reading_pkg_raz_aa_0001
```

Rules:

```text
lowercase only
ASCII letters, numbers, underscore only
must be stable across rebuilds if source inputs and policy are unchanged
must not contain learner name
must not contain private account identifier
```

### 6.3 package_version

Initial allowed value:

```text
v1
```

Future versions require a migration note.

### 6.4 source_manifest_refs

Each reference must point to a source record approved for Reading candidate use.

Minimum shape:

```json
{
  "source_id": "string",
  "source_family": "string",
  "manifest_schema_version": "E4S_SOURCE_MANIFEST_V1",
  "manifest_path": "ulga/graph/e4s_source_manifest.json",
  "allowed_use_ref": "reading_candidate_package"
}
```

Rules:

```text
At least one source_manifest_ref is required.
Every item.source_trace.source_id must match one package-level source_manifest_refs.source_id.
No package may reference a blocked source as Reading authority.
No package may embed restricted source payload beyond the allowed evidence policy.
```

### 6.5 package_scope

Minimum shape:

```json
{
  "skill": "reading",
  "supported_item_types": [],
  "level_claim_policy": "source_claim_only_until_validated",
  "source_unit_policy": "single_source_unit_or_explicit_multi_unit",
  "max_items": 10,
  "requires_direct_evidence": true,
  "allows_inference_items": false
}
```

Rules:

```text
skill must be reading.
supported_item_types must be a subset of the six Reading V1 item types.
requires_direct_evidence must be true.
allows_inference_items must be false for V1.
max_items should remain small for V1 candidate packages.
```

### 6.6 review_status

Allowed values:

```text
not_reviewed
validator_reviewed
human_reviewed
blocked
```

Default:

```text
not_reviewed
```

### 6.7 promotion_status

Allowed values:

```text
not_promoted
blocked
```

Default and required for P1:

```text
not_promoted
```

Forbidden for P1:

```text
promoted
final_authority
public
```

### 6.8 learner_facing_status

Allowed values:

```text
blocked_until_validator_pass
blocked_until_human_review
blocked
```

Default:

```text
blocked_until_validator_pass
```

Forbidden for P1-S1:

```text
learner_ready
published
public
```

---

## 7. Supported Item Types

Reading V1 supports exactly these six item types:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

No other item types are allowed in V1 package contract.

Explicitly blocked item types:

```text
why_inference
how_inference
main_idea
author_purpose
opinion
prediction
free_response
writing_prompt
speaking_prompt
listening_prompt
grammar_transformation
multi_source_synthesis
learner_diagnosis
```

---

## 8. Reading Item Schema

Canonical item shape:

```json
{
  "item_id": "string",
  "item_type": "literal_who",
  "prompt": {},
  "source_trace": {},
  "source_evidence": {},
  "answer_model": {},
  "validator_fields": {},
  "blocked_use": [],
  "review_status": "not_reviewed"
}
```

This JSON is a contract example only. It is not a real Reading item artifact.

Required item fields:

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `item_id` | string | yes | Stable item identifier within package. |
| `item_type` | enum | yes | One of the six Reading V1 item types. |
| `prompt` | object | yes | Prompt text and display metadata. |
| `source_trace` | object | yes | Source reference down to source unit / sentence. |
| `source_evidence` | object | yes | Direct evidence supporting the answer. |
| `answer_model` | object | yes | Canonical answer and scoring semantics. |
| `validator_fields` | object | yes | Validator-readable control flags. |
| `blocked_use` | array | yes | Item-level prohibited uses. |
| `review_status` | enum | yes | Default `not_reviewed`. |

---

## 9. Item ID Rules

Required pattern:

```text
[item_type]_[source_unit_id]_[sequence]
```

Example pattern only:

```text
literal_who_page001_001
```

Rules:

```text
item_id must be unique within a package.
item_id must be deterministic for the same source unit and item policy.
item_id must not contain learner identity.
item_id must not contain private source payload.
```

---

## 10. Prompt Schema

Minimum shape:

```json
{
  "prompt_text": "string",
  "prompt_language": "en",
  "display_mode": "text_only",
  "choices": [],
  "requires_audio": false,
  "requires_image": false
}
```

Rules:

```text
prompt_text is required.
prompt_language must be en for Reading V1 initial package.
display_mode must be text_only unless later evidence-display policy allows image trace.
choices may be empty for non-multiple-choice models.
requires_audio must be false.
requires_image must be false for V1 unless image evidence is separately approved in a future task.
```

Blocked prompt behavior:

```text
No prompt may require learner background knowledge.
No prompt may require opinion or prediction.
No prompt may ask the learner to write a paragraph.
No prompt may include hidden source payload beyond allowed evidence policy.
```

---

## 11. Source Trace Schema

Minimum shape:

```json
{
  "source_id": "string",
  "source_family": "string",
  "source_manifest_ref": "string",
  "source_path_or_reference": "string",
  "source_level_claim": "string",
  "source_level_claim_status": "source_claim_only",
  "source_unit_id": "string",
  "source_unit_type": "sentence",
  "source_sentence_ids": [],
  "source_page_or_location": "string"
}
```

Required rules:

```text
source_id must match one package-level source_manifest_refs.source_id.
source_family must match the source manifest record.
source_manifest_ref must point to the manifest artifact, not arbitrary text.
source_level_claim_status must preserve whether the level is only source-claimed or validated.
source_unit_id is required for every item.
source_sentence_ids is required for sentence-level evidence.
source_page_or_location is required when page or location exists.
```

Allowed source_unit_type values:

```text
sentence
page
passage
wordlist_entry
metadata_record
```

Blocked trace behavior:

```text
No item may have missing source_trace.
No item may point to a status artifact as Reading source.
No item may point to generated content as source authority.
No item may point to a source outside the package-level source_manifest_refs.
```

---

## 12. Source Evidence Schema

Minimum shape:

```json
{
  "evidence_text": "string",
  "evidence_span": "string",
  "answer_span": "string",
  "source_sentence_quote_policy": "limited_quote_for_validation",
  "evidence_is_direct": true,
  "inference_required": false,
  "evidence_transform": "none",
  "copyright_policy": "no_source_payload_redistribution"
}
```

Required rules:

```text
evidence_text is required unless a later source policy forbids storing quoted evidence.
evidence_span is required when source text span is available.
answer_span is required for literal_who, literal_what, literal_where, and cloze_vocabulary.
evidence_is_direct must be true for V1.
inference_required must be false for V1.
evidence_transform must be none unless normalization is explicitly recorded.
copyright_policy must block source payload redistribution.
```

Allowed source_sentence_quote_policy values:

```text
limited_quote_for_validation
span_reference_only
no_quote_reference_only
```

Blocked evidence behavior:

```text
No evidence may be invented.
No evidence may come from unreviewed generated content.
No evidence may require external world knowledge.
No evidence may contradict answer_model.canonical_answer.
No evidence may redistribute restricted source payload beyond the allowed quote policy.
```

---

## 13. Answer Model Schema

Minimum shape:

```json
{
  "answer_type": "short_text",
  "canonical_answer": "string",
  "accepted_answers": [],
  "case_sensitive": false,
  "order_sensitive": false,
  "exact_match_required": true,
  "scoring_policy": "exact_or_accepted_match",
  "distractors": []
}
```

Required rules:

```text
answer_type is required.
canonical_answer is required for all V1 item types.
accepted_answers must include only source-supported alternatives.
case_sensitive should default to false.
order_sensitive must match item_type.
exact_match_required must be explicit.
scoring_policy must be validator-readable.
distractors are optional and must not create ambiguity.
```

Allowed answer_type values:

```text
short_text
boolean
ordered_list
cloze_text
multiple_choice
```

Allowed scoring_policy values:

```text
exact_or_accepted_match
boolean_match
ordered_list_exact
cloze_exact
choice_key_match
```

Item-type answer model requirements:

| item_type | answer_type | required scoring_policy | order_sensitive |
|---|---|---|---:|
| `literal_who` | `short_text` or `multiple_choice` | `exact_or_accepted_match` or `choice_key_match` | false |
| `literal_what` | `short_text` or `multiple_choice` | `exact_or_accepted_match` or `choice_key_match` | false |
| `literal_where` | `short_text` or `multiple_choice` | `exact_or_accepted_match` or `choice_key_match` | false |
| `true_false` | `boolean` | `boolean_match` | false |
| `sentence_ordering` | `ordered_list` | `ordered_list_exact` | true |
| `cloze_vocabulary` | `cloze_text` | `cloze_exact` | false |

Blocked answer model behavior:

```text
No answer model may depend on learner state.
No answer model may require human interpretation for correctness.
No answer model may contain unsupported accepted answers.
No answer model may contain a correct answer not found in source evidence for literal/cloze items.
```

---

## 14. Validator-Readable Fields

Minimum shape:

```json
{
  "item_type_allowed": true,
  "source_trace_present": true,
  "evidence_present": true,
  "answer_model_present": true,
  "evidence_is_direct": true,
  "inference_required": false,
  "blocked_scope_absent": true,
  "learner_state_absent": true,
  "promotion_status_not_promoted": true,
  "source_family_allowed_for_reading": true,
  "status_artifact_not_used_as_source": true,
  "generated_content_not_used_as_authority": true
}
```

Required rules:

```text
Every field must be explicit boolean.
Missing validator fields must be treated as validation failure in P1-S7.
Any false value in blocking fields should block learner-facing use.
Validator fields are declarative in P1-S1; executable validation belongs to P1-S7.
```

Blocking fields:

```text
item_type_allowed
source_trace_present
evidence_present
answer_model_present
evidence_is_direct
blocked_scope_absent
learner_state_absent
promotion_status_not_promoted
source_family_allowed_for_reading
status_artifact_not_used_as_source
generated_content_not_used_as_authority
```

---

## 15. blocked_use Requirements

Every package and item must carry explicit blocked uses.

Minimum package-level blocked_use:

```text
learner_facing_publication
final_authority_promotion
adaptive_recommendation
learner_diagnosis
source_payload_redistribution
listening_output
speaking_output
writing_output
```

Minimum item-level blocked_use:

```text
learner_facing_publication_without_validator
promotion_without_review
adaptive_diagnosis
unsupported_item_type_expansion
```

---

## 16. Package Audit Schema

Minimum shape:

```json
{
  "created_by_task": "E4S-P1-S2_ReadingSampleQuestionPackage_Implementation",
  "contract_source": "docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md",
  "source_manifest_path": "ulga/graph/e4s_source_manifest.json",
  "build_mode": "static_offline_candidate",
  "runtime_used": false,
  "learner_state_used": false,
  "promotion_performed": false
}
```

Required rules:

```text
runtime_used must be false for V1 candidate build.
learner_state_used must be false.
promotion_performed must be false.
build_mode must not imply live learner-facing publication.
```

---

## 17. Invalid Package Examples

These are contract-level invalid examples only. They are not package artifacts.

### 17.1 Missing source trace

Invalid because each item must have source trace.

```json
{
  "item_id": "literal_what_page001_001",
  "item_type": "literal_what",
  "prompt": {"prompt_text": "What does the boy see?"},
  "source_evidence": {},
  "answer_model": {},
  "validator_fields": {"source_trace_present": false}
}
```

Expected validator result in P1-S7:

```text
FAIL_SOURCE_TRACE_MISSING
```

### 17.2 Unsupported item type

Invalid because `why_inference` is outside Reading V1.

```json
{
  "item_id": "why_inference_page001_001",
  "item_type": "why_inference",
  "source_trace": {},
  "source_evidence": {},
  "answer_model": {},
  "validator_fields": {"item_type_allowed": false}
}
```

Expected validator result in P1-S7:

```text
FAIL_ITEM_TYPE_NOT_ALLOWED
```

### 17.3 Inference required

Invalid because Reading V1 requires direct evidence.

```json
{
  "item_id": "literal_where_page001_001",
  "item_type": "literal_where",
  "source_evidence": {
    "evidence_is_direct": false,
    "inference_required": true
  },
  "validator_fields": {
    "evidence_is_direct": false,
    "inference_required": true
  }
}
```

Expected validator result in P1-S7:

```text
FAIL_INFERENCE_REQUIRED_NOT_ALLOWED
```

### 17.4 Promoted package

Invalid because P1 packages must remain candidate-only.

```json
{
  "schema_version": "E4S_READING_QUESTION_PACKAGE_V1",
  "package_class": "reading_practice_candidate_package",
  "promotion_status": "promoted",
  "learner_facing_status": "published"
}
```

Expected validator result in P1-S7:

```text
FAIL_PROMOTION_STATUS_NOT_ALLOWED
FAIL_LEARNER_FACING_STATUS_NOT_ALLOWED
```

### 17.5 Learner state embedded

Invalid because Reading V1 package contract excludes learner state.

```json
{
  "schema_version": "E4S_READING_QUESTION_PACKAGE_V1",
  "package_class": "reading_practice_candidate_package",
  "learner_profile": {
    "learner_id": "example"
  },
  "validator_fields": {
    "learner_state_absent": false
  }
}
```

Expected validator result in P1-S7:

```text
FAIL_LEARNER_STATE_PRESENT
```

### 17.6 Status artifact used as source

Invalid because status artifacts are not Reading source authority.

```json
{
  "source_manifest_refs": [
    {
      "source_id": "status_snapshot_example",
      "source_family": "status_artifact"
    }
  ],
  "validator_fields": {
    "status_artifact_not_used_as_source": false
  }
}
```

Expected validator result in P1-S7:

```text
FAIL_STATUS_ARTIFACT_USED_AS_SOURCE
```

---

## 18. Future P1-S2 Sample Package Requirements

P1-S2 must use this contract to create a small sample candidate package.

Allowed in P1-S2:

```text
one small static candidate package JSON
source trace populated from approved manifest references
only allowed Reading V1 item types
all required package fields
all required item fields
all required validator-readable fields
```

Still blocked in P1-S2 unless separately approved:

```text
student-facing HTML
runtime answer checker
generator code
validator code
learner-facing release
promotion
adaptive behavior
```

P1-S2 must not modify this contract unless the operator explicitly starts a contract patch task.

---

## 19. Acceptance Gates for P1-S1

| Gate | Result | Evidence |
|---|---:|---|
| Current state declared | PASS | Section 1 |
| P1-S0 predecessor respected | PASS | Section 1 |
| Task boundary defined | PASS | Section 2 |
| Contract goal defined | PASS | Section 3 |
| Package schema defined | PASS | Sections 4-6 |
| Supported item types constrained | PASS | Section 7 |
| Item schema defined | PASS | Sections 8-10 |
| Source trace schema defined | PASS | Section 11 |
| Source evidence schema defined | PASS | Section 12 |
| Answer model schema defined | PASS | Section 13 |
| Validator-readable fields defined | PASS | Section 14 |
| blocked_use requirements defined | PASS | Section 15 |
| Audit schema defined | PASS | Section 16 |
| Invalid examples defined | PASS | Section 17 |
| P1-S2 handoff defined | PASS | Section 18 |
| Runtime impact avoided | PASS | Documentation only |
| Sample package avoided | PASS | No JSON artifact created |
| HTML avoided | PASS | No HTML artifact created |
| Generator code avoided | PASS | No generator code created |
| Validator code avoided | PASS | No validator code created |
| Learner state avoided | PASS | No learner state created |
| Promotion avoided | PASS | Design contract only |

---

## 20. Progress Tracker Update

P1 progress after P1-S1:

```text
P1 completed tasks = 2 / 9
P1 task-count progress = 22%
```

Reading V1 readiness after P1-S1:

```text
Source Authority Foundation .... COMPLETE
Reading V1 Goal ................ COMPLETE
Question Package Contract ...... COMPLETE
Sample Package ................. NOT_STARTED
HTML Renderer .................. NOT_STARTED
Answer Checker ................. NOT_STARTED
Evidence Display ............... NOT_STARTED
Generator ...................... NOT_STARTED
Validator ...................... NOT_STARTED
Export / Test / Readback ....... NOT_STARTED
```

Implementation readiness:

```text
0%
```

Reason:

```text
P1-S0 and P1-S1 are design-control tasks. No executable Reading V1 package, renderer, checker, generator, validator, or export pipeline exists yet.
```

---

## 21. Distance Vector

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
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan
```

Sub-task Status:

```text
E4S-P1-S1_ReadingQuestionPackageContract_DesignScan -> COMPLETED
```

P1 remaining distance after this sub-task:

```text
D_P1 = 7 sub-tasks left
```

Remaining P1 tasks:

```text
E4S-P1-S2_ReadingSampleQuestionPackage_Implementation
E4S-P1-S3_ReadingPracticeHTMLRenderer_Implementation
E4S-P1-S4_ReadingAnswerChecker_Implementation
E4S-P1-S5_ReadingEvidenceDisplay_Implementation
E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation
E4S-P1-S7_ReadingV1Validator_Implementation
E4S-P1-S8_ReadingV1ExportTestReadback_QA
```

---

## 22. Deferred Issues Register

```text
issue_id: E4S-P1-S1-DEFER-001
severity: high
affected_file_or_artifact: sample Reading candidate package JSON
classification: FUTURE_WORK
why_deferred: P1-S1 is contract-only; sample package belongs to P1-S2.
recommended_future_task: E4S-P1-S2_ReadingSampleQuestionPackage_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-002
severity: high
affected_file_or_artifact: Reading practice HTML renderer
classification: FUTURE_WORK
why_deferred: Renderer requires a sample package artifact first.
recommended_future_task: E4S-P1-S3_ReadingPracticeHTMLRenderer_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-003
severity: high
affected_file_or_artifact: answer checker runtime
classification: FUTURE_WORK
why_deferred: Answer checker requires concrete sample answer models.
recommended_future_task: E4S-P1-S4_ReadingAnswerChecker_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-004
severity: high
affected_file_or_artifact: evidence display runtime
classification: FUTURE_WORK
why_deferred: Evidence display requires sample item trace/evidence instances.
recommended_future_task: E4S-P1-S5_ReadingEvidenceDisplay_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-005
severity: high
affected_file_or_artifact: source-grounded generator
classification: FUTURE_WORK
why_deferred: Generator requires sample package patterns and later implementation approval.
recommended_future_task: E4S-P1-S6_SourceGroundedQuestionGenerator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-006
severity: high
affected_file_or_artifact: Reading V1 validator
classification: FUTURE_WORK
why_deferred: Validator implementation belongs to P1-S7 after sample and generator contracts are grounded.
recommended_future_task: E4S-P1-S7_ReadingV1Validator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-007
severity: high
affected_file_or_artifact: learner state / adaptive recommendation / error diagnosis
classification: OUT_OF_SCOPE_FOR_P1_V1
why_deferred: Reading V1 package contract explicitly excludes learner-adaptive behavior.
recommended_future_task: future P6/P7 only after explicit approval
blocks_current_task: no
```

---

## 23. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S2_ReadingSampleQuestionPackage_Implementation
```

Only next allowed action:

```text
Create one small static Reading V1 candidate package JSON that conforms to docs/ulga/E4S_P1_READING_QUESTION_PACKAGE_CONTRACT.md, uses approved source manifest references, contains only the six allowed Reading V1 item types, includes complete source_trace / source_evidence / answer_model / validator_fields, and remains blocked from learner-facing use and promotion.
```

Expected next artifact class:

```text
candidate_sample_json_only
```

Stop condition:

```text
Stop here. Do not create Reading HTML, answer checker runtime, evidence display runtime, generator code, validator code, learner state, or promotion artifacts until their explicit P1 tasks are started.
```
