# E4S-P6-S6 Error Tagging Implementation Plan

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
E4S-P6-S6_ErrorTaggingImplementationPlan_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md
- docs/ulga/E4S_P6_ERROR_TAGGING_VALIDATOR_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_GOLDEN_SAMPLE_CONTRACT.md
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
docs/ulga/E4S_P6_ERROR_TAGGING_IMPLEMENTATION_PLAN.md
```

This deliverable defines the staged implementation plan only. It does not implement validator code, generate the golden sample dataset, create builders, modify UI, create learner mastery scoring, aggregate weak points, or create adaptive recommendations.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S6 converts the previous P6 contracts into a future implementation sequence.

The implementation sequence must preserve these prior contracts:

```text
P6-S1: taxonomy contract
P6-S2: record schema contract
P6-S3: compatibility matrix
P6-S4: validator contract
P6-S5: golden sample contract
```

P6-S6 may define:

```text
- implementation stages
- future file targets
- dependency order
- acceptance gates
- rollback boundaries
- expected operator checkpoints
- future QA flow
```

P6-S6 must not create:

```text
- validator source code
- builder source code
- golden sample JSON dataset
- generated exercise data
- learner state mutation
- weak-point aggregation output
- UI / dashboard
- adaptive recommendation
```

### 2.2 Implementation Principle

The future implementation must follow contract-first order:

```text
contract -> golden sample -> validator -> QA -> data builder -> report -> weak-point bridge
```

Runtime-facing or learner-state-facing work must remain blocked until validator and QA gates pass.

---

## 3. Planned Future Implementation Stages

### 3.1 Stage I0 - Contract Freeze Check

Purpose:

```text
Confirm P6-S1 through P6-S6 contracts exist and are internally consistent before any code or dataset is created.
```

Allowed future work:

```text
- inspect contract files
- produce a contract inventory report
- identify missing or conflicting fields
- confirm no runtime files are touched
```

Future output target:

```text
docs/ulga/E4S_P6_CONTRACT_FREEZE_CHECK.md
```

Acceptance gate:

```text
PASS - all required P6 contract files exist
PASS - no unresolved contradiction across taxonomy/schema/matrix/validator/golden-sample contracts
PASS - no runtime/code change required
```

### 3.2 Stage I1 - Golden Sample Dataset Implementation

Purpose:

```text
Create the small manual-QA golden sample dataset defined by P6-S5.
```

Allowed future work:

```text
- create 9 to 12 logical cases
- cover PASS, PASS_WITH_WARNINGS, REVIEW_REQUIRED, and FAIL results
- include schema/link/taxonomy/compatibility/source-trace/boundary failures
- use placeholder source_evidence_ref IDs instead of full source excerpts
```

Potential future output target:

```text
ulga/fixtures/e4s_p6_error_tagging_golden_sample_v1.json
```

Acceptance gate:

```text
PASS - sample count remains small
PASS - all required categories from P6-S5 are represented
PASS - no real learner names or personal data
PASS - no long copyrighted source text
PASS - no generated remediation exercise content
```

Blocked in I1:

```text
- validator implementation
- runtime integration
- learner state mutation
- weak-point aggregation
```

### 3.3 Stage I2 - Static Validator Implementation

Purpose:

```text
Implement an offline/static validator that checks P6-S2 records against P6-S1, P6-S3, and P6-S4.
```

Allowed future work:

```text
- implement schema checks
- implement link integrity checks
- implement source trace checks
- implement controlled taxonomy checks
- implement compatibility matrix checks
- implement diagnosis safety checks
- implement non-generation boundary checks
- produce a validator report from input files
```

Potential future source target:

```text
ulga/validators/validate_e4s_p6_error_tagging.py
```

Potential future report target:

```text
ulga/reports/e4s_p6_error_tagging_validation_report.json
```

Acceptance gate:

```text
PASS - validator can run offline
PASS - validator does not mutate learner state
PASS - validator does not aggregate weak points
PASS - validator does not generate exercises
PASS - validator distinguishes PASS/WARN/REVIEW/FAIL cases from golden sample
```

Blocked in I2:

```text
- data builder
- UI
- adaptive recommendation
- mastery scoring
```

### 3.4 Stage I3 - Golden Sample Validator QA

Purpose:

```text
Run the static validator against the golden sample dataset and verify expected results.
```

Allowed future work:

```text
- execute validator on golden sample
- compare actual result to expected_result
- compare actual issue codes to expected_issue_codes
- produce QA report
```

Potential future report target:

```text
ulga/reports/e4s_p6_error_tagging_golden_sample_qa.json
```

Acceptance gate:

```text
PASS - all PASS cases pass
PASS - all WARN cases return PASS_WITH_WARNINGS
PASS - all REVIEW cases return REVIEW_REQUIRED
PASS - all FAIL cases fail with expected issue families
PASS - no unexpected runtime side effects
```

Blocked in I3:

```text
- source data ingestion
- learner-facing output
- weak-point summary
```

### 3.5 Stage I4 - Tagged Record Builder Planning

Purpose:

```text
Plan how future source-grounded question packages can emit P6-S2-compatible records.
```

Allowed future work:

```text
- define input assumptions from Reading V1 question packages
- define mapping from question package fields to tagged_question_record
- define mapping from answer events to learner_answer_record
- define manual or rule-based path to error_diagnosis_record
- define remediation_link_record mapping strategy
```

Potential future design target:

```text
docs/ulga/E4S_P6_TAGGED_RECORD_BUILDER_PLAN.md
```

Acceptance gate:

```text
PASS - builder plan preserves source_evidence_ref
PASS - builder plan uses P6-S1 taxonomy
PASS - builder plan uses P6-S2 records
PASS - builder plan remains offline/static
```

Blocked in I4:

```text
- actual builder implementation
- runtime learner answer capture
- UI work
```

### 3.6 Stage I5 - Static Record Builder Implementation

Purpose:

```text
Implement a static/offline builder that emits P6-S2-compatible records from approved input records.
```

Potential future source target:

```text
ulga/builders/build_e4s_p6_error_tagging_records.py
```

Potential future output target:

```text
ulga/graph/e4s_p6_error_tagging_records.json
```

Acceptance gate:

```text
PASS - output validates against P6-S4 validator
PASS - source trace is preserved
PASS - no learner state mutation
PASS - no weak-point aggregation
PASS - no generated exercise content
```

Blocked in I5:

```text
- adaptive path
- mastery score
- learner profile update
```

### 3.7 Stage I6 - Weak-point Bridge Design Only

Purpose:

```text
Define how validated error_diagnosis_records could later feed a weak-point summary without implementing that engine.
```

Potential future design target:

```text
docs/ulga/E4S_P6_WEAK_POINT_BRIDGE_DESIGN.md
```

Allowed future work:

```text
- define evidence aggregation prerequisites
- define minimum repeated-evidence rule
- define safe boundary between diagnosis event and weak-point state
- define fields needed by a later weak-point engine
```

Blocked in I6:

```text
- weak-point aggregation implementation
- learner mastery score
- adaptive recommendation
- automatic remediation scheduling
```

---

## 4. Dependency Order

The staged dependency order must be:

```text
I0 Contract Freeze Check
  -> I1 Golden Sample Dataset Implementation
  -> I2 Static Validator Implementation
  -> I3 Golden Sample Validator QA
  -> I4 Tagged Record Builder Planning
  -> I5 Static Record Builder Implementation
  -> I6 Weak-point Bridge Design Only
```

Hard rule:

```text
I5 must not start before I2 and I3 pass.
I6 must not become implementation until I5 validates cleanly.
Adaptive recommendation remains blocked for all P6-S6 planned stages.
```

---

## 5. Future File Target Map

| Stage | File Target | Type | Status |
|---|---|---|---|
| I0 | `docs/ulga/E4S_P6_CONTRACT_FREEZE_CHECK.md` | Design / QA doc | Future |
| I1 | `ulga/fixtures/e4s_p6_error_tagging_golden_sample_v1.json` | Fixture data | Future |
| I2 | `ulga/validators/validate_e4s_p6_error_tagging.py` | Static validator | Future |
| I2 | `ulga/reports/e4s_p6_error_tagging_validation_report.json` | Validation report | Future |
| I3 | `ulga/reports/e4s_p6_error_tagging_golden_sample_qa.json` | QA report | Future |
| I4 | `docs/ulga/E4S_P6_TAGGED_RECORD_BUILDER_PLAN.md` | Design doc | Future |
| I5 | `ulga/builders/build_e4s_p6_error_tagging_records.py` | Static builder | Future |
| I5 | `ulga/graph/e4s_p6_error_tagging_records.json` | Graph/output data | Future |
| I6 | `docs/ulga/E4S_P6_WEAK_POINT_BRIDGE_DESIGN.md` | Design doc | Future |

Rules:

```text
- File targets are planning targets, not created by P6-S6.
- Runtime files must not be touched by P6-S6.
- UI files must not be touched by P6-S6.
```

---

## 6. Acceptance Gates for Future Implementation

### 6.1 Contract Gate

```text
PASS - P6-S1 through P6-S6 are present
PASS - taxonomy/schema/matrix/validator/golden sample contracts are aligned
PASS - all later implementation stages cite the relevant contract
```

### 6.2 Static Safety Gate

```text
PASS - implementation remains offline/static
PASS - no learner state mutation
PASS - no runtime service dependency
PASS - no UI/dashboard dependency
```

### 6.3 Source Trace Gate

```text
PASS - source_evidence_ref is preserved
PASS - source_unit_id is preserved when available
PASS - no long source text is duplicated into QA or report files
```

### 6.4 Validator Gate

```text
PASS - golden sample expected results match actual validator results
PASS - FAIL cases fail for expected issue families
PASS - WARN cases do not fail
PASS - REVIEW cases stay review-required
```

### 6.5 Non-generation Boundary Gate

```text
PASS - remediation_link_record contains tags only
PASS - no generated exercise content appears in validation reports
PASS - no adaptive path is created
PASS - no mastery score is created
```

---

## 7. Operator Checkpoints

Future implementation should request explicit operator approval before:

```text
- creating the golden sample JSON fixture
- implementing the validator source file
- implementing the static record builder
- writing graph/output JSON files
- designing weak-point bridge fields
```

No operator approval is needed for reading existing P6 contract docs.

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Over-expanding golden sample into benchmark | Scope creep | Keep I1 to 9-12 cases |
| Treating one wrong answer as weak point | Over-diagnosis | Preserve diagnosis event vs weak-point separation |
| Validator mutates learner state | Runtime contamination | Static-only validator gate |
| Remediation tag becomes generated exercise | Boundary violation | Non-generation boundary gate |
| Missing source_evidence_ref | Loss of source trace | Source trace gate must fail |
| Unknown taxonomy drift | Inconsistent reporting | Controlled taxonomy gate must fail |
| Compatibility matrix ambiguity | False diagnosis | REVIEW_REQUIRED fallback |
| UI pressure before validator QA | Premature productization | UI remains blocked in P6-S6 |

---

## 9. Explicit Non-goals

P6-S6 does not create:

```text
- validator code
- builder code
- golden sample dataset
- graph/output JSON
- validation report JSON
- CI workflow
- runtime API
- UI / dashboard
- learner mastery score
- weak-point summary
- adaptive recommendation
```

P6-S6 also does not change any existing runtime behavior.

---

## 10. Gate and Distance Update

Gate Metrics:

```text
PASS - staged implementation plan defined
PASS - dependency order defined
PASS - future file target map defined
PASS - acceptance gates defined
PASS - operator checkpoints defined
PASS - risk register defined
PASS - runtime/code untouched
PASS - actual sample dataset not generated
PASS - validator implementation deferred
PASS - builder implementation deferred
PASS - weak-point aggregation remains out of scope
PASS - adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 2 sub-tasks left after P6-S6
E4S-P6-S6_ErrorTaggingImplementationPlan_DesignScan -> COMPLETED
E4S-P6 -> IMPLEMENTATION_PLAN_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 11. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S7_ErrorTaggingCloseoutReadinessCheck
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_CLOSEOUT_READINESS_CHECK.md
```

P6-S7 should verify that P6-S0 through P6-S6 created a coherent contract chain and decide whether P6 can close as contract/design-ready.

P6-S7 must not implement validator code, generate the sample dataset, create builders, modify UI, create learner mastery scoring, aggregate weak points, or create adaptive recommendations.
