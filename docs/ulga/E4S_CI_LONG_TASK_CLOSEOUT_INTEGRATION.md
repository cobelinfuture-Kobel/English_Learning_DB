# E4S-CI0-M5 Long-task Closeout Integration

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Middle Task:
E4S-CI0-M5_LongTaskCloseoutIntegration

Status:
M5_INTEGRATION_CREATED

Previous Gates:
E4S-CI0-M0 -> COMPLETED
E4S-CI0-M1 -> COMPLETED_WITH_WARNING
E4S-CI0-M2 -> COMPLETED
E4S-CI0-M3 -> WORKFLOW_FILE_CREATED
E4S-CI0-M4 -> COMPLETED
```

## 2. Purpose

This document records how the CI readback gate is integrated into long-task closeout.

## 3. Files Changed

```text
AGENTS.md
```

The root agent rules now reference:

```text
docs/ulga/E4S_CI_READBACK_GATE_POLICY.md
docs/ulga/E4S_CI_READBACK_RESPONSE_CONTRACT.md
```

## 4. Long-task Closeout Rule

Repository-changing long tasks must end with a CI readback section or an explicit CI-not-applicable status.

Required closeout structure:

```text
1. Current State
2. Core Execution
3. Gate & Distance Update
4. Next Shortest Step
```

Required CI gate fields:

```text
CI_READBACK_STATUS
workflow_name
workflow_status
workflow_conclusion
run_url
commit_sha
test_or_validator_summary
fail_count
exit_code
task_status_label
distance_vector_update
NEXT_SHORT_STEP
```

## 5. Progression Rule

A task may move to the next long-task milestone only when:

```text
CI passes, or
CI is explicitly not applicable and the task is documentation-only, or
operator explicitly approves a temporary CI-not-verified status
```

The default for implementation tasks is:

```text
CI required
```

## 6. Stop Conditions

Auto-progression must stop on:

```text
CI failure
repository write failure
missing required source or artifact
schema or validator failure
permission error
merge or branch conflict
scope ambiguity
operator instruction conflict
```

When stopped, the next task must be a scoped FullFix or clarification task.

## 7. M5 Gate Check

```text
PASS: AGENTS.md references the CI readback gate policy.
PASS: AGENTS.md references the CI readback response contract.
PASS: repository-changing long tasks now require CI readback or explicit non-applicability.
PASS: auto-progression stop conditions are recorded.
PASS: CI failure blocks next feature/milestone progression.
PASS: no business feature, ReadingV1 artifact, generated content, or workflow redesign was added in M5.
```

## 8. Distance Vector

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

Remaining Middle Tasks:
E4S-CI0-M6
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 3
```

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M6_FullFixRoutingPolicy

Unique execution action:
Write docs/ulga/E4S_CI_FULLFIX_ROUTING_POLICY.md defining CI failure routing, required evidence, and re-run conditions.
```
