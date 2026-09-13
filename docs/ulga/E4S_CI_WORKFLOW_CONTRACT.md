# E4S-CI0-M2 CI Workflow Contract

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M2_CIWorkflowContractDesign

Status:
M2_CONTRACT_PATCHED_FOR_IMPACT_SCOPED_ROUTING
```

## 2. Purpose

This contract defines the authoritative GitHub Actions readback workflow for `English_Learning_DB`.

The workflow must provide remote verification without running unrelated Unit or subsystem regressions. The presence of `tests/ci/` is not permission to execute the entire directory for every repository change.

The routing rule is:

```text
changed paths
+ artifact role
+ impact scope
-> minimum required validation
```

Read-only research that does not mutate the repository creates no PR or push and therefore requires no GitHub Actions run.

## 3. Workflow Identity

```text
workflow_file:
.github/workflows/english-db-ci-readback.yml

workflow_name:
English DB CI Readback

primary_job:
validate

impact_classifier:
ulga/validators/validate_pr_workflow_fanout.py

routing_regression:
tests/ci/test_pr_workflow_fanout.py
```

## 4. Triggers

The workflow supports:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

A catch-all event trigger is allowed only because the job performs impact classification before selecting tests. It must not imply catch-all full regression.

`workflow_dispatch` with no changed-path evidence fails safe to `FULL`.

## 5. Runtime Environment

```text
runner: ubuntu-latest
python: 3.11
```

Checkout must use `fetch-depth: 0` so PR/push changed paths can be determined from Git history.

## 6. Impact Classes

The classifier must produce one of these classes:

```text
STORAGE_ONLY
DOCS_ONLY
CI_GOVERNANCE
KET_FOCUSED
UNITnn
FULL
```

### 6.1 STORAGE_ONLY

Use only when every changed path belongs to an explicitly registered storage/evidence root.

Current registered root:

```text
data/ket/
```

This registry is an artifact-role declaration, not a KET-specific routing design. Future Vocabulary, KET99, RAZ-AW, or other evidence roots may be added to the registry only after their storage-only role is established.

Required behavior:

```text
do not run full tests/ci
do not run unrelated Unit tests
perform only lightweight structural/integrity checks when applicable
```

### 6.2 DOCS_ONLY

Use for ordinary documentation-only changes that do not alter CI governance, runtime contracts, schemas, builders, or learner product behavior.

Required behavior:

```text
UTF-8/readability checks
no repository-wide pytest
```

### 6.3 CI_GOVERNANCE

Use for changes to CI workflow/routing governance, including:

```text
.github/workflows/**
docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md
ulga/validators/validate_pr_workflow_fanout.py
tests/ci/test_pr_workflow_fanout.py
```

Required behavior:

```text
run fan-out validator
run tests/ci/test_pr_workflow_fanout.py
do not run unrelated Unit regressions
```

### 6.4 KET_FOCUSED

Use when changes are limited to KET data plus KET-specific validator/test surfaces.

Required behavior:

```text
run tests/ci/test_ket_data_*.py
do not run Unit01-Unit04 regressions
```

### 6.5 UNITnn

Use when every non-document changed path maps to exactly one Unit identity such as `UNIT04`.

Required behavior:

```text
run focused tests for that Unit
if no focused test can be resolved, fail safe to FULL
```

A mixed Unit change such as Unit02 + Unit04 must not be classified as a single Unit.

### 6.6 FULL

Use when the change is shared, mixed, unknown, release-critical, or cannot be safely narrowed.

Typical FULL surfaces include shared builders/runtime/selectors/renderers/scoring, generic shared schemas/contracts, and unknown paths.

Required behavior:

```text
python -m pytest -q tests/ci --durations=30
```

`FULL` is the fail-safe default.

## 7. Required Steps

### 7.1 Checkout

```text
uses: actions/checkout@v4
fetch-depth: 0
```

### 7.2 Setup Python

```text
uses: actions/setup-python@v5
python-version: 3.11
```

### 7.3 Determine Changed Paths

For pull requests, compare PR base SHA to PR head SHA.

For pushes, compare the previous SHA to the current SHA.

For manual dispatch without a usable diff, use an empty path set so classification fails safe to `FULL`.

### 7.4 Classify Impact

The workflow must call:

```text
python ulga/validators/validate_pr_workflow_fanout.py
  --classify-paths-file <changed-path-file>
  --github-output <GITHUB_OUTPUT>
```

The workflow must not duplicate the classifier algorithm in ad-hoc YAML path lists.

### 7.5 Dependency Installation

Heavy repository requirements are not required for `STORAGE_ONLY` or `DOCS_ONLY`.

Scopes that execute pytest may install `requirements.txt`, `pytest`, and `jsonschema`.

### 7.6 Repository Governance File Check

Required files remain:

```text
AGENTS.md
docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/E4S_CI_READBACK_GATE_POLICY.md
docs/ulga/E4S_CI_TEST_SURFACE_INVENTORY.md
docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md
```

Missing required governance files are a failure.

### 7.7 Impact-Scoped Pytest Selection

The previous rule:

```text
if tests/ci exists -> run all tests/ci
```

is superseded.

Required routing:

```text
STORAGE_ONLY
-> no full pytest

DOCS_ONLY
-> no pytest

CI_GOVERNANCE
-> tests/ci/test_pr_workflow_fanout.py

KET_FOCUSED
-> tests/ci/test_ket_data_*.py

UNITnn
-> only focused tests matching that Unit
-> no match => FULL fail-safe

FULL
-> tests/ci
```

No focused lane may silently pass when its required focused test set is empty.

### 7.8 Validators / Builders Discovery

Validator and builder inventory may remain discovery-only unless the selected impact lane explicitly requires one.

### 7.9 CI Summary

The workflow must report:

```text
CI_WORKFLOW=English DB CI Readback
CI_IMPACT_SCOPE=<scope>
CI_IMPACT_REASON=<reason>
CI_CHANGED_PATH_COUNT=<integer>
CI_ROUTE=<selected route>
CI_PYTEST_STATUS=<status>
CI_EXIT_CODE=0 on success
```

## 8. Required PASS Semantics

PASS requires:

```text
impact classification completed
selected route matches the classifier result
all required tests/checks for that route pass
unknown/mixed/shared changes are not incorrectly narrowed
focused test discovery does not silently return zero tests
```

## 9. Required FAIL / Fail-Safe Semantics

The workflow must fail or escalate to FULL when:

```text
impact cannot be determined safely
multiple Unit scopes are changed
a shared/unknown path is present
a focused Unit lane resolves no test targets
a required validator/test exits non-zero
an unexpected routing exception occurs
```

## 10. Scope Exclusions

This FullFix must not:

```text
change Unit01-Unit04 teaching content
change KET S1 segmentation
change Vocabulary/RAZ-AW/KET99 content
change learner runtime
change renderer/scoring/question-bank behavior
create a parallel CI workflow
disable full regression for genuinely shared/runtime changes
```

## 11. Routing Governance

The following three surfaces must stay aligned:

```text
.github/workflows/english-db-ci-readback.yml
ulga/validators/validate_pr_workflow_fanout.py
tests/ci/test_pr_workflow_fanout.py
```

The routing regression must prove at minimum:

```text
registered storage-only change -> STORAGE_ONLY
custom future storage registry -> STORAGE_ONLY
KET data + KET test -> KET_FOCUSED
CI workflow/contract change -> CI_GOVERNANCE
single Unit04 change -> UNIT04
mixed Unit02 + Unit04 -> FULL
shared runtime change -> FULL
unknown path -> FULL
ordinary docs -> DOCS_ONLY
```

## 12. FullFix Acceptance

```text
PASS:
catch-all event trigger no longer means catch-all full pytest
storage/evidence updates do not run unrelated Unit regression
single-Unit updates use focused Unit tests
shared/mixed/unknown changes fail safe to FULL
workflow, contract, classifier, and routing regression agree
no learner/product content changed
```
