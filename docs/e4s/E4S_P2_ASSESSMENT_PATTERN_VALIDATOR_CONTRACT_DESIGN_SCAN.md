# E4S-P2-S5 Assessment Pattern Validator Contract Design Scan

## 1. Current State

當前主任務（Epic ID）：

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

中文名稱：

```text
英語四技能來源可追蹤練習系統
```

當前 Phase：

```text
E4S-P2_AssessmentPatternExpansion
```

當前子任務（Sub-task ID）：

```text
E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_DISTRACTOR_POLICY_AND_ANSWER_MODEL_DESIGN_SCAN.md
   - P2-S5 is the next shortest step.
   - P2-S5 may define future validator contract only.
   - P2-S5 must not implement validator code, tests, generated JSON, student-facing HTML, or promotion.

2. docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
   - Defines A2 Key / KET Reading pattern mappings and writing-boundary rules.
   - Defines validator implications for A2 Key alias, pattern family, answer model, evidence, distractor, matching, open cloze, writing boundary, and promotion.

3. docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
   - Defines Cambridge YLE mapping and source evidence requirements.
   - Defines Cambridge path alias and future validator implications.

4. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - Defines canonical assessment pattern object.
   - Defines question_type enum, answer_model families, validation matrix, difficulty fields, and promotion control.

5. 重點任務排程.txt
   - Every task must follow Current State / Core Execution / Gate & Distance Update / Next Shortest Step.
   - Anti-Scope-Creep applies.
```

外接儲存權限驗證：

```text
GitHub: [已授權] 讀取專案 / 透過 API 寫入專案檔案
Google Drive: [已授權] 讀取雲端硬碟參考檔案、Spec 或資料集
```

本次交握產出目標（Deliverable）：

```text
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no generated JSON
- no JSON schema file
- no student-facing HTML
- no learner records
- no schema promotion
- no generated question package
- no sample item bank
```

---

## 2. Required Task Header

```text
Task:
E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan

Scope:
Define the future validator contract for Phase 2 assessment patterns, including validator layers, required inputs, required outputs, severity model, blocking error classes, warning classes, and promotion gates.

Allowed files:
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md

Forbidden files:
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*

Current-task blockers:
- P2-S1 must exist.
- P2-S2 must exist.
- P2-S3 must exist.
- P2-S4 must exist.
- Validator contract must cover structural validation, pattern-family validation, source-trace validation, answer-model validation, evidence validation, distractor validation, difficulty validation, writing-boundary validation, generated-content validation, and promotion validation.
- This design must not implement validator code or tests.

Warning policy:
Validator design gaps may be recorded as deferred issues. They must not expand into implementation.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task defines promotion gates but does not promote any pattern, item, distractor, source, or generated package.

Stop condition:
Stop after the validator contract design-scan document is written and P2-S6 is identified as the next shortest step.

Deferred issues register:
All validator code, tests, JSON schema files, generated sample packages, runtime answer checking, and readback QA are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P2-S5 defines the future validator contract for Phase 2 assessment patterns.

It answers:

```text
What must a future validator check before a Phase 2 assessment pattern, candidate item, answer model, distractor set, source trace, or sample package can be accepted as candidate-safe?
```

It does not answer:

```text
How is the validator implemented?
```

This task is a design boundary only.

---

### 3.2 Validator Contract Goals

A future Phase 2 validator must be able to produce a deterministic report that answers:

```text
- Is the pattern structurally valid?
- Is the question_type allowed?
- Is the mapped family compatible with the Cambridge/YLA/A2 Key alias?
- Is the answer_model complete and compatible with the pattern?
- Is answer evidence present?
- Are distractors valid, non-correct, non-ambiguous, and level-safe?
- Is source trace present and usable?
- Is difficulty metadata complete?
- Are writing-boundary patterns blocked from Reading generation?
- Are generated artifacts still candidate_only?
- Is promotion blocked unless an explicit future promotion task allows it?
```

---

### 3.3 Validation Target Types

Future validation targets may include:

```text
assessment_pattern
candidate_question_item
candidate_practice_package
answer_model
distractor_set
source_evidence_bundle
cambridge_path_alias
a2_key_path_alias
pattern_family_mapping
generated_distractor_set
writing_boundary_record
```

P2-S5 only defines target types. It does not create any target instance.

---

## 4. Validator Input Contract

### 4.1 Required Input Envelope

Future validators should accept an envelope shaped like:

```json
{
  "validation_target_type": "assessment_pattern",
  "validation_target_id": "AP_P2_000001",
  "phase": "E4S-P2",
  "contract_version": "p2.validator_contract.v1",
  "source_artifact_ref": "...",
  "target_payload": {},
  "validation_profile": "candidate_acceptance"
}
```

This is a design target only. It is not a committed JSON schema.

### 4.2 Required Envelope Fields

```text
validation_target_type
validation_target_id
phase
contract_version
source_artifact_ref
target_payload
validation_profile
```

Allowed validation profiles:

```text
design_scan_consistency
candidate_acceptance
sample_package_acceptance
promotion_precheck
readback_qa
```

Rules:

```text
- phase must be E4S-P2.
- validation_target_type must be one of the allowed target types.
- validation_profile determines which validator layers are required.
- source_artifact_ref is required even for generated candidates.
```

---

## 5. Validator Output Contract

### 5.1 Required Output Shape

Future validators should produce a report shaped like:

```json
{
  "validation_status": "FAIL",
  "validation_target_type": "assessment_pattern",
  "validation_target_id": "AP_P2_000001",
  "contract_version": "p2.validator_contract.v1",
  "blocking_error_count": 1,
  "warning_count": 2,
  "errors": [],
  "warnings": [],
  "gate_results": {},
  "promotion_allowed": false,
  "learner_facing_allowed": false
}
```

This is a design target only. It is not a committed JSON schema.

### 5.2 Status Values

```text
PASS
PASS_WITH_WARNINGS
FAIL
BLOCKED_BY_SCOPE
BLOCKED_BY_MISSING_EVIDENCE
BLOCKED_BY_PROMOTION_POLICY
```

Status rules:

```text
- any blocking error -> FAIL or BLOCKED_*.
- warnings alone -> PASS_WITH_WARNINGS.
- promotion_allowed defaults to false.
- learner_facing_allowed defaults to false.
```

---

## 6. Severity Model

Allowed severity values:

```text
blocking
warning
info
```

Severity rules:

```text
- blocking means the target cannot be candidate-accepted.
- warning means the target may be candidate-accepted only if the validation profile allows warnings.
- info records non-blocking metadata and trace notes.
```

Default:

```text
Unknown validator failures default to blocking until explicitly classified.
```

---

## 7. Validator Layer Contract

### 7.1 structural_validator

Purpose:

```text
Check that required top-level fields exist and enum values are legal.
```

Required checks:

```text
- validation_target_type is allowed.
- phase is E4S-P2.
- status does not imply promotion.
- required identity fields exist.
- question_type comes from controlled enum when present.
```

Blocking error examples:

```text
E4S_P2_STRUCT_MISSING_REQUIRED_FIELD
E4S_P2_STRUCT_UNKNOWN_TARGET_TYPE
E4S_P2_STRUCT_INVALID_PHASE
E4S_P2_STRUCT_UNKNOWN_QUESTION_TYPE
E4S_P2_STRUCT_PROMOTED_STATUS_NOT_ALLOWED
```

---

### 7.2 pattern_family_validator

Purpose:

```text
Check that pattern_family, question_type, and mapped Cambridge/A2 Key alias are compatible.
```

Required checks:

```text
- question_type is compatible with pattern_family.
- Cambridge YLE alias part maps to an allowed internal pattern family.
- A2 Key alias part maps to an allowed internal pattern family.
- KET legacy alias does not activate legacy 9-part format by default.
```

Blocking error examples:

```text
E4S_P2_PATTERN_FAMILY_MISMATCH
E4S_P2_CAMBRIDGE_ALIAS_INVALID_PART
E4S_P2_CAMBRIDGE_ALIAS_FAMILY_MISMATCH
E4S_P2_A2KEY_ALIAS_INVALID_PART
E4S_P2_A2KEY_ALIAS_FAMILY_MISMATCH
E4S_P2_KET_LEGACY_FORMAT_NOT_ALLOWED
```

---

### 7.3 source_trace_validator

Purpose:

```text
Check that source identity and location are traceable.
```

Required checks:

```text
- source_type exists.
- source_id exists.
- source_unit_id or source_location exists.
- source_authority_status exists when required.
- generated content does not replace source trace.
```

Blocking error examples:

```text
E4S_P2_SOURCE_MISSING_TYPE
E4S_P2_SOURCE_MISSING_ID
E4S_P2_SOURCE_MISSING_LOCATION
E4S_P2_SOURCE_GENERATED_REPLACES_TRACE
E4S_P2_SOURCE_AUTHORITY_STATUS_MISSING
```

---

### 7.4 evidence_validator

Purpose:

```text
Check that each answer and pair has evidence.
```

Required checks:

```text
- answer_evidence exists for every answer model that requires it.
- pair_evidence exists for matching_pairs.
- child evidence exists for composite_set child items.
- title choice evidence can point to whole-text gist if local span is not appropriate.
```

Blocking error examples:

```text
E4S_P2_EVIDENCE_MISSING_ANSWER_EVIDENCE
E4S_P2_EVIDENCE_MISSING_PAIR_EVIDENCE
E4S_P2_EVIDENCE_MISSING_CHILD_EVIDENCE
E4S_P2_EVIDENCE_GIST_NOT_DECLARED
E4S_P2_EVIDENCE_NOT_TRACEABLE
```

---

### 7.5 answer_model_validator

Purpose:

```text
Check that answer_model family, required fields, cardinality, normalization, and evidence obligations are valid.
```

Required checks by family:

```text
exact_text:
- canonical_answer exists.
- normalization_policy exists.
- answer_evidence exists.

choice_id:
- choice_set exists.
- correct_choice_ids exists.
- single-answer tasks have exactly one correct choice unless cardinality permits more.
- answer key is not raw display text.

boolean:
- truth_value exists.
- false_rationale_if_false exists when answer is false.

ordered_sequence:
- ordered_item_ids exists.
- source_order_trace exists.
- duplicate item ids are blocked.

matching_pairs:
- left_item_ids and right_item_ids exist.
- pair_set exists.
- reuse_policy exists.

cloze_tokens:
- gap_ids exist.
- canonical_tokens exist.
- accepted_tokens are bounded.
- source_gap_context exists.

accepted_answer_set:
- canonical_answer exists.
- accepted_answers is finite.
- answer_length_limit exists.
- every accepted answer is evidence-backed or authority-backed.

composite_set:
- child_item_ids exist.
- child_answer_models exist.
- every child answer model is valid.

rubric_scored_response:
- boundary-only in Phase 2 Reading.
- scoring_allowed must be false.
- learner_facing_allowed must be false.
```

Blocking error examples:

```text
E4S_P2_ANSWER_UNKNOWN_FAMILY
E4S_P2_ANSWER_MISSING_CANONICAL
E4S_P2_ANSWER_MISSING_NORMALIZATION_POLICY
E4S_P2_ANSWER_CHOICE_ID_NOT_STABLE
E4S_P2_ANSWER_CHOICE_KEY_USES_DISPLAY_TEXT
E4S_P2_ANSWER_BOOLEAN_FALSE_RATIONALE_MISSING
E4S_P2_ANSWER_SEQUENCE_TRACE_MISSING
E4S_P2_ANSWER_MATCHING_REUSE_POLICY_MISSING
E4S_P2_ANSWER_CLOZE_ACCEPTED_TOKENS_UNBOUNDED
E4S_P2_ANSWER_ACCEPTED_SET_UNBOUNDED
E4S_P2_ANSWER_COMPOSITE_CHILD_INVALID
E4S_P2_ANSWER_RUBRIC_RESPONSE_NOT_READING_SAFE
```

---

### 7.6 distractor_validator

Purpose:

```text
Check that distractors are represented, justified, non-correct, non-ambiguous, and level-safe.
```

Required checks:

```text
- distractor_id exists.
- provenance exists.
- reason_for_plausibility exists.
- reason_not_correct exists.
- source_relation exists.
- ambiguity_risk exists.
- generated distractors are candidate_only.
- distractor does not satisfy answer evidence.
- medium ambiguity requires evidence contrast.
- high ambiguity is blocked unless future human-review workflow allows it.
```

Blocking error examples:

```text
E4S_P2_DISTRACTOR_MISSING_ID
E4S_P2_DISTRACTOR_MISSING_PROVENANCE
E4S_P2_DISTRACTOR_MISSING_REASON_NOT_CORRECT
E4S_P2_DISTRACTOR_ALSO_CORRECT
E4S_P2_DISTRACTOR_AMBIGUITY_HIGH
E4S_P2_DISTRACTOR_AMBIGUITY_UNRESOLVED
E4S_P2_DISTRACTOR_LEVEL_UNSAFE
E4S_P2_DISTRACTOR_GENERATED_NOT_CANDIDATE_ONLY
```

Warning examples:

```text
E4S_P2_DISTRACTOR_MEDIUM_AMBIGUITY_REVIEW_RECOMMENDED
E4S_P2_DISTRACTOR_LEVEL_WARNING
```

---

### 7.7 option_set_validator

Purpose:

```text
Distinguish answer options, distractors, unused options, and accepted answers.
```

Required checks:

```text
- multiple_choice uses choice_set and distractor_set.
- word_box_cloze may use option_set and unused_options.
- open_cloze_lite must not use distractor_set.
- accepted_answer_set is not the same as distractor_set.
```

Blocking error examples:

```text
E4S_P2_OPTION_SET_TYPE_CONFUSION
E4S_P2_OPTION_UNUSED_OPTION_MARKING_MISSING
E4S_P2_OPTION_OPEN_CLOZE_HAS_DISTRACTOR_SET
E4S_P2_OPTION_ACCEPTED_ANSWER_MARKED_AS_DISTRACTOR
```

---

### 7.8 difficulty_validator

Purpose:

```text
Check that difficulty metadata and cognitive-load metadata are present and compatible with the pattern.
```

Required checks:

```text
- cefr_level exists.
- cognitive_load exists.
- source_length_band exists.
- inference_level exists.
- Cambridge path hint does not override CEFR.
- writing_boundary_only is high_for_A2 or otherwise declared.
```

Blocking error examples:

```text
E4S_P2_DIFFICULTY_MISSING_CEFR
E4S_P2_DIFFICULTY_MISSING_COGNITIVE_LOAD
E4S_P2_DIFFICULTY_MISSING_SOURCE_LENGTH_BAND
E4S_P2_DIFFICULTY_MISSING_INFERENCE_LEVEL
E4S_P2_DIFFICULTY_WRITING_BOUNDARY_NOT_DECLARED
```

Warning examples:

```text
E4S_P2_DIFFICULTY_LEVEL_HINT_INCOMPLETE
E4S_P2_DIFFICULTY_COGNITIVE_LOAD_REVIEW_RECOMMENDED
```

---

### 7.9 writing_boundary_validator

Purpose:

```text
Block writing-production patterns from Reading generation.
```

Required checks:

```text
- rubric_scored_response is writing_boundary_only.
- scoring_allowed is false.
- learner_facing_allowed is false.
- A2 Key Parts 6–7 are not accepted as Reading generation targets.
```

Blocking error examples:

```text
E4S_P2_WRITING_BOUNDARY_GENERATION_NOT_ALLOWED
E4S_P2_WRITING_BOUNDARY_SCORING_NOT_ALLOWED
E4S_P2_WRITING_BOUNDARY_LEARNER_FACING_NOT_ALLOWED
E4S_P2_WRITING_BOUNDARY_A2KEY_PART_NOT_ALLOWED_FOR_READING
```

---

### 7.10 generated_content_validator

Purpose:

```text
Ensure generated material remains candidate-only and review-bound.
```

Required checks:

```text
- generated artifacts are marked generated: true.
- candidate_only is true.
- generation_method is recorded when required by future implementation.
- human_review_status exists for generated distractors.
- generated content does not replace source trace or answer evidence.
```

Blocking error examples:

```text
E4S_P2_GENERATED_NOT_MARKED
E4S_P2_GENERATED_NOT_CANDIDATE_ONLY
E4S_P2_GENERATED_REPLACES_SOURCE_TRACE
E4S_P2_GENERATED_REPLACES_ANSWER_EVIDENCE
E4S_P2_GENERATED_REVIEW_STATUS_MISSING
```

---

### 7.11 promotion_validator

Purpose:

```text
Block implicit promotion and learner-facing leakage.
```

Required checks:

```text
- promotion_allowed defaults to false.
- learner_facing_allowed defaults to false.
- status does not imply promoted authority.
- promoted_by_future_task requires explicit future promotion task.
- candidate_only artifacts cannot become final authority by appearing in a package.
```

Blocking error examples:

```text
E4S_P2_PROMOTION_IMPLICIT_PROMOTION
E4S_P2_PROMOTION_LEARNER_FACING_NOT_ALLOWED
E4S_P2_PROMOTION_STATUS_INVALID
E4S_P2_PROMOTION_FUTURE_TASK_MISSING
E4S_P2_PROMOTION_CANDIDATE_PACKAGE_PROMOTES_CHILDREN
```

---

## 8. Gate Profiles

### 8.1 design_scan_consistency

Required layers:

```text
structural_validator
pattern_family_validator
promotion_validator
```

Purpose:

```text
Check design files for internal consistency.
```

Output expectation:

```text
PASS_WITH_WARNINGS allowed.
No candidate acceptance allowed.
```

---

### 8.2 candidate_acceptance

Required layers:

```text
structural_validator
pattern_family_validator
source_trace_validator
evidence_validator
answer_model_validator
distractor_validator
option_set_validator
difficulty_validator
writing_boundary_validator
generated_content_validator
promotion_validator
```

Purpose:

```text
Check whether a candidate assessment pattern or question item is safe enough to enter candidate-only storage.
```

Output expectation:

```text
blocking_error_count must be 0.
promotion_allowed must remain false.
learner_facing_allowed must remain false.
```

---

### 8.3 sample_package_acceptance

Required layers:

```text
candidate_acceptance layers for every child item
composite_set checks when package includes reading_comprehension_set
promotion_validator at package level
```

Purpose:

```text
Check whether a future sample package is internally valid as candidate-only.
```

Output expectation:

```text
No child item may bypass its own answer/evidence/distractor checks.
Package status cannot promote child artifacts.
```

---

### 8.4 promotion_precheck

Required layers:

```text
all candidate_acceptance layers
promotion_validator
source_trace_validator
evidence_validator
generated_content_validator
```

Purpose:

```text
Check whether a future explicit promotion task has the minimum evidence needed to begin review.
```

Output expectation:

```text
This profile may report promotion_readiness, but it cannot itself promote.
```

---

## 9. Minimum Error Code Registry V1

Blocking error code groups:

```text
E4S_P2_STRUCT_*
E4S_P2_PATTERN_*
E4S_P2_SOURCE_*
E4S_P2_EVIDENCE_*
E4S_P2_ANSWER_*
E4S_P2_DISTRACTOR_*
E4S_P2_OPTION_*
E4S_P2_DIFFICULTY_*
E4S_P2_WRITING_BOUNDARY_*
E4S_P2_GENERATED_*
E4S_P2_PROMOTION_*
```

Warning code groups:

```text
E4S_P2_WARNING_DISTRACTOR_*
E4S_P2_WARNING_DIFFICULTY_*
E4S_P2_WARNING_SOURCE_*
E4S_P2_WARNING_REVIEW_*
```

Rules:

```text
- Error code registry is design-level only in P2-S5.
- Future implementation may refine names but must preserve group semantics.
- Unknown failure class defaults to blocking.
```

---

## 10. Validator Report Required Summary Fields

Future reports must include:

```text
validation_status
validation_target_type
validation_target_id
contract_version
validation_profile
blocking_error_count
warning_count
layer_results
gate_results
promotion_allowed
learner_facing_allowed
next_required_action
```

Recommended `next_required_action` values:

```text
none
fix_structure
attach_source_trace
attach_answer_evidence
fix_answer_model
fix_distractors
resolve_ambiguity
mark_generated_candidate_only
move_to_writing_authority
request_human_review
blocked_until_future_task
```

---

## 11. Non-Goals

This task does not define or implement:

```text
- validator code
- validator CLI
- validator tests
- JSON schema file
- generated validation reports
- generated sample package
- sample item bank
- learner-facing quiz renderer
- runtime answer checker
- official source manifest
- Cambridge asset ingestion
- promotion workflow implementation
- human review workflow implementation
```

---

## 12. Deferred Issues Register

```text
issue_id: P2-S5-U1-VALIDATOR-IMPLEMENTATION
severity: normal
affected_file_or_artifact: future validators / tools
classification: FUTURE_WORK
why_deferred: P2-S5 defines the contract only and must not implement validator code.
recommended_future_task: future E4S-P2 validator implementation task after P2 readback QA
blocks_current_task: no
```

```text
issue_id: P2-S5-U2-VALIDATOR-TESTS
severity: normal
affected_file_or_artifact: future tests
classification: FUTURE_WORK
why_deferred: P2-S5 does not create test files.
recommended_future_task: future E4S-P2 validator implementation QA task
blocks_current_task: no
```

```text
issue_id: P2-S5-U3-JSON-SCHEMA
severity: normal
affected_file_or_artifact: future JSON schema
classification: FUTURE_WORK
why_deferred: P2-S5 is a design scan, not schema implementation.
recommended_future_task: future E4S-P2 schema contract implementation task
blocks_current_task: no
```

```text
issue_id: P2-S6-SAMPLE-PACKAGE
severity: normal
affected_file_or_artifact: future candidate sample package
classification: FUTURE_WORK
why_deferred: P2-S5 must not generate sample packages.
recommended_future_task: E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
blocks_current_task: no
```

```text
issue_id: P2-S7-READBACK-QA
severity: normal
affected_file_or_artifact: future Phase 2 readback QA
classification: FUTURE_WORK
why_deferred: Readback QA should run after P2-S6 candidate-only sample package design.
recommended_future_task: E4S-P2-S7_Phase2ReadbackQA
blocks_current_task: no
```

---

## 13. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S1 assessment pattern contract design scan exists.
[PASS] P2-S2 Cambridge YLE pattern mapping design scan exists.
[PASS] P2-S3 KET / A2 Key reading pattern mapping design scan exists.
[PASS] P2-S4 distractor policy and answer model design scan exists.
[PASS] P2-S5 deliverable path is defined.
[PASS] Validator input envelope is defined.
[PASS] Validator output contract is defined.
[PASS] Severity model is defined.
[PASS] Structural validator layer is defined.
[PASS] Pattern family validator layer is defined.
[PASS] Source trace validator layer is defined.
[PASS] Evidence validator layer is defined.
[PASS] Answer model validator layer is defined.
[PASS] Distractor validator layer is defined.
[PASS] Option-set validator layer is defined.
[PASS] Difficulty validator layer is defined.
[PASS] Writing-boundary validator layer is defined.
[PASS] Generated-content validator layer is defined.
[PASS] Promotion validator layer is defined.
[PASS] Gate profiles are defined.
[PASS] Minimum error code registry is defined.
[PASS] Validator report required summary fields are defined.
[PASS] Validator implementation is deferred.
[PASS] Validator tests are deferred.
[PASS] JSON schema implementation is deferred.
[PASS] No runtime code is created.
[PASS] No validator code is created.
[PASS] No test is created.
[PASS] No generated JSON is created.
[PASS] No student-facing HTML is created.
[PASS] No learner record is created.
[PASS] No candidate is promoted.
```

### Distance Vector

```text
Total Distance for Phase 2:
D_P2 = 2 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan -> COMPLETED

Remaining:
P2-S6  AssessmentPatternSamplePackage_CandidateOnly       NEXT
P2-S7  Phase2ReadbackQA                                   DEFERRED
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN_COMPLETED
```

---

## 14. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
```

唯一執行動作：

```text
請下達：
E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
```

Next task boundary:

```text
P2-S6 may define or create a candidate-only sample package only if it remains non-promoted and non-learner-facing.
P2-S6 must not implement validator code, runtime answer checking, student-facing HTML, or promotion.
```
