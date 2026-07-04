# E4S-P6-S4 Error Tagging Validator Contract

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
E4S-P6-S4_ErrorTaggingValidatorContract_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md
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
docs/ulga/E4S_P6_ERROR_TAGGING_VALIDATOR_CONTRACT.md
```

This deliverable defines validator responsibilities and expected behavior only. It does not implement validator code, builders, generated data, learner state updates, weak-point aggregation, UI, or adaptive recommendation.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S4 defines the contract for a future error-tagging validator. The validator will later verify that P6-S2 records correctly use P6-S1 taxonomy and P6-S3 compatibility rules.

P6-S4 may define:

```text
- validator responsibilities
- validator inputs
- validator outputs
- PASS / WARN / FAIL / REVIEW behavior
- validation stages
- issue severity model
- source trace requirements
- non-goals
```

P6-S4 must not implement:

```text
- Python validator code
- Python builder code
- JSON output generation
- runtime execution
- UI / HTML
- learner mastery scoring
- learner state mutation
- weak-point aggregation
- remediation exercise generation
- adaptive recommendation
```

### 2.2 Validator Purpose

The future validator must answer this question:

```text
Are the error-tagging records structurally valid, taxonomy-compatible, source-traceable, and safe for later weak-point aggregation?
```

The validator must not answer:

```text
Is the learner weak at this concept?
What exercise should be generated next?
What is the learner's mastery score?
What adaptive path should be selected?
```

Those belong to later tasks.

---

## 3. Validator Inputs

### 3.1 Required Input Files / Objects

A future validator should accept these logical inputs:

```text
tagged_question_records
learner_answer_records
error_diagnosis_records
remediation_link_records
taxonomy_contract
compatibility_matrix
```

Where:

| Input | Source Contract | Purpose |
|---|---|---|
| `tagged_question_records` | P6-S2 | Validate question taxonomy usage |
| `learner_answer_records` | P6-S2 | Validate learner answer linkage and scoring shape |
| `error_diagnosis_records` | P6-S2 | Validate error_type / error_detail / confidence / evidence |
| `remediation_link_records` | P6-S2 | Validate remediation_tag mapping and linkage |
| `taxonomy_contract` | P6-S1 | Validate controlled values |
| `compatibility_matrix` | P6-S3 | Validate ALLOW / WARN / BLOCK / REVIEW rules |

### 3.2 Required Record Identifiers

The validator must require these IDs when the corresponding records exist:

```text
tagged_question_id
learner_answer_id
error_diagnosis_id
remediation_link_id
question_id
source_evidence_ref
```

### 3.3 Optional Context Inputs

Optional validator context may include:

```text
source_unit_index
source_sentence_index
question_package_index
attempt_context_index
manual_review_notes
```

Optional context may improve diagnostics, but absence of optional context must not block basic schema validation.

---

## 4. Validator Outputs

### 4.1 Top-level Output Shape

A future validator should emit a report with this logical shape:

```json
{
  "validator_id": "E4S_P6_S4_VALIDATOR_CONTRACT",
  "schema_version": "p6_s4_v1",
  "result": "PASS_WITH_WARNINGS",
  "summary": {},
  "issues": [],
  "record_counts": {},
  "gate_metrics": {},
  "next_action_hint": null
}
```

This is a contract shape only, not generated data.

### 4.2 Allowed Result Values

| Result | Meaning |
|---|---|
| `PASS` | No blocking issue and no warning issue |
| `PASS_WITH_WARNINGS` | No blocking issue, but one or more warnings/review notices exist |
| `FAIL` | One or more blocking issues exist |
| `REVIEW_REQUIRED` | Validator cannot safely classify one or more records without human review |
| `NOT_RUN` | Validator did not execute or inputs were unavailable |

### 4.3 Required Summary Fields

A future report summary should include:

```text
total_tagged_question_records
total_learner_answer_records
total_error_diagnosis_records
total_remediation_link_records
pass_count
warn_count
fail_count
review_count
missing_trace_count
blocked_compatibility_count
unknown_error_count
human_review_required_count
```

---

## 5. Validation Stages

A future validator should apply stages in this order.

### 5.1 Stage 1 - Required Record Shape

Check:

```text
- required fields exist
- field types match the P6-S2 contract
- IDs use expected prefixes
- schema_version exists
- taxonomy_version exists when taxonomy values are used
```

Blocking failures:

```text
missing_required_field
invalid_field_type
invalid_record_id_prefix
missing_schema_version
missing_taxonomy_version
```

### 5.2 Stage 2 - Cross-record Link Integrity

Check:

```text
- learner_answer_record.tagged_question_id exists in tagged_question_records
- error_diagnosis_record.learner_answer_id exists in learner_answer_records
- remediation_link_record.error_diagnosis_id exists in error_diagnosis_records
- redundant question_id values agree across linked records
```

Blocking failures:

```text
broken_tagged_question_link
broken_learner_answer_link
broken_error_diagnosis_link
question_id_mismatch
```

### 5.3 Stage 3 - Source Trace Integrity

Check for Reading V1:

```text
- source_unit_id exists when available
- source_evidence_ref exists
- source_evidence_ref is carried through tagged question and diagnosis records
- diagnosis based on source evidence has evidence reference
```

Blocking failures:

```text
missing_source_evidence_ref
missing_source_unit_id_for_reading_v1
source_evidence_ref_mismatch
source_grounded_diagnosis_without_evidence
```

Warnings:

```text
optional_sentence_evidence_missing
source_context_index_unavailable
```

### 5.4 Stage 4 - Controlled Taxonomy Values

Check:

```text
- question_type is listed in P6-S1
- skill_area is listed in P6-S1
- concept_tags are listed in P6-S1
- cognitive_skill is listed in P6-S1
- error_type is listed in P6-S1
- error_detail is listed in P6-S1
- remediation_tag is listed in P6-S1
```

Blocking failures:

```text
unknown_question_type
unknown_skill_area
unknown_concept_tag
unknown_cognitive_skill
unknown_error_type
unknown_error_detail
unknown_remediation_tag
```

### 5.5 Stage 5 - Compatibility Matrix Checks

Apply P6-S3 compatibility rules:

```text
1. question_type -> skill_area
2. question_type -> cognitive_skill
3. skill_area -> concept_tags
4. error_type -> error_detail
5. error_detail -> remediation_tag
6. confidence restrictions
7. block rules
8. warning rules
```

Blocking failures:

```text
blocked_question_type_skill_area
blocked_question_type_cognitive_skill
blocked_skill_area_concept_tag
blocked_error_type_error_detail
blocked_error_detail_remediation_tag
blocked_confidence_assignment
blocked_reading_v1_future_question_type
```

Warnings:

```text
warn_question_type_skill_area
warn_question_type_cognitive_skill
warn_skill_area_concept_tag
warn_low_confidence_diagnosis
warn_single_answer_rule_application
warn_single_answer_vocabulary_gap
warn_remediation_from_concept_only
```

### 5.6 Stage 6 - Diagnosis Safety

Check:

```text
- concept_error is not high confidence from one answer
- vocabulary_gap from one answer is not over-promoted
- rule_application_error from one answer is not over-promoted
- unknown_error uses not_enough_evidence or needs_human_review
- unsafe diagnosis uses human_review_required
```

Blocking failures:

```text
unsafe_concept_error_high_confidence
unsafe_specific_diagnosis_without_evidence
unknown_error_with_specific_detail
unknown_error_with_specific_remediation
missing_human_review_required_for_unsafe_diagnosis
```

Review outcomes:

```text
careless_error_requires_review
question_misread_requires_review
insufficient_evidence_requires_review
```

### 5.7 Stage 7 - Non-generation Boundary

Check:

```text
- remediation_link_record does not contain generated exercise content
- validator output does not mutate learner state
- validator output does not create weak-point summary
- validator output does not create adaptive path
```

Blocking failures:

```text
remediation_link_contains_generated_content
validator_mutates_learner_state
validator_generates_weak_point_summary
validator_generates_adaptive_recommendation
```

---

## 6. Issue Severity Model

### 6.1 Severity Levels

| Severity | Meaning | Result Impact |
|---|---|---|
| `INFO` | Informational note | Does not affect result |
| `WARN` | Valid but risky or incomplete | PASS_WITH_WARNINGS |
| `REVIEW` | Human review required | REVIEW_REQUIRED or PASS_WITH_WARNINGS depending on policy |
| `FAIL` | Blocking contract violation | FAIL |

### 6.2 Issue Object Contract

A future validator issue should use this logical shape:

```json
{
  "severity": "FAIL",
  "code": "blocked_error_type_error_detail",
  "record_type": "error_diagnosis_record",
  "record_id": "ED_RV1_000001",
  "field": "error_detail",
  "message": "error_detail is incompatible with error_type",
  "expected": "P6-S3 compatible error_detail",
  "actual": "missing_third_person_s",
  "source_ref": "docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md"
}
```

Rules:

```text
- issue codes must use lower_snake_case.
- issue messages should be short and operational.
- issue objects must not contain learner real names.
- issue objects must not quote long copyrighted source text.
```

---

## 7. PASS / WARN / FAIL Behavior

### 7.1 PASS

The validator may return `PASS` only when:

```text
- all required records are well-formed
- all required links resolve
- source trace is present for Reading V1
- all taxonomy values are controlled
- compatibility checks return ALLOW only
- no REVIEW or WARN issues exist
- no boundary violation exists
```

### 7.2 PASS_WITH_WARNINGS

The validator may return `PASS_WITH_WARNINGS` when:

```text
- no FAIL issue exists
- one or more WARN issues exist
- REVIEW issues are either absent or policy allows pass-with-review-note
```

### 7.3 REVIEW_REQUIRED

The validator should return `REVIEW_REQUIRED` when:

```text
- automatic classification is unsafe
- evidence is not enough
- careless_error is asserted without strong support
- question_misread is asserted without learner explanation
- human_review_required is present and unresolved
```

### 7.4 FAIL

The validator must return `FAIL` when:

```text
- any required field is missing
- any required cross-record link is broken
- source_evidence_ref is missing for Reading V1 diagnosis
- any controlled taxonomy value is unknown
- any BLOCK rule is violated
- diagnosis is over-promoted against confidence restrictions
- remediation link contains generated exercise content
- validator output attempts to mutate learner state or create weak-point summary
```

### 7.5 NOT_RUN

The validator may return `NOT_RUN` when:

```text
- required input files are unavailable
- input cannot be parsed
- contract version is unsupported
- validator execution is intentionally skipped
```

---

## 8. Gate Metrics Contract

A future validator report should expose these gate metrics:

```text
record_shape_gate
link_integrity_gate
source_trace_gate
taxonomy_gate
compatibility_gate
diagnosis_safety_gate
non_generation_boundary_gate
overall_gate
```

Allowed gate values:

```text
PASS
PASS_WITH_WARNINGS
FAIL
REVIEW_REQUIRED
NOT_RUN
```

Gate aggregation rule:

```text
- If any gate is FAIL, overall_gate = FAIL.
- Else if any gate is REVIEW_REQUIRED, overall_gate = REVIEW_REQUIRED.
- Else if any gate is PASS_WITH_WARNINGS, overall_gate = PASS_WITH_WARNINGS.
- Else if all gates are PASS, overall_gate = PASS.
- If required inputs are missing before validation, overall_gate = NOT_RUN.
```

---

## 9. Reading V1 Validator Boundary

For Reading V1, the future validator should treat these as active:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

Future-compatible question types from P6-S1 must be treated as:

```text
DEFER
```

A Reading V1 record using deferred question types should fail with:

```text
blocked_reading_v1_future_question_type
```

---

## 10. Explicit Non-goals

P6-S4 does not create:

```text
- validator source code
- CLI command
- CI workflow
- JSON report file
- synthetic test dataset
- weak-point summary
- learner mastery score
- remediation package
- adaptive recommendation
- UI / dashboard
```

P6-S4 also does not change any existing runtime behavior.

---

## 11. Gate and Distance Update

Gate Metrics:

```text
PASS - validator responsibilities defined
PASS - validator inputs defined
PASS - validator outputs defined
PASS - validation stages defined
PASS - issue severity model defined
PASS - PASS/WARN/FAIL/REVIEW behavior defined
PASS - gate metrics contract defined
PASS - Reading V1 validator boundary defined
PASS - runtime/code untouched
PASS - validator implementation deferred
PASS - weak-point aggregation remains out of scope
PASS - adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 4 sub-tasks left after P6-S4
E4S-P6-S4_ErrorTaggingValidatorContract_DesignScan -> COMPLETED
E4S-P6 -> VALIDATOR_CONTRACT_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 12. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S5_ErrorTaggingGoldenSampleContract_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_GOLDEN_SAMPLE_CONTRACT.md
```

P6-S5 should define a small golden-sample contract for manual QA of valid, warning, review-required, and fail cases.

P6-S5 must not generate the actual sample dataset, implement validator code, create builders, change UI, create learner mastery scoring, aggregate weak points, or create adaptive recommendations.
