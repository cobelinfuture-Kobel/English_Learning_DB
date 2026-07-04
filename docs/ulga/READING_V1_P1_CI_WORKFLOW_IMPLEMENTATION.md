# ReadingV1 P1 CI Workflow Implementation

Task:
ReadingV1_P1_CI_Workflow_Implementation

Status:
READY_FOR_PUSH_AND_CI_RUN

Files created:

```text
.github/workflows/reading-v1-p1-tests.yml
docs/ulga/READING_V1_P1_CI_WORKFLOW_IMPLEMENTATION.md
```

Workflow purpose:

```text
Run the four ReadingV1 P1 unittest modules in GitHub Actions.
```

Local validation:

```text
python -m unittest tests.ulga.test_reading_v1_practice_bank tests.ulga.test_reading_v1_private_homework_overlay tests.ulga.test_reading_v1_private_homework_output_gate tests.ulga.test_reading_v1_private_page_export
Expected: Ran 17 tests / OK
```

Status after this task:

```text
ReadingV1_P1_LOCAL_STATUS = PASS_LOCAL_SYNCED
ReadingV1_P1_CI_STATUS = CI_WORKFLOW_READY_NOT_YET_CONFIRMED
ReadingV1_P1_STATUS = PASS_WITH_WARNINGS_FOUNDATION_READY
```

Next task after push:

```text
ReadingV1_P1_CI_Run_Readback
```

Stop rule:

```text
Do not proceed to P2 until the GitHub Actions run is completed and read back as PASS_CI_SYNCED.
```
