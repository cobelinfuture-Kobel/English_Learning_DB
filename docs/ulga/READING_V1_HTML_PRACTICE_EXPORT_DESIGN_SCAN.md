# ReadingV1 HTML Practice Export Design Scan

Task:
ReadingV1_HTMLPracticeExport_DesignScan

Scope:
Define the private page export contract after OutputGate PASS.

Allowed files:
- docs/ulga/READING_V1_HTML_PRACTICE_EXPORT_DESIGN_SCAN.md

Forbidden files:
- code
- tests
- generated page files
- public delivery files
- promotion artifacts

Status:
Documentation-only.

Stop condition:
- define page inputs
- define student view boundary
- define parent view boundary
- define render-entry checks
- do not implement code
- do not generate files

---

## 1. Purpose

P1-M8 defines how an OutputGate-approved ReadingV1 package may enter a private local page renderer.

This stage is still private-only and candidate-only.

---

## 2. Required Inputs

```text
OutputGate report
Overlay package
runtime display payload references
render policy
operator local context
```

Required status:

```text
gate_status == HTML_ENTRY_ALLOWED
html_entry_allowed == true
error_count == 0
```

---

## 3. Page Contract

Student view may show:

```text
instruction
question prompt
runtime display text
answer blank
choice list if available
```

Student view must not show:

```text
answer key
teacher evidence
internal locator
validator internals
promotion metadata
```

Parent or teacher view may show answer references when policy allows.

---

## 4. Render Checks

Before rendering:

```text
OutputGate PASS
private_homework_only true
public_ready false
local_private_homework_only mode
student answer key hidden
all selected items allowed
```

If any check fails, renderer returns blocked status and no page body.

---

## 5. Future Implementation

Recommended files:

```text
ulga/renderers/render_reading_v1_private_homework_html.py
ulga/validators/validate_reading_v1_html_export.py
tests/ulga/test_reading_v1_html_practice_export.py
```

First implementation should return a page string in memory for tests and should not write page files by default.

---

## 6. Progress

```text
P1-M7 PASS_WITH_LOCAL_SCRATCH_VALIDATION
P1-M8 COMPLETED_BY_DESIGN
P1-M9 NOT_STARTED
```

Task status:

```text
ReadingV1_HTMLPracticeExport_DesignScan -> COMPLETED_BY_DESIGN
```

Next:

```text
ReadingV1_HTMLPracticeExport_Implementation
```
