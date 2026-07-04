# ReadingV1 Private Homework Output Gate Design Scan

## 1. Current State

Task:
ReadingV1_PrivateHomeworkOutputGate_DesignScan

Scope:
Define the final private-only gate before ReadingV1 local HTML rendering.

Allowed files:
- docs/ulga/READING_V1_PRIVATE_HOMEWORK_OUTPUT_GATE_DESIGN_SCAN.md

Forbidden files:
- code files
- tests
- generated data
- generated HTML
- public delivery files
- copied external reading material
- promotion artifacts

Current-task blockers:
- PracticeBank validation exists, but there is no final rendering-entry gate.
- Overlay validation exists, but there is no package-level render-entry gate.
- Local resolver policy exists, but there is no final pass/fail contract.

Warning policy:
- Documentation-only warnings are acceptable.
- Implementation is future work.
- Public delivery, promotion, or durable copied external material remains forbidden in P1.

Generated artifact policy:
- No generated artifact is allowed in this task.
- This task writes one design document only.

Runtime impact:
- None.

Promotion impact:
- None.
- PASS means private local render entry only.

Stop condition:
- Stop after defining inputs, report shape, blocking checks, render-entry rule, checklist, deferred issues, and next task.
- Do not implement code.
- Do not generate HTML.
- Do not persist copied external reading material.
- Do not promote any candidate.

Deferred issues register:
- OutputGate implementation is deferred.
- HTML export is deferred.
- P1 closeout QA is deferred.

---

## 2. Gate Purpose

The OutputGate is the last non-rendering control before HTML export.

It combines:

```text
PracticeBank validation
Overlay validation
Local resolver policy
Private-only render policy
Student/parent visibility policy
Reference-only material policy
```

The gate has two outcomes:

```text
HTML_ENTRY_ALLOWED
HTML_ENTRY_BLOCKED
```

HTML entry means local/private renderer eligibility only. It does not mean public-ready, commercial-ready, promoted, assessed, or learner-state recorded.

---

## 3. Required Gate Inputs

```text
practice_bank_package
practice_bank_validation_report
overlay_package
overlay_validation_report
local_resolver_policy_report
render_policy
operator_runtime_context
```

Required statuses:

```text
practice_bank_validation_report.validator_status == PASS
overlay_validation_report.validator_status == PASS
local_resolver_policy_report.resolver_status == PASS
```

Required flags:

```text
private_homework_only == true
public_ready == false
not_for_public_export == true
not_for_commercial_distribution == true
authority_status == candidate_only
promotion_status == not_promoted
```

---

## 4. OutputGate Report Shape

```json
{
  "output_gate_report_id": "RV1_OUTGATE_YYYYMMDD_000001",
  "schema_version": "reading_v1_private_homework_output_gate.v1",
  "pipeline_stage": "private_homework_output_gate",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "private_homework_only": true,
  "public_ready": false,
  "gate_inputs": {
    "practice_bank_validator_status": "PASS",
    "overlay_validator_status": "PASS",
    "local_resolver_status": "PASS"
  },
  "render_policy": {
    "render_mode": "local_private_homework_only",
    "allow_public_export": false,
    "allow_commercial_distribution": false,
    "allow_copied_material_persistence": false,
    "allow_answer_key_display_to_student": false,
    "allow_answer_key_display_to_parent": true
  },
  "item_gate_results": [],
  "summary": {
    "gate_status": "HTML_ENTRY_BLOCKED",
    "html_entry_allowed": false,
    "item_count": 0,
    "allowed_item_count": 0,
    "blocked_item_count": 0,
    "warning_count": 0,
    "error_count": 0
  }
}
```

---

## 5. Item Gate Result Shape

```json
{
  "source_item_id": "RV1_ITEM_000001",
  "overlay_item_id": "RV1_OVERLAY_ITEM_000001",
  "gate_status": "PASS",
  "html_entry_allowed": true,
  "checks": {
    "practice_bank_item_pass": true,
    "overlay_item_pass": true,
    "overlay_ready": true,
    "display_payload_safe": true,
    "copied_material_persisted": false,
    "answer_key_hidden_from_student": true,
    "parent_teacher_answer_key_allowed": true,
    "public_export_blocked": true,
    "commercial_distribution_blocked": true
  },
  "errors": [],
  "warnings": []
}
```

---

## 6. HTML Entry Rule

A package may enter local/private HTML rendering only if:

```text
PracticeBank report PASS
Overlay report PASS
Resolver policy PASS
every item is allowed
display payload is safe
no copied material is persisted
private_homework_only == true
public_ready == false
public export is blocked
commercial distribution is blocked
answer key is hidden from student view
```

Partial item exclusion is deferred.

---

## 7. Blocking Error Codes

```text
RV1_OUT_ERR_PRACTICE_BANK_NOT_PASS
RV1_OUT_ERR_OVERLAY_NOT_PASS
RV1_OUT_ERR_RESOLVER_NOT_PASS
RV1_OUT_ERR_OVERLAY_READY_FALSE
RV1_OUT_ERR_DISPLAY_PAYLOAD_UNSAFE
RV1_OUT_ERR_COPIED_MATERIAL_PERSISTED
RV1_OUT_ERR_PRIVATE_HOMEWORK_FALSE
RV1_OUT_ERR_PUBLIC_READY_TRUE
RV1_OUT_ERR_PUBLIC_EXPORT_ALLOWED
RV1_OUT_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED
RV1_OUT_ERR_ANSWER_KEY_VISIBLE_TO_STUDENT
RV1_OUT_ERR_AUTHORITY_STATUS_NOT_CANDIDATE
RV1_OUT_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED
```

Allowed warnings:

```text
RV1_OUT_WARN_RUNTIME_ONLY_DISPLAY
RV1_OUT_WARN_PARENT_VIEW_REFERENCE_ONLY
RV1_OUT_WARN_ITEM_EXCLUSION_POLICY_DEFERRED
```

Warnings do not imply HTML entry readiness.

---

## 8. Relationship to P1-M8

P1-M8 HTML export may start only after:

```text
gate_status == HTML_ENTRY_ALLOWED
html_entry_allowed == true
error_count == 0
```

P1-M8 remains private-only and must keep student answer visibility controlled.

---

## 9. Reading System Progress Update

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M5 Private Homework Overlay ........... PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M6 Local Runtime Pipeline ............. COMPLETED_BY_DESIGN
P1-M7 Output Gate ........................ COMPLETED_BY_DESIGN
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 10. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Header exists | PASS | Section 1 |
| Stop condition exists | PASS | Section 1 |
| Inputs defined | PASS | Section 3 |
| Report shape defined | PASS | Section 4 |
| Item result shape defined | PASS | Section 5 |
| HTML entry rule defined | PASS | Section 6 |
| Blocking errors defined | PASS | Section 7 |
| P1-M8 relationship defined | PASS | Section 8 |
| No code implemented | PASS | Documentation-only task |
| No generated artifact committed | PASS | Documentation-only task |
| No HTML generated | PASS | Documentation-only task |
| No promotion performed | PASS | candidate-only boundary |

Task status:

```text
ReadingV1_PrivateHomeworkOutputGate_DesignScan -> COMPLETED_BY_DESIGN
```

---

## 11. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkOutputGate_Implementation
```

唯一執行動作:

```text
建立 OutputGate schema / validator / synthetic gate builder / tests；不產生 HTML。
```
