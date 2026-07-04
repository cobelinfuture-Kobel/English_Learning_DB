# Reading V1 P1 Task Sequence Reference

```text
Canonical reference file: docs/ulga/READING_V1_P1_TASK_SEQUENCE_REFERENCE.md
Epic ID: P1-ReadingV1_CambridgeAlignedPrivateHomeworkPracticeSystem
Chinese name: Reading V1 劍橋對齊家庭私有練習系統
Status owner: operator / ChatGPT / Codex handoff
Task mode: sequential, gated, anti-scope-creep
```

This file is the required task-order reference for every future Reading V1 P1 handoff.

Every Reading V1 P1 task must read this file before execution, cite it in the task's data-source/readback section, check the current task order, and report completion distance at the end.

---

## 1. Epic Definition

### 1.1 Epic Goal

Build a Cambridge / CEFR / YLE-aligned, RAZ-source-grounded, ULGA-controlled Reading V1 private homework practice system.

The P1 system must produce a validated PracticeBank and local/private homework HTML output while preserving source traceability and blocking public/commercial export.

### 1.2 P1 Scope

P1 includes:

```text
Cambridge / CEFR / YLE-aligned Reading V1 scope
Private homework policy constraints
PracticeBank schema and implementation
Private homework candidate overlay
Local runtime / in-memory source pipeline
Private homework output gate
Local/private HTML practice export
P1 closeout QA
```

### 1.3 Explicitly Out of Scope

P1 must not implement:

```text
P2 assessment pattern expansion
Cambridge formal exam full mapping
Adaptive learning
Learner error tagging / weak-point diagnosis
Listening
Speaking
Writing
Student app
GitHub Pages public practice site
Commercial worksheet package
Bulk RAZ source-text database
```

---

## 2. Mandatory Handoff Rule

Every future Reading V1 P1 task must begin with this check:

```text
TASK_SEQUENCE_REFERENCE_READ = docs/ulga/READING_V1_P1_TASK_SEQUENCE_REFERENCE.md
TASK_SEQUENCE_REFERENCE_STATUS = PASS / FAIL
CURRENT_MIDDLE_TASK = P1-Mx
CURRENT_SMALL_TASK = P1-Mx-Sy
ORDER_ALIGNMENT = PASS / FAIL
ANTI_SCOPE_CREEP_CHECK = PASS / FAIL
```

Every future Reading V1 P1 task must end with this report:

```text
CURRENT_TASK_STATUS = COMPLETED / PARTIAL / FAILED / BLOCKED
MIDDLE_TASK_PROGRESS = xx%
P1_OVERALL_PROGRESS = xx%
D_MID = n middle tasks left
D_SMALL = n small tasks left
NEXT_SHORT_STEP = one exact next task only
```

No task may skip this file unless the operator explicitly replaces the roadmap with a newer canonical reference.

---

## 3. Progress Metrics

Progress is measured by Reading V1 system readiness, not by number of conversations.

Required progress dimensions:

```text
Governance / Scope Lock
Policy / Private Homework Safety
Cambridge Spiral Scope
PracticeBank Contract
PracticeBank Implementation
Private Homework Candidate Overlay
Local Runtime / In-Memory Pipeline
Private Homework Output Gate
HTML Practice Export
P1 Closeout QA
```

Each dimension uses one of these states:

```text
NOT_STARTED
IN_PROGRESS
PARTIAL_DONE
MOSTLY_DONE
COMPLETE
BLOCKED
```

---

## 4. Current Progress Snapshot

```text
P1-M0 Governance / Scope Lock ...................... PARTIAL_DONE
P1-M1 Policy & Private Homework Safety Foundation .. MOSTLY_DONE
P1-M2 Cambridge Spiral Scope Definition ............ NOT_STARTED
P1-M3 PracticeBank Contract ........................ NOT_STARTED
P1-M4 PracticeBank Implementation .................. NOT_STARTED
P1-M5 Private Homework Candidate Overlay ........... NOT_STARTED
P1-M6 Local Runtime / In-Memory Source Pipeline .... NOT_STARTED
P1-M7 Private Homework Output Gate ................. NOT_STARTED
P1-M8 HTML Practice Export ......................... NOT_STARTED
P1-M9 P1 Closeout QA ............................... NOT_STARTED
```

Current distance vector:

```text
D_MID = 8 middle tasks left
D_SMALL = approximately 72 small tasks left
P1_OVERALL_PROGRESS = 20%
```

Reasoning for current progress:

```text
P1-M0 is partial because the task tree and handoff rule are now defined, but not yet embedded into all future task templates.
P1-M1 is mostly done because private homework and pattern-based policy foundations already exist, but PolicyOverlay_ReadbackQA / test-plan work may still be added later.
P1-M2 through P1-M9 are not started as executable milestones under this canonical sequence.
```

---

## 5. Task Sequence

The task order is strict unless the operator explicitly approves a reorder.

```text
P1-M0  Governance / Scope Lock
P1-M1  Policy & Private Homework Safety Foundation
P1-M2  Cambridge Spiral Scope Definition
P1-M3  PracticeBank Contract
P1-M4  PracticeBank Implementation
P1-M5  Private Homework Candidate Overlay
P1-M6  Local Runtime / In-Memory Source Pipeline
P1-M7  Private Homework Output Gate
P1-M8  HTML Practice Export
P1-M9  P1 Closeout QA
```

The next active task is:

```text
NEXT_SHORT_STEP = ReadingV1_CambridgeSpiralScope_DesignScan
```

---

## 6. Middle Tasks and Small Tasks

### P1-M0 Governance / Scope Lock

Purpose:

```text
Lock P1 to Reading V1 and prevent expansion into P2 or later phases.
```

Small tasks:

```text
P1-M0-S1  Define P1 Epic ID / Chinese name / goal
P1-M0-S2  Define P1 out-of-scope list
P1-M0-S3  Define Reading System progress dimensions
P1-M0-S4  Define per-task Gate / Distance report format
P1-M0-S5  Define NEXT_SHORT_STEP rule
P1-M0-S6  Write this canonical task sequence reference
```

Gate:

```text
PASS: P1 objective is explicit
PASS: P2+ is deferred
PASS: future tasks must report progress against Reading V1 readiness
PASS: this file exists in docs/ulga
```

Status:

```text
PARTIAL_DONE
```

---

### P1-M1 Policy & Private Homework Safety Foundation

Purpose:

```text
Allow private homework use only under local/private constraints while blocking public, commercial, GitHub Pages, and bulk source-text storage paths.
```

Small tasks:

```text
P1-M1-S1  RAZ_PrivateHomeworkUsePolicy_DesignScan
P1-M1-S2  RAZ_PatternBasedPrivateHomeworkPolicy_DesignScan
P1-M1-S3  Machine-readable private homework policy overlay JSON
P1-M1-S4  ReadingV1_PrivateHomeworkPolicyOverlay_DesignScan
P1-M1-S5  PolicyOverlay_ReadbackQA
P1-M1-S6  PolicyOverlay_TestPlan_DesignScan
```

Gate:

```text
PASS: public payload display remains blocked
PASS: private homework is local runtime only
PASS: persistent repo state is locator / metadata / policy flags only
PASS: GitHub Pages is blocked
PASS: commercial export is blocked
PASS: bulk RAZ source-text database is blocked
PASS: candidate queue is not destructively modified
```

Status:

```text
MOSTLY_DONE
```

---

### P1-M2 Cambridge Spiral Scope Definition

Canonical task name:

```text
ReadingV1_CambridgeSpiralScope_DesignScan
```

Purpose:

```text
Define the Reading V1 learning standard before PracticeBank generation.
```

Small tasks:

```text
P1-M2-S1   Define ReadingV1 level stages
P1-M2-S2   Define grammar focus per stage
P1-M2-S3   Define sentence patterns per stage
P1-M2-S4   Define vocabulary band per stage
P1-M2-S5   Define chunk policy per stage
P1-M2-S6   Define theme / situation scope per stage
P1-M2-S7   Define Reading V1 question-type scope
P1-M2-S8   Define spiral rule: old knowledge + small new knowledge
P1-M2-S9   Define html_ready conditions
P1-M2-S10  Define validator requirements
```

Required deliverable:

```text
docs/ulga/READING_V1_CAMBRIDGE_SPIRAL_SCOPE_DESIGN_SCAN.md
```

Gate:

```text
PASS: each stage has grammar / pattern / vocabulary / chunk / theme / question_type
PASS: Cambridge / CEFR / YLE role is clearly defined
PASS: CEFR is not treated as the only learning path
PASS: no P2 formal assessment expansion is included
PASS: no PracticeBank is generated in this task
```

Status:

```text
NOT_STARTED
```

---

### P1-M3 PracticeBank Contract

Canonical task name:

```text
ReadingV1_PrivateHomeworkPracticeBank_DesignScan
```

Purpose:

```text
Define the Reading V1 PracticeBank schema and validation contract.
```

Small tasks:

```text
P1-M3-S1   Define PracticeBank root schema
P1-M3-S2   Define practice_item_id rule
P1-M3-S3   Define source_mode values
P1-M3-S4   Define required practice item fields
P1-M3-S5   Define V1 question-type whitelist
P1-M3-S6   Define html_ready rules
P1-M3-S7   Define private_homework_only flags
P1-M3-S8   Define forbidden fields
P1-M3-S9   Define summary schema
P1-M3-S10  Define validator contract
```

Required deliverable:

```text
docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_CONTRACT.md
```

Gate:

```text
PASS: PracticeBank schema is complete
PASS: V1 question type scope is enforced
PASS: source trace / answer model / validator fields exist
PASS: persistent RAZ source text is forbidden
PASS: P2 question types are excluded
```

Status:

```text
NOT_STARTED
```

---

### P1-M4 PracticeBank Implementation

Canonical task name:

```text
ReadingV1_PrivateHomeworkPracticeBank_Implementation
```

Purpose:

```text
Create the first validated Reading V1 private homework PracticeBank.
```

Small tasks:

```text
P1-M4-S1   Build PracticeBank builder
P1-M4-S2   Create 12-item smoke PracticeBank
P1-M4-S3   Attach Cambridge spiral stage to each item
P1-M4-S4   Attach grammar_focus to each item
P1-M4-S5   Attach pattern_id / pattern_text to each item
P1-M4-S6   Attach vocabulary / chunk references
P1-M4-S7   Create question_text / answer_key / answer_model
P1-M4-S8   Create PracticeBank summary
P1-M4-S9   Create validator
P1-M4-S10  Create tests
```

Required deliverables:

```text
tools/build_reading_v1_private_homework_practice_bank.py
ulga/reports/reading_v1_private_homework_practice_bank.json
ulga/reports/reading_v1_private_homework_practice_bank_summary.json
tests/test_build_reading_v1_private_homework_practice_bank.py
```

Gate:

```text
PASS: practice_item_count >= 12
PASS: html_ready_count >= 12
PASS: source_text_stored = false
PASS: source_payload_copied = false
PASS: github_pages_allowed = false
PASS: commercial_use_allowed = false
PASS: validator PASS
```

Status:

```text
NOT_STARTED
```

---

### P1-M5 Private Homework Candidate Overlay

Canonical task name:

```text
ReadingV1_PrivateHomeworkOverlayArtifact_Implementation
```

Purpose:

```text
Create an external private-homework overlay artifact without destructively modifying base candidate records.
```

Small tasks:

```text
P1-M5-S1   Build overlay builder
P1-M5-S2   Read private homework policy overlay JSON
P1-M5-S3   Read Reading V1 candidate / PracticeBank artifacts
P1-M5-S4   Create overlay_records
P1-M5-S5   Set overlay_status
P1-M5-S6   Set evidence_text_persistence_allowed = false
P1-M5-S7   Set runtime_materialization_allowed = true
P1-M5-S8   Create overlay summary
P1-M5-S9   Create validator
P1-M5-S10  Create tests
```

Required deliverables:

```text
tools/build_reading_v1_private_homework_candidate_overlay.py
ulga/reports/reading_v1_private_homework_candidate_overlay.json
ulga/reports/reading_v1_private_homework_candidate_overlay_summary.json
tests/test_build_reading_v1_private_homework_candidate_overlay.py
```

Gate:

```text
PASS: overlay artifact contains no source text
PASS: base candidate queue is not destructively updated
PASS: target_env = local_homework_print
PASS: repo_visibility = private
PASS: not_for_public_export = true
PASS: not_for_commercial_distribution = true
```

Status:

```text
NOT_STARTED
```

---

### P1-M6 Local Runtime / In-Memory Source Pipeline

Canonical task names:

```text
P1-M6A ReadingV1_LocalRuntimeInMemoryPipeline_DesignScan
P1-M6B ReadingV1_LocalRuntimeInMemoryPipeline_Implementation
```

Purpose:

```text
Enable local/private runtime materialization without committing protected source text back to GitHub.
```

Small tasks:

```text
P1-M6-S1   Define local source folder contract
P1-M6-S2   Define source locator -> local file resolver
P1-M6-S3   Define operator attestation file
P1-M6-S4   Define runtime materialization object
P1-M6-S5   Define max_excerpt_lines enforcement
P1-M6-S6   Implement local runtime loader
P1-M6-S7   Implement in-memory merge with quiz metadata
P1-M6-S8   Block materialized source text from repo writes
P1-M6-S9   Create local-only smoke output
P1-M6-S10  Create tests
```

Required deliverables:

```text
docs/ulga/READING_V1_LOCAL_RUNTIME_IN_MEMORY_PIPELINE_DESIGN_SCAN.md
tools/build_reading_v1_local_runtime_materialization.py
tests/test_reading_v1_local_runtime_materialization.py
```

Gate:

```text
PASS: repo stores only locator / metadata / quiz metadata / policy flags
PASS: local runtime reads operator-provided local source only after attestation
PASS: materialized source text is not committed to GitHub
PASS: materialized source text is not uploaded to GitHub Pages
PASS: target_env is local_homework_print only
```

Status:

```text
NOT_STARTED
```

---

### P1-M7 Private Homework Output Gate

Canonical task names:

```text
P1-M7A ReadingV1_PrivateHomeworkHTMLOutputGate_DesignScan
P1-M7B ReadingV1_PrivateHomeworkHTMLOutputGate_Implementation
```

Purpose:

```text
Prevent private homework output from being exported to public, commercial, or GitHub Pages targets.
```

Small tasks:

```text
P1-M7-S1   Define target_env enum
P1-M7-S2   Define blocked target environments
P1-M7-S3   Define allowed target environment: local_homework_print
P1-M7-S4   Define validate_output_gate()
P1-M7-S5   Check policy flags
P1-M7-S6   Check not_for_public_export
P1-M7-S7   Check protected source marker
P1-M7-S8   Raise PermissionError on violations
P1-M7-S9   Create tests
P1-M7-S10  Create fail cases
```

Required deliverables:

```text
tools/reading_v1_private_homework_output_gate.py
tests/test_reading_v1_private_homework_output_gate.py
```

Gate:

```text
PASS: local_homework_print is allowed
PASS: github_pages is blocked
PASS: public_site is blocked
PASS: public_preview is blocked
PASS: commercial_worksheet is blocked
PASS: blocked case raises PermissionError
```

Status:

```text
NOT_STARTED
```

---

### P1-M8 HTML Practice Export

Canonical task name:

```text
ReadingV1_PrivateHomeworkHTMLExport_Implementation
```

Purpose:

```text
Create local/private Reading V1 homework HTML practice output.
```

Small tasks:

```text
P1-M8-S1   Define HTML template
P1-M8-S2   Render practice items
P1-M8-S3   Render question_text
P1-M8-S4   Render answer field / options
P1-M8-S5   Render answer key section
P1-M8-S6   Render level / theme / grammar / pattern tags
P1-M8-S7   Render private homework notice
P1-M8-S8   Connect output gate
P1-M8-S9   Create smoke HTML
P1-M8-S10  Create renderer tests
```

Required deliverables:

```text
tools/export_reading_v1_private_homework_html.py
output/reading_v1/private_homework/reading_v1_private_homework_smoke.html
tests/test_export_reading_v1_private_homework_html.py
```

Gate:

```text
PASS: HTML opens locally
PASS: HTML renders >= 12 items
PASS: answer key exists
PASS: private homework notice exists
PASS: no GitHub Pages flag
PASS: no commercial flag
PASS: output gate PASS
```

Status:

```text
NOT_STARTED
```

---

### P1-M9 P1 Closeout QA

Canonical task name:

```text
ReadingV1_P1_PrivateHomework_CloseoutQA
```

Purpose:

```text
Confirm that P1 is a usable private homework Reading V1 system, not just a policy layer.
```

Small tasks:

```text
P1-M9-S1   Check PracticeBank count
P1-M9-S2   Check Cambridge spiral scope coverage
P1-M9-S3   Check grammar / pattern / vocabulary / chunk / theme tags
P1-M9-S4   Check validator PASS
P1-M9-S5   Check HTML output PASS
P1-M9-S6   Check public targets are blocked
P1-M9-S7   Check repo contains no RAZ raw text / full passage
P1-M9-S8   Check no P2 leakage
P1-M9-S9   Create closeout report
P1-M9-S10  Update Reading System Progress
```

Required deliverables:

```text
docs/ulga/READING_V1_P1_PRIVATE_HOMEWORK_CLOSEOUT_QA.md
ulga/reports/reading_v1_p1_private_homework_closeout_summary.json
```

Gate:

```text
PASS: practice_item_count >= 12
PASS: html_ready_count >= 12
PASS: local_html_export = PASS
PASS: public_export = BLOCKED
PASS: github_pages = BLOCKED
PASS: commercial_use = BLOCKED
PASS: source_text_stored = false
PASS: source_payload_copied = false
PASS: validator = PASS
PASS: P1_COMPLETE = true
```

Status:

```text
NOT_STARTED
```

---

## 7. Required Handoff Template

Every future Reading V1 P1 response must include this block:

```text
## Reading V1 P1 Handoff Check

TASK_SEQUENCE_REFERENCE_READ = PASS / FAIL
TASK_SEQUENCE_REFERENCE_PATH = docs/ulga/READING_V1_P1_TASK_SEQUENCE_REFERENCE.md
CURRENT_EPIC = P1-ReadingV1_CambridgeAlignedPrivateHomeworkPracticeSystem
CURRENT_MIDDLE_TASK = P1-Mx
CURRENT_SMALL_TASK = P1-Mx-Sy
ORDER_ALIGNMENT = PASS / FAIL
ANTI_SCOPE_CREEP_CHECK = PASS / FAIL

## Gate Metrics

[PASS/FAIL] deliverable created or updated
[PASS/FAIL] scope matched current task only
[PASS/FAIL] no P2 leakage
[PASS/FAIL] no public/export violation
[PASS/FAIL] validation/test status reported honestly

## Distance Vector

MIDDLE_TASK_PROGRESS = xx%
P1_OVERALL_PROGRESS = xx%
D_MID = n middle tasks left
D_SMALL = n small tasks left
CURRENT_TASK_STATUS = COMPLETED / PARTIAL / FAILED / BLOCKED
NEXT_SHORT_STEP = exact next task only
```

---

## 8. Current Next Step

```text
NEXT_SHORT_STEP = ReadingV1_CambridgeSpiralScope_DesignScan
```

Allowed next deliverable:

```text
docs/ulga/READING_V1_CAMBRIDGE_SPIRAL_SCOPE_DESIGN_SCAN.md
```

Forbidden in the next task:

```text
Do not generate PracticeBank.
Do not write HTML exporter.
Do not implement runtime pipeline.
Do not add P2 assessment pattern expansion.
Do not create public learner-facing output.
```

---

## 9. Change Control

This roadmap may be updated only by an explicit operator-approved roadmap update task.

If updated, the task must report:

```text
ROADMAP_FILE_UPDATED = true
OLD_NEXT_SHORT_STEP = ...
NEW_NEXT_SHORT_STEP = ...
D_MID_BEFORE = ...
D_MID_AFTER = ...
D_SMALL_BEFORE = ...
D_SMALL_AFTER = ...
REORDER_APPROVED_BY_OPERATOR = true / false
```

Without explicit approval, the sequence in this file remains authoritative.
