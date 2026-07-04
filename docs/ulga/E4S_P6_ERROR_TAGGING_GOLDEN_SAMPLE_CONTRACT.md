# E4S-P6-S5 Error Tagging Golden Sample Contract

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
E4S-P6-S5_ErrorTaggingGoldenSampleContract_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md
- docs/ulga/E4S_P6_ERROR_TAGGING_VALIDATOR_CONTRACT.md
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
docs/ulga/E4S_P6_ERROR_TAGGING_GOLDEN_SAMPLE_CONTRACT.md
```

This deliverable defines the golden-sample contract only. It does not generate the actual sample dataset, implement validator code, create builders, change UI, create learner mastery scoring, aggregate weak points, or create adaptive recommendations.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S5 defines the required shape and coverage of a future small golden-sample set for manual QA of the P6 error-tagging validator.

P6-S5 may define:

```text
- sample case categories
- required case count targets
- expected validator outcomes
- required record fragments
- expected issue codes
- manual QA checklist
- acceptance criteria for the future sample dataset
```

P6-S5 must not create:

```text
- actual golden sample JSON file
- synthetic student dataset
- source text dataset
- validator implementation
- builder implementation
- CI workflow
- learner state update
- weak-point summary
- remediation package
- adaptive recommendation
```

### 2.2 Golden Sample Purpose

The future golden sample must answer this QA question:

```text
Can a future validator correctly distinguish valid, warning, review-required, and fail cases using P6-S1 taxonomy, P6-S2 record schema, P6-S3 compatibility rules, and P6-S4 validator behavior?
```

The future golden sample must not answer:

```text
What is the learner's mastery level?
Which weak point is confirmed?
Which adaptive path should be selected?
What exercise should be generated next?
```

Those belong to later phases or later P6 tasks.

---

## 3. Golden Sample Set Contract

### 3.1 Required Sample Set Name

A future implementation may create a sample set using this logical name:

```text
e4s_p6_error_tagging_golden_sample_v1
```

This P6-S5 document does not create that dataset.

### 3.2 Required Sample Categories

The future golden sample should include these categories:

| Category | Expected Validator Result | Purpose |
|---|---|---|
| `valid_pass_case` | `PASS` | Confirms clean records pass all gates |
| `valid_warning_case` | `PASS_WITH_WARNINGS` | Confirms non-blocking risky records are warned |
| `review_required_case` | `REVIEW_REQUIRED` | Confirms unsafe auto-diagnosis is routed to human review |
| `fail_schema_case` | `FAIL` | Confirms missing/invalid required fields fail |
| `fail_link_case` | `FAIL` | Confirms broken cross-record links fail |
| `fail_taxonomy_case` | `FAIL` | Confirms unknown taxonomy values fail |
| `fail_compatibility_case` | `FAIL` | Confirms P6-S3 BLOCK combinations fail |
| `fail_source_trace_case` | `FAIL` | Confirms Reading V1 source trace violations fail |
| `fail_boundary_case` | `FAIL` | Confirms generated content / learner mutation boundary violations fail |

### 3.3 Required Case Count Target

The future sample set should be small and controlled.

Recommended count:

```text
9 to 12 total cases
```

Minimum required coverage:

```text
1 PASS case
2 PASS_WITH_WARNINGS cases
2 REVIEW_REQUIRED cases
4 FAIL cases
```

Rules:

```text
- Do not expand this into a large benchmark.
- Do not include real learner names.
- Do not include long copyrighted source text.
- Use short placeholder source_evidence_ref values instead of full source excerpts.
```

---

## 4. Sample Case Object Contract

A future golden sample case should use this logical shape:

```json
{
  "sample_case_id": "GS_P6_001",
  "category": "valid_pass_case",
  "expected_result": "PASS",
  "description": "Short operational reason for the case.",
  "records_under_test": {
    "tagged_question_record": "present_or_omitted_by_case",
    "learner_answer_record": "present_or_omitted_by_case",
    "error_diagnosis_record": "present_or_omitted_by_case",
    "remediation_link_record": "present_or_omitted_by_case"
  },
  "expected_gate_outcomes": {},
  "expected_issue_codes": [],
  "manual_review_note": null
}
```

This is a contract shape only, not generated dataset content.

### 4.1 Required Fields

| Field | Type | Required | Rule |
|---|---|---:|---|
| `sample_case_id` | string | Yes | Prefix `GS_P6_`. |
| `category` | string | Yes | Must use P6-S5 category values. |
| `expected_result` | string | Yes | Must use P6-S4 result values. |
| `description` | string | Yes | Short operational reason. |
| `records_under_test` | object | Yes | Contains logical record fragments or references. |
| `expected_gate_outcomes` | object | Yes | Expected gate result by P6-S4 gate name. |
| `expected_issue_codes` | array[string] | Yes | Empty only for clean PASS case. |
| `manual_review_note` | string or null | Yes | Required non-null for review-required cases. |

### 4.2 Required Gate Outcome Keys

Each sample case should declare expected outcomes for:

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

Allowed values:

```text
PASS
PASS_WITH_WARNINGS
FAIL
REVIEW_REQUIRED
NOT_RUN
```

### 4.3 Required Record Fragments

Each sample case may include logical fragments of:

```text
tagged_question_record
learner_answer_record
error_diagnosis_record
remediation_link_record
```

Fragments should be minimal and should only include fields needed to test the target condition.

Rules:

```text
- Do not duplicate the full P6-S2 schema in every sample.
- Include only enough fields to trigger the target validator behavior.
- Keep source_evidence_ref as an ID reference, not a long text quote.
```

---

## 5. Required Golden Sample Coverage

### 5.1 PASS Case Coverage

At least one case must prove that a clean Reading V1 record chain passes.

Required characteristics:

```text
question_type = literal_what or literal_who or literal_where
skill_area = reading or comprehension
concept_tags include a compatible reading tag
cognitive_skill = locate_information or choose_answer or produce_word
error_type/error_detail/remediation_tag are compatible if an incorrect answer is included
source_evidence_ref is present
all cross-record links resolve
no generated content exists
```

Expected result:

```text
PASS
```

Expected issue codes:

```text
[]
```

### 5.2 Warning Case Coverage

At least two cases must prove that warning conditions are not promoted to failure.

Recommended warning targets:

```text
warn_single_answer_vocabulary_gap
warn_single_answer_rule_application
warn_remediation_from_concept_only
warn_question_type_skill_area
```

Expected result:

```text
PASS_WITH_WARNINGS
```

Rules:

```text
- WARN cases must have no FAIL issue.
- WARN cases must preserve source trace when Reading V1 is involved.
- WARN cases must not mutate learner state or create generated content.
```

### 5.3 REVIEW_REQUIRED Case Coverage

At least two cases must prove that unsafe automatic classification routes to review.

Recommended review targets:

```text
careless_error_requires_review
question_misread_requires_review
insufficient_evidence_requires_review
human_review_required unresolved
```

Expected result:

```text
REVIEW_REQUIRED
```

Required fields:

```text
manual_review_note must explain why human review is required.
expected_issue_codes must include a REVIEW issue code.
```

### 5.4 FAIL Schema Case Coverage

At least one case must prove that malformed record shape fails.

Recommended issue codes:

```text
missing_required_field
invalid_field_type
invalid_record_id_prefix
missing_schema_version
missing_taxonomy_version
```

Expected result:

```text
FAIL
```

### 5.5 FAIL Link Case Coverage

At least one case must prove that broken cross-record links fail.

Recommended issue codes:

```text
broken_tagged_question_link
broken_learner_answer_link
broken_error_diagnosis_link
question_id_mismatch
```

Expected result:

```text
FAIL
```

### 5.6 FAIL Taxonomy Case Coverage

At least one case must prove that unknown controlled values fail.

Recommended issue codes:

```text
unknown_question_type
unknown_skill_area
unknown_concept_tag
unknown_cognitive_skill
unknown_error_type
unknown_error_detail
unknown_remediation_tag
```

Expected result:

```text
FAIL
```

### 5.7 FAIL Compatibility Case Coverage

At least one case must prove that P6-S3 BLOCK combinations fail.

Recommended issue codes:

```text
blocked_question_type_skill_area
blocked_question_type_cognitive_skill
blocked_skill_area_concept_tag
blocked_error_type_error_detail
blocked_error_detail_remediation_tag
blocked_confidence_assignment
blocked_reading_v1_future_question_type
```

Expected result:

```text
FAIL
```

### 5.8 FAIL Source Trace Case Coverage

At least one case must prove that Reading V1 diagnosis without source evidence fails.

Recommended issue codes:

```text
missing_source_evidence_ref
source_evidence_ref_mismatch
source_grounded_diagnosis_without_evidence
```

Expected result:

```text
FAIL
```

### 5.9 FAIL Boundary Case Coverage

At least one case must prove that non-generation boundary violations fail.

Recommended issue codes:

```text
remediation_link_contains_generated_content
validator_mutates_learner_state
validator_generates_weak_point_summary
validator_generates_adaptive_recommendation
```

Expected result:

```text
FAIL
```

---

## 6. Manual QA Checklist

A future manual QA pass over the golden sample should verify:

```text
- Every sample_case_id is unique.
- Every category is represented at least once where required.
- Expected result matches P6-S4 result values.
- Expected gate outcomes use P6-S4 gate names.
- Expected issue codes come from P6-S4 issue code families.
- PASS case has zero issue codes.
- WARN cases have no FAIL issue codes.
- REVIEW cases include manual_review_note.
- FAIL cases include at least one blocking issue code.
- Reading V1 cases preserve source_evidence_ref unless the target is a source trace failure.
- No sample contains real learner names.
- No sample contains long copyrighted source text.
- No sample contains generated remediation exercise content.
```

---

## 7. Acceptance Criteria for Future Golden Sample Dataset

A future dataset can be accepted only if:

```text
PASS - It uses this P6-S5 contract.
PASS - It covers PASS, PASS_WITH_WARNINGS, REVIEW_REQUIRED, and FAIL outcomes.
PASS - It includes schema, link, taxonomy, compatibility, source trace, and boundary failure coverage.
PASS - It is small enough for manual QA.
PASS - It contains no real learner names or personal data.
PASS - It contains no long copyrighted source text.
PASS - It does not generate exercises or adaptive recommendations.
PASS - It can be used by a future validator implementation test without modifying runtime.
```

---

## 8. Explicit Non-goals

P6-S5 does not create:

```text
- golden sample JSON dataset
- sample source text corpus
- validator code
- test runner
- CI workflow
- generated exercise package
- learner profile update
- weak-point summary
- remediation recommendation
- UI / dashboard
```

P6-S5 also does not change any existing runtime behavior.

---

## 9. Gate and Distance Update

Gate Metrics:

```text
PASS - golden sample purpose defined
PASS - required sample categories defined
PASS - required case count target defined
PASS - sample case object contract defined
PASS - expected gate outcome keys defined
PASS - PASS/WARN/REVIEW/FAIL coverage defined
PASS - manual QA checklist defined
PASS - future dataset acceptance criteria defined
PASS - runtime/code untouched
PASS - actual sample dataset not generated
PASS - validator implementation deferred
PASS - weak-point aggregation remains out of scope
PASS - adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 3 sub-tasks left after P6-S5
E4S-P6-S5_ErrorTaggingGoldenSampleContract_DesignScan -> COMPLETED
E4S-P6 -> GOLDEN_SAMPLE_CONTRACT_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 10. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S6_ErrorTaggingImplementationPlan_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_IMPLEMENTATION_PLAN.md
```

P6-S6 should define the staged implementation plan for future validator/data work without writing implementation code.

P6-S6 must not implement validator code, generate the sample dataset, create builders, modify UI, create learner mastery scoring, aggregate weak points, or create adaptive recommendations.
