# E4S-CI0-M2 CI Workflow Contract

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M2_CIWorkflowContractDesign

Status:
M2_CONTRACT_CREATED

Previous Gates:
E4S-CI0-M0_ScopeGovernanceLock -> COMPLETED
E4S-CI0-M1_CurrentTestSurfaceInventory -> COMPLETED_WITH_WARNING
```

## 2. Purpose

This contract defines the first GitHub Actions workflow for `English_Learning_DB`.

The workflow must provide remote CI readback evidence without expanding into unrelated feature work or requiring unavailable tests.

## 3. Workflow Identity

```text
workflow_file:
.github/workflows/english-db-ci-readback.yml

workflow_name:
English DB CI Readback

primary_job:
validate
```

## 4. Triggers

The workflow must support:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

Rationale:

```text
push: validates main updates
pull_request: validates future branch/PR work
workflow_dispatch: allows manual CI readback for long-task gates
```

## 5. Runtime Environment

```text
runner:
ubuntu-latest

python:
3.11

node:
not required in M3 unless a package.json surface is later inventoried
```

## 6. Dependency Policy

The workflow must:

```text
upgrade pip
install requirements.txt only if present
install pytest
```

It may install:

```text
jsonschema
```

It must not install heavy or unrelated dependencies without a later contract patch.

## 7. Required Steps

### 7.1 Checkout

```text
uses: actions/checkout@v4
```

### 7.2 Setup Python

```text
uses: actions/setup-python@v5
python-version: 3.11
```

### 7.3 Install Dependencies

Required behavior:

```text
python -m pip install --upgrade pip
if requirements.txt exists, pip install -r requirements.txt
pip install pytest jsonschema
```

### 7.4 Repository Governance File Check

Required files:

```text
AGENTS.md
docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/E4S_CI_READBACK_GATE_POLICY.md
docs/ulga/E4S_CI_TEST_SURFACE_INVENTORY.md
docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md
```

Fail condition:

```text
Any required file missing.
```

### 7.5 UTF-8 Markdown Readability Check

Required behavior:

```text
Recursively read *.md files under docs/ and root governance files.
Fail on UTF-8 read error.
```

Rationale:

```text
The current CI0 line is documentation-heavy. Readability is a valid docs-only remote gate.
```

### 7.6 JSON Integrity Check

Required behavior:

```text
Scan known roots only if they exist:
- ulga/
- raz_output_jsons/
- docs/

Parse every discovered *.json file as UTF-8 JSON.
Print json_checked and json_failed.
Fail if json_failed > 0.
```

Allowed behavior:

```text
If a root directory does not exist, skip it without failure.
```

### 7.7 Pytest Conditional Discovery

Required behavior:

```text
If tests/ exists, run pytest -q.
If tests/ does not exist, print CI_PYTEST_STATUS=SKIPPED_NO_TESTS_DIR and continue.
```

Fail condition:

```text
pytest exits non-zero when tests/ exists.
```

### 7.8 Validators Discovery

Required behavior:

```text
If ulga/validators/ exists, list *.py validator files.
Do not execute validators in M3 unless a validator command contract is later added.
```

### 7.9 Builders Discovery

Required behavior:

```text
If ulga/builders/ exists, list *.py builder files.
Do not execute builders in M3.
```

Rationale:

```text
Builders may generate artifacts. M3 must not violate generated artifact policy.
```

### 7.10 CI Summary Output

The workflow must print these fields:

```text
CI_WORKFLOW=English DB CI Readback
CI_GOVERNANCE_FILES_STATUS=PASS/FAIL
CI_MARKDOWN_UTF8_STATUS=PASS/FAIL
CI_JSON_STATUS=PASS/FAIL
CI_JSON_CHECKED=<integer>
CI_JSON_FAILED=<integer>
CI_PYTEST_STATUS=PASS/FAIL/SKIPPED_NO_TESTS_DIR
CI_VALIDATOR_DISCOVERY_STATUS=PASS/SKIPPED_NO_VALIDATOR_DIR
CI_BUILDER_DISCOVERY_STATUS=PASS/SKIPPED_NO_BUILDER_DIR
CI_EXIT_CODE=0 if all required gates pass
```

## 8. Required PASS Semantics

The workflow is considered PASS only when:

```text
governance file check passes
markdown UTF-8 readability passes
JSON integrity passes
pytest passes or is explicitly skipped because tests/ does not exist
validator discovery passes or is explicitly skipped because ulga/validators/ does not exist
builder discovery passes or is explicitly skipped because ulga/builders/ does not exist
```

## 9. Required FAIL Semantics

The workflow must fail when:

```text
required governance file missing
markdown UTF-8 read failure
invalid JSON discovered
pytest failure when tests/ exists
unexpected script exception
```

The workflow must not fail only because:

```text
tests/ does not exist
ulga/validators/ does not exist
ulga/builders/ does not exist
optional artifact root does not exist
```

## 10. Scope Exclusions

M3 implementation must not:

```text
run all builders
run all unknown validators
commit generated artifacts
create ReadingV1 practice data
create learner-facing output
create public deployment
require npm test
add new tests solely to satisfy CI
```

## 11. M2 Gate Check

```text
PASS: workflow file path is defined.
PASS: workflow name is defined.
PASS: triggers include push, pull_request, and workflow_dispatch.
PASS: runtime environment is Python-first.
PASS: governance file check is required.
PASS: markdown UTF-8 readability check is required.
PASS: JSON integrity check is required.
PASS: pytest is conditional, not forced.
PASS: validators/builders are discovery-only in first implementation.
PASS: fail/pass semantics are explicit.
PASS: no ReadingV1, HTML, adaptive, generated-content, or deployment scope was added.
```

## 12. Distance Vector

```text
Epic:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Completed Middle Tasks:
E4S-CI0-M0
E4S-CI0-M1
E4S-CI0-M2

Remaining Middle Tasks:
E4S-CI0-M3
E4S-CI0-M4
E4S-CI0-M5
E4S-CI0-M6
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 6
```

## 13. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M3_CIWorkflowImplementation

Unique execution action:
Create .github/workflows/english-db-ci-readback.yml according to this contract.
```
