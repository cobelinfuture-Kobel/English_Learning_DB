# E4S-CI0-M4 CI Readback Response Contract

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M4_CIReadbackResponseContract

Status:
M4_CONTRACT_PATCHED_FOR_CI_SAFE_PYTEST_SCOPE

Previous Gates:
E4S-CI0-M0 -> COMPLETED
E4S-CI0-M1 -> COMPLETED_WITH_WARNING
E4S-CI0-M2 -> COMPLETED
E4S-CI0-M3 -> WORKFLOW_FILE_CREATED
```

## 2. Purpose

This contract defines the required readback format for GitHub Actions CI validation in `English_Learning_DB`.

It prevents ambiguous task closeout and prevents copying status labels from other projects or previous tasks.

## 3. Required CI Readback Fields

Every CI readback must include:

```text
CI_READBACK_STATUS
workflow_name
workflow_status
workflow_conclusion
run_url
trigger
target_branch
commit_sha
test_or_validator_summary
fail_count
exit_code
task_status_label
distance_vector_update
NEXT_SHORT_STEP
```

If a field is unavailable, the readback must state:

```text
UNAVAILABLE: <reason>
```

Do not silently omit fields.

## 4. PASS Readback Template

```text
CI Readback — PASS

workflow_name = English DB CI Readback
workflow_status = completed
workflow_conclusion = success
trigger = push / pull_request / workflow_dispatch
target_branch = main
commit_sha = <sha>
run_url = <GitHub Actions run URL>

Validation Summary:
CI_GOVERNANCE_FILES_STATUS = PASS
CI_MARKDOWN_UTF8_STATUS = PASS
CI_JSON_STATUS = PASS
CI_JSON_CHECKED = <integer>
CI_JSON_FAILED = 0
CI_PYTEST_STATUS = PASS / SKIPPED_NO_TESTS_DIR / SKIPPED_NO_CI_SAFE_TEST_TARGETS
CI_VALIDATOR_DISCOVERY_STATUS = PASS / SKIPPED_NO_VALIDATOR_DIR
CI_BUILDER_DISCOVERY_STATUS = PASS / SKIPPED_NO_BUILDER_DIR
CI_EXIT_CODE = 0

fail_count = 0
exit_code = 0

task_status_label = <current task-specific PASS label>

Distance Vector:
<updated distance vector>

NEXT_SHORT_STEP:
<one next task only>
```

## 5. FAIL Readback Template

```text
CI Readback — FAIL

workflow_name = English DB CI Readback
workflow_status = completed / in_progress / queued / failed_to_fetch
workflow_conclusion = failure / cancelled / timed_out / action_required / unavailable
trigger = push / pull_request / workflow_dispatch / unavailable
target_branch = <branch>
commit_sha = <sha>
run_url = <GitHub Actions run URL or UNAVAILABLE: reason>

Failure Summary:
failed_step = <step name>
failed_command = <command or UNAVAILABLE>
exit_code = <integer or UNAVAILABLE>
error_excerpt = <short excerpt>

fail_count = <integer or UNAVAILABLE>

task_status_label = FAILED_CI_ACTIONS or <current task-specific CI fail label>

Required Next Task:
<CurrentTaskID>_CIReadback_FullFix

NEXT_SHORT_STEP:
Open FullFix task. Do not proceed to the next feature or milestone.
```

## 6. Documentation-only Readback Template

Use this only when a task changes documentation and no CI run is applicable or available.

```text
CI Readback — DOCS_ONLY_CI_NOT_VERIFIED

reason = <why no CI run was used>
changed_files = <files>
commit_sha = <sha>

task_status_label = DOCS_ONLY_CI_NOT_VERIFIED

Distance Vector:
<updated distance vector>

NEXT_SHORT_STEP:
<one next task only>
```

A documentation-only readback must not be reported as `PASS_CI_SYNCED_AND_CLEAN`.

## 7. Hardcoded Status Ban

Do not copy status labels from other projects or previous task lines.

Forbidden examples:

```text
S24B_STATUS = PASS_CI_SYNCED_AND_CLEAN
PASS_LOCAL_SYNCED_AND_CLEAN
```

Allowed pattern:

```text
<CurrentTrackOrTaskStatus> = <status supported by current governance>
```

For CI0, use:

```text
E4S_CI0_STATUS = PASS_CI_SYNCED_AND_CLEAN
E4S_CI0_STATUS = DOCS_ONLY_CI_NOT_VERIFIED
E4S_CI0_STATUS = FAILED_CI_ACTIONS
E4S_CI0_STATUS = PASS_WITH_WARNINGS_CI_NOT_FULLY_ENUMERATED
```

## 8. Distance Vector Requirements

Every readback must update:

```text
Epic ID
current middle task
current small task, if applicable
completed middle tasks
remaining middle tasks
D_middle_remaining
current task status
NEXT_SHORT_STEP
```

## 9. Reading / Grammar Progress Compatibility

If the active task belongs to a Reading or Grammar track, readback must include the applicable progress block.

For CI0 governance tasks, use:

```text
Reading System Progress = NOT_APPLICABLE_TO_CI0_GOVERNANCE
English Grammar System Progress = CI / Readback Sync updated when task affects grammar governance
```

## 10. M4 Gate Check

```text
PASS: required readback fields are defined.
PASS: PASS template is defined.
PASS: FAIL template is defined.
PASS: documentation-only template is defined.
PASS: hardcoded cross-project status labels are forbidden.
PASS: E4S_CI0-specific status labels are defined.
PASS: CI-safe pytest skip status is supported.
PASS: Distance Vector requirements are explicit.
PASS: NEXT_SHORT_STEP must remain unique.
```

## 11. Distance Vector

```text
Epic:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Completed Middle Tasks:
E4S-CI0-M0
E4S-CI0-M1
E4S-CI0-M2
E4S-CI0-M3
E4S-CI0-M4

Remaining Middle Tasks:
E4S-CI0-M5
E4S-CI0-M6
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 4
```

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M5_LongTaskCloseoutIntegration

Unique execution action:
Patch repository governance files so long-task closeout explicitly references the CI readback gate.
```
