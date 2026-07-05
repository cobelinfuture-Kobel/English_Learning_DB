# E4S-CI0-M7 CI Readback FullFix — Import Path

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Task:
E4S-CI0-M7_CIReadback_FullFix_ImportPath

Status:
FULLFIX_APPLIED_PENDING_CI_RERUN_READBACK

Blocked Parent Task:
E4S-CI0-M7_PilotCIRunReadbackQA
```

## 2. Failure Evidence

Operator-provided CI log evidence:

```text
failed_step:
Run CI-safe pytest targets when present

failed_command:
pytest -q tests/test_raz_reversed_anomaly.py

error_type:
ModuleNotFoundError

error_excerpt:
from tools.raz.build_raz_a_reference_sentences import (...)
ModuleNotFoundError: No module named 'tools.raz'

exit_code:
2
```

## 3. Root Cause

The CI-safe smoke test imports a repository-local module:

```python
from tools.raz.build_raz_a_reference_sentences import (...)
```

The repository had `tools/raz/build_raz_a_reference_sentences.py`, but did not have:

```text
tools/__init__.py
tools/raz/__init__.py
```

This made the import boundary fragile in GitHub Actions. The workflow also did not explicitly set `PYTHONPATH` to the repository workspace before running pytest.

## 4. Scope Classification

```text
classification:
CURRENT_TASK_BLOCKER

why:
M7 cannot close because the CI-safe smoke test cannot import its target module.

fix type:
Scoped package/import-path FullFix
```

## 5. Files Changed

```text
tools/__init__.py
tools/raz/__init__.py
.github/workflows/english-db-ci-readback.yml
```

## 6. Fix Applied

Created package markers:

```text
tools/__init__.py
tools/raz/__init__.py
```

Updated workflow job environment:

```yaml
env:
  PYTHONPATH: ${{ github.workspace }}
```

Updated pytest invocation to use:

```text
python -m pytest
```

instead of bare `pytest`.

## 7. Files Not Changed

```text
No RAZ builder logic changed.
No tests changed.
No generated artifacts committed.
No validators changed.
No ReadingV1 feature work added.
No learner-facing output added.
No public deployment added.
No promotion performed.
```

## 8. Required Re-run

The GitHub Actions workflow must be re-run on the new commit.

Required PASS evidence:

```text
workflow_name = English DB CI Readback
workflow_status = completed
workflow_conclusion = success
run_url = recorded
CI_PYTEST_STATUS = PASS
CI_EXIT_CODE = 0
```

## 9. Gate Result

```text
PASS: import path defect was identified.
PASS: tools and tools/raz are now explicit Python packages.
PASS: CI workflow now exposes repository root through PYTHONPATH.
PASS: pytest is invoked via python -m pytest for interpreter consistency.
PASS: no generated artifacts or unrelated features were added.
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
E4S-CI0-M7_CIReadback_FullFix_ImportPath -> APPLIED_PENDING_CI_RERUN

Remaining Middle Tasks:
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 2
```

## 11. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M7_CIReadback_RerunAfterImportPathFullFix

Unique execution action:
Read the GitHub Actions run for the commit that patched package/import path handling and confirm whether English DB CI Readback passes.
```
