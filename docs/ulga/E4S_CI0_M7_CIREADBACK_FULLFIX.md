# E4S-CI0-M7 CI Readback FullFix

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Task:
E4S-CI0-M7_CIReadback_FullFix

Status:
FULLFIX_APPLIED_PENDING_CI_RERUN_READBACK

Blocked Parent Task:
E4S-CI0-M7_PilotCIRunReadbackQA
```

## 2. Failure Evidence

Operator-provided CI log evidence:

```text
failed_step:
Run pytest when tests directory exists

failed_command:
pytest -q

error_type:
ModuleNotFoundError

error_excerpt:
ImportError while importing tests/test_raz_reversed_anomaly.py
from tools.raz.build_raz_a_reference_sentences import (...)
tools/raz/build_raz_a_reference_sentences.py imports pandas as pd
ModuleNotFoundError: No module named 'pandas'

exit_code:
2
```

## 3. Root Cause

The CI workflow correctly runs `pytest -q` when the `tests/` directory exists.

The test module imports `tools/raz/build_raz_a_reference_sentences.py`. That builder imports `pandas` at module load time.

The first CI workflow installed:

```text
pytest
jsonschema
```

and installed `requirements.txt` only if present. At the time of the failure, no `requirements.txt` existed in the repository, so `pandas` was not installed in CI.

## 4. Scope Classification

```text
classification:
CURRENT_TASK_BLOCKER

why:
M7 cannot close because CI pytest collection fails before tests can run.

fix type:
Scoped CI dependency FullFix
```

## 5. Files Changed

```text
requirements.txt
```

## 6. Fix Applied

Created `requirements.txt` with CI/runtime dependencies needed by the current RAZ builder import surface:

```text
pandas>=2.2,<3
openpyxl>=3.1,<4
```

Rationale:

```text
pandas is directly required by tools/raz/build_raz_a_reference_sentences.py.
openpyxl is included because the same builder uses Excel workbook inputs/outputs through pandas, and pandas requires an Excel engine for .xlsx read/write surfaces.
```

## 7. Files Not Changed

```text
No tests changed.
No RAZ builder logic changed.
No validators changed.
No generated artifacts committed.
No ReadingV1 feature work added.
No learner-facing output added.
No promotion performed.
```

## 8. Required Re-run

The same GitHub Actions workflow must be re-run or triggered by the new commit.

Required PASS evidence:

```text
workflow_name = English DB CI Readback
workflow_status = completed
workflow_conclusion = success
run_url = recorded
CI_PYTEST_STATUS = PASS
CI_JSON_STATUS = PASS
CI_EXIT_CODE = 0
```

## 9. Gate Result

```text
PASS: CI-blocking pandas dependency gap was fixed inside current scope.
PASS: requirements.txt now exists for workflow dependency installation.
PASS: no out-of-scope feature or artifact work was added.
PENDING: CI rerun readback evidence.
```

## 10. Distance Vector

```text
Epic:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Completed Middle Tasks:
E4S-CI0-M0
E4S-CI0-M1
E4S-CI0-M2
E4S-CI0-M3
E4S-CI0-M4
E4S-CI0-M5
E4S-CI0-M6

Blocked / Active Middle Task:
E4S-CI0-M7

Current FullFix:
E4S-CI0-M7_CIReadback_FullFix -> APPLIED_PENDING_CI_RERUN

Remaining Middle Tasks:
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 2
```

## 11. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M7_CIReadback_RerunAfterDependencyFullFix

Unique execution action:
Read the GitHub Actions run for the commit that added requirements.txt and confirm whether English DB CI Readback passes.
```
