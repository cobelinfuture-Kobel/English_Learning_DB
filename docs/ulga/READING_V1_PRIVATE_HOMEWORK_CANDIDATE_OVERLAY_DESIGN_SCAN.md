# ReadingV1 Private Homework Candidate Overlay Design Scan

## 1. Current State

Task:
ReadingV1_PrivateHomeworkCandidateOverlay_DesignScan

Scope:
Define how a validated PracticeBank candidate is transformed into a private homework overlay input for later local/private rendering.

Allowed files:
- docs/ulga/READING_V1_PRIVATE_HOMEWORK_CANDIDATE_OVERLAY_DESIGN_SCAN.md

Forbidden files:
- runtime code
- builders
- validators
- tests
- generated PracticeBank JSON
- generated overlay JSON
- learner-facing HTML
- public export artifacts
- RAZ raw text, full passage text, or full book text
- promotion artifacts

Current-task blockers:
- Missing overlay schema between PracticeBank and future HTML export
- Missing render policy separation between html_ready and public_ready
- Missing privacy / source-payload rules for overlay layer
- Missing gate for blocking non-private or source-copying payloads before HTML export

Warning policy:
- Documentation-only warnings are acceptable if they do not block overlay contract definition.
- Any implementation or renderer change is classified as FUTURE_WORK.
- Any need to inspect or copy real source payload is a blocker for implementation and must be deferred.

Generated artifact policy:
- No generated overlay artifact is allowed in this task.
- This task writes one design document only.

Runtime impact:
- None.

Promotion impact:
- None.
- Overlay records remain candidate-only and private-homework-only.
- Overlay readiness does not imply learner-facing authority or public export readiness.

Stop condition:
- Stop after defining overlay purpose, input contract, overlay schema, policy flags, render gate, Gate PASS checklist, deferred issues, and next task.
- Do not implement overlay builder.
- Do not generate overlay JSON.
- Do not generate HTML.
- Do not copy or persist raw source text.

Deferred issues register:
- P1-M5 implementation is deferred unless separately approved as a code task.
- P1-M6 Local Runtime / In-Memory Source Pipeline is deferred.
- P1-M7 Private Homework Output Gate is deferred.
- P1-M8 HTML Practice Export is deferred.
- P1-M9 P1 Closeout QA is deferred.

---

## 2. Purpose

The Private Homework Candidate Overlay is the bridge between:

```text
PracticeBank candidate
↓
private homework render input
↓
future local/private HTML export
```

It does not create questions. It does not validate source authority. It does not render HTML.

Its purpose is to create a render-safe wrapper around already validated PracticeBank items so that future HTML export can operate without touching raw source text or authority internals.

---

## 3. Boundary

The overlay may contain:

```text
package metadata
student-facing prompt text
answer model reference
item ordering
local render settings
private homework labels
source locator references
answer evidence references
policy flags
html_ready state copied from validator result
```

The overlay must not contain:

```text
raw RAZ page text
full RAZ passage text
full book text
unreviewed source payload
public export settings
commercial worksheet metadata
formal Cambridge mock exam branding
promotion metadata
adaptive learner state
student performance history
```

Critical rule:

```text
overlay_ready != html_ready != public_ready
```

Meaning:

```text
overlay_ready: safe to pass to local/private renderer
html_ready: item passed PracticeBank html gate
public_ready: out of P1 scope and must remain false
```

---

## 4. Input Preconditions

A PracticeBank package may enter overlay preparation only if:

```text
validator_status == PASS
all selected items computed_html_ready == true
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
raw_source_text_persisted == false
full_passage_text_persisted == false
source_payload_copied_to_repo == false
authority_status == candidate_only
promotion_status == not_promoted
```

If any item fails these checks, the overlay stage must block the whole package or exclude the failing item with a documented reason.

---

## 5. Overlay Package Schema

```json
{
  "overlay_id": "RV1_OVERLAY_YYYYMMDD_000001",
  "schema_version": "reading_v1_private_homework_overlay.v1",
  "pipeline_stage": "private_homework_overlay_candidate",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "private_homework_only": true,
  "public_ready": false,
  "source_practice_bank_id": "RV1_PB_YYYYMMDD_000001",
  "source_validation_report_ref": "report_ref_or_path",
  "scope": {
    "level_stage": "RV1-S1",
    "theme": "Home",
    "situation": "home_description",
    "item_count": 12,
    "render_language": "en",
    "instruction_language": "zh-TW"
  },
  "render_policy": {
    "render_mode": "local_private_homework_only",
    "allow_public_export": false,
    "allow_commercial_distribution": false,
    "allow_raw_source_text": false,
    "allow_full_passage_text": false,
    "allow_source_payload_copy": false,
    "allow_answer_key_display_to_student": false,
    "allow_answer_key_display_to_parent": true
  },
  "items": [],
  "overlay_validation_summary": {
    "overlay_ready": false,
    "blocked_count": 0,
    "warning_count": 0,
    "error_count": 0
  }
}
```

Package-level invariants:

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
```

---

## 6. Overlay Item Schema

```json
{
  "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
  "source_item_id": "RV1_ITEM_000001",
  "level_stage": "RV1-S1",
  "question_type": "literal_where",
  "theme": "Home",
  "display_order": 1,
  "student_view": {
    "prompt": "Where is the bag?",
    "display_text_ref": "private_runtime_locator_or_reviewed_display_text_ref",
    "display_text_inline": null,
    "options": [],
    "requires_image": false,
    "requires_audio": false
  },
  "parent_or_teacher_view": {
    "answer_key_ref": "answer_model_ref",
    "answer_evidence_ref": "evidence_ref",
    "show_answer_key": true,
    "show_source_locator": true
  },
  "source_trace_view": {
    "source_locator": "source_locator_ref",
    "source_unit_ref": "source_unit_ref",
    "source_payload_stored": false,
    "raw_source_text_visible": false,
    "full_passage_text_visible": false
  },
  "policy_flags": {
    "private_homework_only": true,
    "public_ready": false,
    "not_for_public_export": true,
    "not_for_commercial_distribution": true,
    "raw_raz_text_persisted": false,
    "full_passage_text_persisted": false,
    "source_payload_copied_to_repo": false
  },
  "gates": {
    "practice_bank_validator_status": "PASS",
    "html_ready": true,
    "overlay_ready": false,
    "overlay_ready_reason": null
  }
}
```

Important overlay rule:

```text
student_view.display_text_inline must remain null unless a later private-runtime source resolver supplies reviewed local display text.
```

The overlay should prefer references / locators over copied source text.

---

## 7. Overlay Readiness Rule

An overlay item is `overlay_ready = true` only if:

```text
source_item_id exists
level_stage exists
question_type exists
student_view.prompt exists
student_view.display_text_ref exists OR display_text_inline is allowed by private runtime policy
parent_or_teacher_view.answer_key_ref exists
parent_or_teacher_view.answer_evidence_ref exists
source_trace_view.source_payload_stored == false
source_trace_view.raw_source_text_visible == false
source_trace_view.full_passage_text_visible == false
policy_flags.private_homework_only == true
policy_flags.public_ready == false
policy_flags.not_for_public_export == true
policy_flags.not_for_commercial_distribution == true
policy_flags.raw_raz_text_persisted == false
policy_flags.full_passage_text_persisted == false
policy_flags.source_payload_copied_to_repo == false
gates.practice_bank_validator_status == PASS
gates.html_ready == true
```

An overlay package is `overlay_ready = true` only if every selected item is overlay_ready and every package-level render policy blocks public / commercial / source-payload export.

---

## 8. Blocking Error Codes for Future Overlay Validator

```text
RV1_OVERLAY_ERR_SOURCE_ITEM_ID_MISSING
RV1_OVERLAY_ERR_PRACTICE_BANK_NOT_PASS
RV1_OVERLAY_ERR_HTML_READY_FALSE
RV1_OVERLAY_ERR_PUBLIC_READY_TRUE
RV1_OVERLAY_ERR_PUBLIC_EXPORT_ALLOWED
RV1_OVERLAY_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED
RV1_OVERLAY_ERR_RAW_SOURCE_TEXT_INLINE
RV1_OVERLAY_ERR_FULL_PASSAGE_TEXT_INLINE
RV1_OVERLAY_ERR_SOURCE_PAYLOAD_STORED
RV1_OVERLAY_ERR_ANSWER_KEY_REF_MISSING
RV1_OVERLAY_ERR_ANSWER_EVIDENCE_REF_MISSING
RV1_OVERLAY_ERR_SOURCE_TRACE_REF_MISSING
RV1_OVERLAY_ERR_AUTHORITY_STATUS_NOT_CANDIDATE
RV1_OVERLAY_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED
```

Allowed warnings:

```text
RV1_OVERLAY_WARN_DISPLAY_TEXT_REQUIRES_PRIVATE_RUNTIME
RV1_OVERLAY_WARN_PARENT_VIEW_SOURCE_LOCATOR_ONLY
RV1_OVERLAY_WARN_ITEM_ORDER_NOT_GROUPED_BY_TYPE
```

Warnings do not imply automatic overlay_ready.

---

## 9. Future File Layout Recommendation

This is not implemented in the current task.

```text
ulga/schemas/reading_v1_private_homework_overlay.schema.json
ulga/validators/validate_reading_v1_private_homework_overlay.py
ulga/builders/build_reading_v1_private_homework_overlay.py
tests/ulga/test_reading_v1_private_homework_overlay.py
```

Implementation should come after this design scan only if no P1-M4 issue blocks the pipeline.

---

## 10. Reading System Progress Update

| Dimension | Before | After This DesignScan |
|---|---|---|
| Source Authority | PARTIAL | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | PracticeBank validator scaffold implemented | overlay validator contract defined |
| Reading Generation | synthetic scaffold only | unchanged |
| Reading Practice | PracticeBank schema + validator + scaffold implemented | private homework overlay contract defined |
| Reading Assessment | NOT_STARTED | unchanged; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Private Homework Overlay | NOT_STARTED | DESIGN_DEFINED |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M5 Private Homework Overlay ........... COMPLETED_BY_DESIGN
P1-M6 Local Runtime Pipeline ............. NOT_STARTED
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 11. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Required task header exists | PASS | Section 1 |
| Stop condition exists | PASS | Section 1 |
| Overlay purpose defined | PASS | Section 2 |
| Overlay boundary defined | PASS | Section 3 |
| Input preconditions defined | PASS | Section 4 |
| Overlay package schema defined | PASS | Section 5 |
| Overlay item schema defined | PASS | Section 6 |
| overlay_ready rule defined | PASS | Section 7 |
| Future overlay validator errors defined | PASS | Section 8 |
| No overlay JSON generated | PASS | Documentation-only task |
| No HTML generated | PASS | Documentation-only task |
| No runtime modified | PASS | Documentation-only task |
| No RAZ raw text stored | PASS | Documentation-only task |
| No promotion performed | PASS | candidate-only/not_promoted boundary |

Task status:

```text
ReadingV1_PrivateHomeworkCandidateOverlay_DesignScan -> COMPLETED_BY_DESIGN
```

---

## 12. Deferred Issues Register

### D1

issue_id:
P1-M5_PrivateHomeworkCandidateOverlay_Implementation

severity:
required_next_step

affected_file_or_artifact:
ulga/schemas, ulga/builders, ulga/validators, tests

classification:
FUTURE_WORK

why_deferred:
This task defines overlay schema / policy only.

recommended_future_task:
ReadingV1_PrivateHomeworkCandidateOverlay_Implementation

blocks_current_task:
no

### D2

issue_id:
P1-M6_LocalRuntimeInMemorySourcePipeline

severity:
required_later_step

affected_file_or_artifact:
local runtime source resolver / private source locator bridge

classification:
FUTURE_WORK

why_deferred:
Source resolution must be designed separately and must not copy raw source payload to repo.

recommended_future_task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_DesignScan

blocks_current_task:
no

---

## 13. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkCandidateOverlay_Implementation
```

唯一執行動作:

```text
建立 overlay schema / validator / synthetic overlay builder / tests；不讀取 RAZ raw text，不輸出 HTML。
```

Next task boundary:

```text
Use PracticeBank validator output as input.
Implement overlay contract only.
Do not implement local source resolver yet.
Do not generate learner-facing HTML.
Do not enter public export or promotion.
```
