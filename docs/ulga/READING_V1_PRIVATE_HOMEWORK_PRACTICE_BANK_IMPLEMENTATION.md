# ReadingV1 Private Homework PracticeBank Implementation

## 1. Current State

Task:
ReadingV1_PrivateHomeworkPracticeBank_Implementation

Scope:
Implement the first contract-level ReadingV1 PracticeBank schema, validator, synthetic builder scaffold, and tests.

Allowed files:
- ulga/schemas/reading_v1_practice_bank.schema.json
- ulga/validators/validate_reading_v1_practice_bank.py
- ulga/builders/build_reading_v1_practice_bank.py
- tests/ulga/test_reading_v1_practice_bank.py
- docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_IMPLEMENTATION.md

Forbidden files:
- real RAZ source files
- raw source text artifacts
- full passage text artifacts
- learner-facing HTML
- public export artifacts
- promotion artifacts
- P2 formal assessment pattern files

Current-task blockers:
- PracticeBank contract had no executable validator
- No schema existed for candidate-only package / item policy
- No automated guard existed for raw RAZ text persistence, public export, commercial distribution, source payload storage, stage question-type mismatch, answer evidence, or html_ready computation

Warning policy:
- Local scratch validation may be reported as PASS if the committed test scaffold is identical to the local scratch files.
- Full repository CI is not claimed unless a GitHub Actions run is explicitly checked later.

Generated artifact policy:
- No generated PracticeBank JSON is committed.
- The builder may emit synthetic fixtures only when run locally.
- No RAZ text or source payload is committed.

Runtime impact:
- None. The code is offline / local utility scaffolding only.

Promotion impact:
- None. All artifacts remain candidate-only.

Stop condition:
- Stop after schema, validator, synthetic builder, tests, and readback document are written.
- Do not generate learner-facing homework HTML.
- Do not promote any PracticeBank candidate.
- Do not enter P1-M5 overlay work inside this task.

Deferred issues register:
- P1-M5 Private Homework Candidate Overlay is deferred.
- P1-M6 Local Runtime / In-Memory Source Pipeline is deferred.
- P1-M7 Private Homework Output Gate is deferred.
- P1-M8 HTML Practice Export is deferred.
- P1-M9 P1 Closeout QA is deferred.

---

## 2. Files Created

```text
ulga/schemas/reading_v1_practice_bank.schema.json
ulga/validators/validate_reading_v1_practice_bank.py
ulga/builders/build_reading_v1_practice_bank.py
tests/ulga/test_reading_v1_practice_bank.py
docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_IMPLEMENTATION.md
```

---

## 3. Implementation Summary

### 3.1 Schema

Created:

```text
ulga/schemas/reading_v1_practice_bank.schema.json
```

The schema defines:

```text
PracticeBank package
PracticeBank item
source_payload_policy
scope
spiral_plan
source_selection
content_binding
source_trace
answer_model
answer_evidence
policy_flags
html_gate
validator_status
```

Hard policy constants include:

```text
authority_status == candidate_only
promotion_status == not_promoted
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
raw_source_text_persisted == false
full_passage_text_persisted == false
source_payload_copied_to_repo == false
```

### 3.2 Validator

Created:

```text
ulga/validators/validate_reading_v1_practice_bank.py
```

The validator checks:

```text
schema_version presence
candidate-only status
not-promoted status
level_stage validity
stage-specific question-type whitelist
formal assessment leakage
source trace presence
source payload storage block
raw RAZ text persistence block
full passage persistence block
public export block
commercial distribution block
answer key presence
answer evidence presence
direct evidence requirement
cloze answer uniqueness
sentence ordering evidence
computed html_ready
```

The validator exposes:

```text
validate_package(package)
validate_item(item, index=None)
CLI: python ulga/validators/validate_reading_v1_practice_bank.py <practice_bank_json> [--report path]
```

### 3.3 Synthetic Builder Scaffold

Created:

```text
ulga/builders/build_reading_v1_practice_bank.py
```

The builder intentionally emits only synthetic contract fixtures:

```text
source_family = synthetic_contract_fixture
source_system = reading_v1_contract_fixture
source_locator = synthetic://...
source_payload_stored = false
raw_source_text_copied = false
full_passage_text_copied = false
```

It does not read RAZ files and does not persist raw source text.

### 3.4 Tests

Created:

```text
tests/ulga/test_reading_v1_practice_bank.py
```

Test coverage:

```text
synthetic contract fixture passes
raw RAZ text policy blocks item
stage / question-type mismatch blocks item
cloze missing answer blocks item
package public export policy blocks package
```

---

## 4. Local Scratch Validation

A temporary local scratch repo was assembled with the same validator, builder, and tests before writing to GitHub.

Command:

```text
python -m unittest tests.ulga.test_reading_v1_practice_bank
```

Result:

```text
Ran 5 tests
OK
```

Important limitation:

```text
This is local scratch validation, not GitHub Actions CI.
No full-repo CI result is claimed in this task.
```

---

## 5. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Schema file created | PASS | ulga/schemas/reading_v1_practice_bank.schema.json |
| Validator file created | PASS | ulga/validators/validate_reading_v1_practice_bank.py |
| Synthetic builder file created | PASS | ulga/builders/build_reading_v1_practice_bank.py |
| Tests created | PASS | tests/ulga/test_reading_v1_practice_bank.py |
| Candidate-only policy enforced | PASS | schema + validator |
| Raw RAZ text persistence blocked | PASS | validator + test |
| Full passage persistence blocked | PASS | schema + validator |
| Public export blocked | PASS | schema + validator + test |
| Commercial distribution blocked | PASS | schema + validator |
| Stage question-type mismatch blocked | PASS | validator + test |
| Cloze missing answer blocked | PASS | validator + test |
| Synthetic fixture validates | PASS | local scratch unittest |
| No PracticeBank JSON committed | PASS | no output artifact committed |
| No HTML generated | PASS | no HTML artifact committed |
| No promotion performed | PASS | candidate-only/not_promoted throughout |
| No RAZ raw text stored | PASS | no RAZ source payload touched |

Task status:

```text
ReadingV1_PrivateHomeworkPracticeBank_Implementation -> PASS_WITH_LOCAL_SCRATCH_VALIDATION
```

---

## 6. Reading System Progress Update

| Dimension | Before | After This Implementation |
|---|---|---|
| Source Authority | PARTIAL | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | PracticeBank contract defined | PracticeBank validator scaffold implemented |
| Reading Generation | NOT_STARTED | synthetic scaffold only |
| Reading Practice | PracticeBank contract defined | PracticeBank schema + validator + scaffold implemented |
| Reading Assessment | NOT_STARTED | unchanged; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Cambridge Spiral Scope | DESIGN_DEFINED | unchanged |
| PracticeBank Contract | DESIGN_DEFINED | implemented at contract scaffold level |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M5 Private Homework Overlay ........... NOT_STARTED
P1-M6 Local Runtime Pipeline ............. NOT_STARTED
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 7. Deferred Issues Register

### D1

issue_id:
P1-M5_PrivateHomeworkCandidateOverlay

severity:
required_next_step

affected_file_or_artifact:
private homework overlay contract and candidate overlay utility

classification:
FUTURE_WORK

why_deferred:
This task only implements PracticeBank schema, validator, and synthetic builder scaffold.

recommended_future_task:
ReadingV1_PrivateHomeworkCandidateOverlay_DesignScan

blocks_current_task:
no

### D2

issue_id:
P1-M6_LocalRuntimeInMemorySourcePipeline

severity:
required_later_step

affected_file_or_artifact:
local runtime source adapter / in-memory source locator resolver

classification:
FUTURE_WORK

why_deferred:
The current task does not connect real source material or RAZ-derived records.

recommended_future_task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan

blocks_current_task:
no

### D3

issue_id:
P1-M8_HTMLPracticeExport

severity:
required_later_step

affected_file_or_artifact:
HTML export renderer

classification:
FUTURE_WORK

why_deferred:
HTML generation must wait for overlay and output gate.

recommended_future_task:
ReadingV1_HTMLPracticeExport_Implementation

blocks_current_task:
no

---

## 8. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkCandidateOverlay_DesignScan
```

唯一執行動作:

```text
定義 PracticeBank candidate 如何轉成 private homework overlay input；只定義 overlay schema / policy，不產生 HTML。
```

Next task boundary:

```text
Use PracticeBank schema and validator as input.
Do not read or store RAZ raw text.
Do not generate learner-facing HTML.
Do not enter public export.
Do not promote candidate artifacts.
```
