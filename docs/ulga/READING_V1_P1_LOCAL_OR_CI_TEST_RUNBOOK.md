# ReadingV1 P1 Local or CI Test Runbook

Task:
ReadingV1_P1_LocalOrCI_Test_Runbook

Scope:
Define exact verification commands for ReadingV1 P1 after `CI_EVIDENCE_UNAVAILABLE`.

Allowed files:
- docs/ulga/READING_V1_P1_LOCAL_OR_CI_TEST_RUNBOOK.md

Forbidden files:
- code changes
- test changes
- generated outputs
- promotion artifacts

Runtime impact:
- None.

Promotion impact:
- None.

---

## 1. Current State

Prior status:

```text
ReadingV1_P1_CI_STATUS = CI_EVIDENCE_UNAVAILABLE
```

Preserved P1 status:

```text
ReadingV1_P1_STATUS = PASS_WITH_WARNINGS_FOUNDATION_READY
```

Observed repository precheck:

```text
.github/workflows/tests.yml: not found
.github/workflows/ci.yml: not found
pyproject.toml: not found
requirements.txt: not found
```

Therefore the first verification path is standard-library unittest.

---

## 2. Local Test Commands

Run from repository root:

```powershell
python -m unittest tests.ulga.test_reading_v1_practice_bank
python -m unittest tests.ulga.test_reading_v1_private_homework_overlay
python -m unittest tests.ulga.test_reading_v1_private_homework_output_gate
python -m unittest tests.ulga.test_reading_v1_private_page_export
```

Single-command form:

```powershell
python -m unittest tests.ulga.test_reading_v1_practice_bank tests.ulga.test_reading_v1_private_homework_overlay tests.ulga.test_reading_v1_private_homework_output_gate tests.ulga.test_reading_v1_private_page_export
```

Expected total:

```text
PracticeBank: 5 tests
Overlay: 5 tests
OutputGate: 5 tests
Private page export: 2 tests
Total: 17 tests
```

---

## 3. Status Rules

If all local tests pass with exit code 0:

```text
ReadingV1_P1_LOCAL_STATUS = PASS_LOCAL_SYNCED
```

If any local test fails:

```text
ReadingV1_P1_LOCAL_STATUS = FAIL_REQUIRES_FIX
```

If a GitHub Actions run later exists and passes:

```text
ReadingV1_P1_CI_STATUS = PASS_CI_SYNCED
```

If a GitHub Actions run later exists and fails:

```text
ReadingV1_P1_CI_STATUS = FAIL_CI_REQUIRES_FIX
```

If no CI run exists:

```text
ReadingV1_P1_CI_STATUS = CI_EVIDENCE_UNAVAILABLE
```

---

## 4. Evidence Required

Local evidence:

```text
command used
terminal output
exit code
current commit SHA
```

CI evidence:

```text
workflow name
run URL
run conclusion
commit SHA
job name
unittest command output
```

---

## 5. Stop Rules

Do not move to P2 if:

```text
any P1 test fails
imports fail
CI is missing and no local evidence is supplied
CI fails
promotion status changes unexpectedly
```

---

## 6. Next Safe Task

If local tests pass but CI remains unavailable:

```text
ReadingV1_P1_Local_Test_Readback
```

If a CI workflow should be added:

```text
ReadingV1_P1_CI_Workflow_Implementation
```

If CI passes later:

```text
ReadingV1_P1_CI_Pass_Readback
```

Task status:

```text
ReadingV1_P1_LocalOrCI_Test_Runbook -> COMPLETED_BY_DESIGN
```
