# E4S-CI0-M6 FullFix Routing Policy

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M6_FullFixRoutingPolicy

Status:
M6_POLICY_CREATED

Previous Gates:
E4S-CI0-M0 -> COMPLETED
E4S-CI0-M1 -> COMPLETED_WITH_WARNING
E4S-CI0-M2 -> COMPLETED
E4S-CI0-M3 -> WORKFLOW_FILE_CREATED
E4S-CI0-M4 -> COMPLETED
E4S-CI0-M5 -> COMPLETED
```

## 2. Purpose

This policy defines how `English_Learning_DB` must respond when GitHub Actions CI readback fails or cannot provide required evidence.

The goal is to prevent unstable long-task progression.

## 3. Failure Classes

### 3.1 CI_ACTIONS_FAILURE

Use when GitHub Actions completed but concluded failure.

Examples:

```text
invalid JSON
missing required governance file
pytest failure
markdown UTF-8 failure
script exception
```

Required next task:

```text
<CurrentTaskID>_CIReadback_FullFix
```

### 3.2 CI_ACTIONS_CANCELLED_OR_TIMED_OUT

Use when the workflow was cancelled, timed out, or did not complete.

Required next task:

```text
<CurrentTaskID>_CIReadback_RerunOrInfraCheck
```

If rerun produces a deterministic failure, route to FullFix.

### 3.3 CI_READBACK_UNAVAILABLE

Use when the workflow result cannot be read through available tools.

This is not a PASS.

Allowed temporary status:

```text
CI_READBACK_UNAVAILABLE_PENDING_MANUAL_EVIDENCE
```

Required evidence if operator supplies manual evidence:

```text
run URL
workflow status
workflow conclusion
failed/passed step summary
visible timestamp or commit SHA
```

### 3.4 DOCS_ONLY_CI_NOT_VERIFIED

Use only when:

```text
task is documentation-only
no test command is applicable
CI is not available or not required by current gate
reason is explicitly recorded
```

This status must not be used for code, workflow, validator, builder, schema, generated artifact, or test changes.

## 4. FullFix Naming Rule

```text
<CurrentTaskID>_CIReadback_FullFix
```

Examples:

```text
E4S-CI0-M3_CIReadback_FullFix
R4-M8_CIReadback_FullFix
P1-M4_CIReadback_FullFix
```

## 5. Required FullFix Header

Every CI FullFix task must begin with:

```text
Task:
<CurrentTaskID>_CIReadback_FullFix

Scope:
Fix only the CI-blocking failure from the latest failed run.

Allowed files:
<files implicated by failure evidence>

Forbidden files:
Unrelated feature files, generated artifacts, promotion outputs, learner-facing content, public deployment files unless directly implicated.

Current-task blockers:
<failed CI checks>

Warning policy:
Non-blocking warnings may be documented but not fixed unless they block CI.

Generated artifact policy:
Do not commit generated artifacts unless explicitly approved.

Runtime impact:
No runtime or deployment change unless directly required by the failed CI gate.

Promotion impact:
No candidate promotion.

Stop condition:
CI passes or failure is reclassified with evidence.

Deferred issues register:
<out-of-scope findings>
```

## 6. Required Failure Evidence

A CI FullFix may not start without:

```text
workflow_name
workflow_status
workflow_conclusion
run_url
commit_sha
failed_step
failed_command
exit_code
error_excerpt
suspected_files
why_this_blocks_current_task
```

If any field is unavailable, write:

```text
UNAVAILABLE: <reason>
```

## 7. FullFix Scope Rule

FullFix means:

```text
full repair of the current CI-blocking issue inside the approved task boundary
```

FullFix does not mean:

```text
fix adjacent warnings
redesign downstream architecture
run broad cleanup
promote candidate artifacts
rewrite unrelated validators
expand into next feature
```

## 8. Re-run Requirement

After a FullFix, the same or stricter CI gate must be re-run.

A FullFix may close only when:

```text
workflow status = completed
workflow conclusion = success
fail_count = 0
run URL is recorded
```

If readback remains unavailable, closeout must say:

```text
CI_READBACK_UNAVAILABLE_PENDING_MANUAL_EVIDENCE
```

and must not claim `PASS_CI_SYNCED_AND_CLEAN`.

## 9. Progression Ban

While required CI is failing:

```text
Do not proceed to the next feature task.
Do not proceed to the next authority build.
Do not proceed to ReadingV1 generation.
Do not proceed to GrammarSkillTree expansion.
Do not promote candidate artifacts.
Do not close the task as synced.
```

## 10. M6 Gate Check

```text
PASS: CI failure classes are defined.
PASS: FullFix naming rule is defined.
PASS: required FullFix header is defined.
PASS: required failure evidence is defined.
PASS: FullFix scope boundary is defined.
PASS: re-run requirement is defined.
PASS: progression ban is explicit.
PASS: no unrelated feature work was added.
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
E4S-CI0-M5
E4S-CI0-M6

Remaining Middle Tasks:
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 2
```

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M7_PilotCIRunReadbackQA

Unique execution action:
Read or trigger the English DB CI Readback workflow, capture result evidence, and write docs/ulga/E4S_CI_READBACK_PILOT_QA.md.
```
