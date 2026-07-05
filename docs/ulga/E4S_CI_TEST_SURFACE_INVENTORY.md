# E4S-CI0-M1 Current Test Surface Inventory

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M1_CurrentTestSurfaceInventory

Status:
M1_INVENTORY_CREATED

Previous Gate:
E4S-CI0-M0_ScopeGovernanceLock -> COMPLETED
```

## 2. Purpose

This inventory identifies the current CI-eligible verification surfaces for `English_Learning_DB` before implementing a GitHub Actions workflow.

The goal is not to invent new tests. The goal is to document what the first CI workflow can safely validate without expanding into ReadingV1, GrammarSkillTree, RAZ processing, or generated-content promotion.

## 3. Data Sources Inspected

Directly fetched repository files:

```text
AGENTS.md
docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/E4S_CI_READBACK_GATE_POLICY.md
```

Connector probes attempted:

```text
GitHub code search: pytest
GitHub code search: tests
GitHub code search: validator
GitHub code search: build_
GitHub code search: jsonschema
Fetch .github/workflows/english-db-ci-readback.yml
```

Probe result note:

```text
The GitHub connector did not return indexed search results for the generic probes above.
This must not be interpreted as proof that no tests, validators, or builders exist.
It only means M1 cannot rely on code-search enumeration as complete evidence.
```

## 4. Confirmed Project Verification Requirements

The repository root governance says this repository is the private authority database for:

```text
English learning materials
ULGA graph
RAZ corpus processing
tag registry
validators
content authority reports
```

Therefore the CI workflow should be designed for a Python / JSON / authority-artifact repository, not for a single npm-based application.

The repository governance also requires every task to close one approved milestone only and not expand a Grammar task into Reading, Writing, Listening, Speaking, adaptive learning, public site work, or commercial worksheet export unless the epic is explicitly changed.

The existing CI evidence rule already distinguishes:

```text
PASS_CI_SYNCED_AND_CLEAN
PASS_LOCAL_ONLY_CI_NOT_VERIFIED
DOCS_ONLY_CI_NOT_VERIFIED
```

The English Grammar governance requires CI readback fields when CI evidence is available:

```text
workflow status = completed
workflow conclusion = success
test command = PASS
test exit code = 0
working tree = clean, if confirmed
```

## 5. CI-eligible Verification Surfaces for First Workflow

### 5.1 Repository Text / Markdown Documentation Check

Recommended for M3 first workflow:

```text
Check that required governance docs exist.
Check that CI0 docs exist after each CI0 stage.
Check markdown files are readable as UTF-8.
```

Initial required docs:

```text
AGENTS.md
docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/E4S_CI_READBACK_GATE_POLICY.md
docs/ulga/E4S_CI_TEST_SURFACE_INVENTORY.md
```

### 5.2 JSON Integrity Check

Recommended for M3 first workflow:

```text
Recursively parse *.json under known project artifact directories when those directories exist.
Do not fail when a directory is absent.
Fail only when a discovered JSON file cannot be parsed.
```

Candidate directories:

```text
ulga/
raz_output_jsons/
docs/
```

Rationale:

```text
This project contains authority artifacts and generated reports. JSON syntax integrity is a safe, low-risk remote validation gate.
```

### 5.3 Python Test Discovery

Recommended for M3 first workflow:

```text
If tests/ exists, run pytest -q.
If tests/ does not exist, print a clear no-tests-discovered message and continue.
```

M1 must not create new tests only to satisfy CI.

### 5.4 Validator Smoke Discovery

Recommended for M3 first workflow:

```text
If ulga/validators/ exists, list validator files.
Do not execute unknown validators blindly in the first workflow.
Only execute validators later when M2/M3 contract explicitly maps command semantics.
```

Rationale:

```text
The project contains multiple authority lines. Running every validator blindly could trigger unrelated requirements or generated-artifact expectations.
```

### 5.5 Builder Smoke Discovery

Recommended for M3 first workflow:

```text
If ulga/builders/ exists, list builder files.
Do not execute builders in first CI unless a safe smoke mode is documented.
```

Rationale:

```text
Builders may generate large artifacts. The project-wide generated artifact policy says large generated artifacts must not be committed by default.
```

### 5.6 Workflow Presence Check

Recommended for M3 first workflow after implementation:

```text
.github/workflows/english-db-ci-readback.yml must exist.
```

At M1 time, this file was not present.

## 6. Items CI Must Not Do Yet

The first CI workflow must not:

```text
run all builders blindly
commit generated artifacts
promote candidate data
require ReadingV1 artifacts that are not part of CI0
require GrammarSkillTree pilot artifacts unless the current task is R4/R5/R6
run public site deployment
require npm test unless a package.json-based surface is explicitly inventoried later
```

## 7. M1 Gate Check

```text
PASS: existing governance sources were inspected.
PASS: current CI evidence requirements were identified.
PASS: code-search enumeration limitation was recorded as a warning, not hidden.
PASS: first-workflow verification surfaces were defined without requiring nonexistent tests.
PASS: JSON integrity was classified as the safest universal first gate.
PASS: pytest was defined as conditional discovery, not mandatory existence.
PASS: validators/builders were classified as discovery-only until safe commands are contracted.
PASS: no ReadingV1, HTML, adaptive, or generated-content feature work was added.
```

## 8. Warning Register

```text
warning_id: E4S-CI0-M1-W1
severity: medium
affected_area: repository enumeration
classification: CURRENT_TASK_WARNING
summary: GitHub connector code search returned no generic test/validator/builder results, so M1 cannot claim a complete file-level inventory.
why_non_blocking: M1 can still define safe first-workflow surfaces using fetched governance files and conditional discovery logic.
recommended_future_task: E4S-CI0-M3 should implement runtime directory discovery inside GitHub Actions.
blocks_current_task: no
```

## 9. Distance Vector

```text
Epic:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Completed Middle Tasks:
E4S-CI0-M0
E4S-CI0-M1

Remaining Middle Tasks:
E4S-CI0-M2
E4S-CI0-M3
E4S-CI0-M4
E4S-CI0-M5
E4S-CI0-M6
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 7
```

## 10. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M2_CIWorkflowContractDesign

Unique execution action:
Write docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md defining the first English_Learning_DB GitHub Actions workflow contract before implementing .github/workflows/english-db-ci-readback.yml.
```
