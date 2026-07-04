# ReadingV1 Private Homework Candidate Overlay Implementation

## 1. Current State

Task:
ReadingV1_PrivateHomeworkCandidateOverlay_Implementation

Scope:
Implement the ReadingV1 private homework overlay schema, validator, synthetic overlay builder, and tests.

Allowed files:
- ulga/schemas/reading_v1_private_homework_overlay.schema.json
- ulga/validators/validate_reading_v1_private_homework_overlay.py
- ulga/builders/build_reading_v1_private_homework_overlay.py
- tests/ulga/test_reading_v1_private_homework_overlay.py
- docs/ulga/READING_V1_PRIVATE_HOMEWORK_CANDIDATE_OVERLAY_IMPLEMENTATION.md

Forbidden files:
- real RAZ source files
- raw source text artifacts
- full passage text artifacts
- generated overlay JSON artifacts
- learner-facing HTML
- public export artifacts
- promotion artifacts
- P2 formal assessment pattern files

Current-task blockers:
- Overlay contract had no executable schema
- Overlay contract had no validator
- No builder existed to transform PracticeBank-like records into render-safe overlay candidates
- No automated guard existed for inline source text, public_ready, public export, commercial distribution, html_ready false, missing answer references, or source payload storage

Warning policy:
- Local scratch validation may be reported as PASS if committed files match the tested scratch files.
- Python startup emitted a spreadsheet warmup warning from the execution environment; unittest returned exit code 0 and all overlay tests passed.
- Full repository CI is not claimed unless GitHub Actions is explicitly checked later.

Generated artifact policy:
- No generated overlay JSON is committed.
- The builder may emit synthetic overlay candidates only when run locally.
- No RAZ text or source payload is committed.

Runtime impact:
- None. The code is offline / local utility scaffolding only.

Promotion impact:
- None. All overlay artifacts remain candidate-only and not_promoted.

Stop condition:
- Stop after overlay schema, validator, builder, tests, and readback document are written.
- Do not generate learner-facing homework HTML.
- Do not promote any overlay candidate.
- Do not enter P1-M6 local runtime source resolver work inside this task.

Deferred issues register:
- P1-M6 Local Runtime / In-Memory Source Pipeline is deferred.
- P1-M7 Private Homework Output Gate is deferred.
- P1-M8 HTML Practice Export is deferred.
- P1-M9 P1 Closeout QA is deferred.

---

## 2. Files Created

```text
ulga/schemas/reading_v1_private_homework_overlay.schema.json
ulga/validators/validate_reading_v1_private_homework_overlay.py
ulga/builders/build_reading_v1_private_homework_overlay.py
tests/ulga/test_reading_v1_private_homework_overlay.py
docs/ulga/READING_V1_PRIVATE_HOMEWORK_CANDIDATE_OVERLAY_IMPLEMENTATION.md
```

---

## 3. Implementation Summary

### 3.1 Overlay Schema

Created:

```text
ulga/schemas/reading_v1_private_homework_overlay.schema.json
```

The schema defines:

```text
overlay package
overlay item
scope
render_policy
student_view
parent_or_teacher_view
source_trace_view
policy_flags
gates
overlay_validation_summary
```

Hard policy constants include:

```text
authority_status == candidate_only
promotion_status == not_promoted
private_homework_only == true
public_ready == false
render_policy.allow_public_export == false
render_policy.allow_commercial_distribution == false
render_policy.allow_raw_source_text == false
render_policy.allow_full_passage_text == false
render_policy.allow_source_payload_copy == false
student_view.display_text_inline == null
```

### 3.2 Overlay Validator

Created:

```text
ulga/validators/validate_reading_v1_private_homework_overlay.py
```

The validator checks:

```text
schema_version
authority_status == candidate_only
promotion_status == not_promoted
private_homework_only == true
public_ready == false
render policy blocks public / commercial / source-payload export
source_item_id exists
level_stage is RV1-S0..RV1-S3
question_type is ReadingV1 V1-only
student prompt exists
student_view.display_text_inline is empty
answer_key_ref exists
answer_evidence_ref exists
source_trace_view exists
source payload is not stored
raw source text is not visible
full passage text is not visible
item policy flags block public / commercial / source-payload export
PracticeBank validator status is PASS
html_ready is true
computed overlay_ready
```

The validator exposes:

```text
validate_overlay_package(package)
validate_overlay_item(item, index=None)
CLI: python ulga/validators/validate_reading_v1_private_homework_overlay.py <overlay_json> [--report path]
```

### 3.3 Synthetic Overlay Builder

Created:

```text
ulga/builders/build_reading_v1_private_homework_overlay.py
```

The builder:

```text
accepts a PracticeBank-like package
accepts a PracticeBank validation report
copies only safe references / locators
copies prompts and answer reference metadata
does not inline source text
does not read RAZ files
does not generate HTML
outputs a private-homework overlay candidate when run locally
```

### 3.4 Tests

Created:

```text
tests/ulga/test_reading_v1_private_homework_overlay.py
```

Test coverage:

```text
synthetic overlay passes
inline display text blocks item
html_ready false blocks item
public_ready true blocks package and item
missing answer_evidence_ref blocks item
```

---

## 4. Local Scratch Validation

A temporary local scratch repo was assembled with the same overlay validator, builder, and tests before writing to GitHub.

Command:

```text
python -m unittest tests.ulga.test_reading_v1_private_homework_overlay
```

Result:

```text
Ran 5 tests
OK
```

Observed non-project environment warning:

```text
Spreadsheet runtime warmup failed during python startup
```

Classification:

```text
harmless environment warning
not from project code
unittest exit code = 0
does not block current task
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
| Overlay schema file created | PASS | ulga/schemas/reading_v1_private_homework_overlay.schema.json |
| Overlay validator file created | PASS | ulga/validators/validate_reading_v1_private_homework_overlay.py |
| Overlay builder file created | PASS | ulga/builders/build_reading_v1_private_homework_overlay.py |
| Overlay tests created | PASS | tests/ulga/test_reading_v1_private_homework_overlay.py |
| Candidate-only policy enforced | PASS | schema + validator |
| Not-promoted policy enforced | PASS | schema + validator |
| Public-ready blocked | PASS | schema + validator + test |
| Public export blocked | PASS | schema + validator |
| Commercial distribution blocked | PASS | schema + validator |
| Inline source text blocked | PASS | schema + validator + test |
| Source payload storage blocked | PASS | schema + validator |
| html_ready false blocked | PASS | validator + test |
| Missing answer evidence ref blocked | PASS | validator + test |
| Synthetic overlay validates | PASS | local scratch unittest |
| No overlay JSON committed | PASS | no output artifact committed |
| No HTML generated | PASS | no HTML artifact committed |
| No promotion performed | PASS | candidate-only/not_promoted throughout |
| No RAZ raw text stored | PASS | no RAZ source payload touched |

Task status:

```text
ReadingV1_PrivateHomeworkCandidateOverlay_Implementation -> PASS_WITH_LOCAL_SCRATCH_VALIDATION
```

---

## 6. Reading System Progress Update

| Dimension | Before | After This Implementation |
|---|---|---|
| Source Authority | PARTIAL | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | PracticeBank + overlay contracts defined | overlay validator scaffold implemented |
| Reading Generation | synthetic scaffold only | unchanged |
| Reading Practice | PracticeBank schema + validator + scaffold implemented | private homework overlay schema + validator + builder implemented |
| Reading Assessment | NOT_STARTED | unchanged; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Private Homework Overlay | DESIGN_DEFINED | PASS_WITH_LOCAL_SCRATCH_VALIDATION |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M5 Private Homework Overlay ........... PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M6 Local Runtime Pipeline ............. NOT_STARTED
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 7. Deferred Issues Register

### D1

issue_id:
P1-M6_LocalRuntimeInMemorySourcePipeline

severity:
required_next_step

affected_file_or_artifact:
local runtime source resolver / private source locator bridge

classification:
FUTURE_WORK

why_deferred:
The current task implements overlay scaffolding only. Source resolution requires a separate design and must not copy raw source payload to repo.

recommended_future_task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan

blocks_current_task:
no

### D2

issue_id:
P1-M7_PrivateHomeworkOutputGate

severity:
required_later_step

affected_file_or_artifact:
output gate schema / validator / policy checker

classification:
FUTURE_WORK

why_deferred:
Output gate must wait until local runtime source resolver boundary is defined.

recommended_future_task:
ReadingV1_PrivateHomeworkOutputGate_DesignScan

blocks_current_task:
no

### D3

issue_id:
P1-M8_HTMLPracticeExport

severity:
required_later_step

affected_file_or_artifact:
HTML renderer / private homework export artifacts

classification:
FUTURE_WORK

why_deferred:
HTML export must wait for source resolver and output gate.

recommended_future_task:
ReadingV1_HTMLPracticeExport_Implementation

blocks_current_task:
no

---

## 8. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan
```

唯一執行動作:

```text
定義 private runtime source locator 如何在本機解析顯示文字；不把 RAZ raw text 或 full passage 寫入 GitHub。
```

Next task boundary:

```text
Define local/in-memory source resolver contract only.
Do not generate HTML.
Do not commit source payload artifacts.
Do not enter public export or promotion.
```
