# E4S-CI0 GitHub Actions CI Readback Gate Policy

## 1. Current State

```text
Epic ID:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Chinese Name:
English_Learning_DB GitHub Actions CI Readback 長任務驗收系統

Current Middle Task:
E4S-CI0-M0_ScopeGovernanceLock

Current Small Task Range:
E4S-CI0-M0-S1_to_S5

Status:
M0_POLICY_CREATED
```

## 2. Purpose

This policy establishes GitHub Actions CI readback as the authoritative verification gate for long-task closeout in `English_Learning_DB`.

The project must not rely on manually pasted local terminal results as the final task verification source unless explicitly approved for an emergency or connector outage.

The intended long-task flow is:

```text
complete scoped task
-> commit / push
-> GitHub Actions CI runs
-> ChatGPT / Codex reads CI result
-> PASS allows closeout and next task
-> FAIL blocks progression and routes to FullFix
```

## 3. Scope Lock

This CI0 line is a project governance and verification line.

It is allowed to define:

```text
CI readback gate policy
CI workflow contract
CI workflow implementation plan
CI readback response format
long-task closeout integration
FullFix routing policy
pilot CI readback QA
handoff rules for later ReadingV1 / ULGA / GrammarSkillTree tasks
```

It is not allowed to implement unrelated product features.

## 4. Non-goals

The CI0 line must not expand into:

```text
ReadingV1 PracticeBank implementation
Reading HTML renderer
student-facing app
public GitHub Pages deployment
GPT Action API server
adaptive learner state
wrong-answer notebook
listening / speaking / writing feature work
Cambridge formal exam full mapping
RAZ full text database promotion
large content generation
```

Any request to add these items must be split into a separate approved task line.

## 5. Authoritative Verification Source

For normal long-task closeout, the authoritative verification source is:

```text
GitHub Actions workflow result
```

Local tests may be used during development, but local test output alone does not authorize progression to the next milestone.

A task may close only when its required verification source is stated explicitly.

## 6. CI Readback Gate Conditions

A task may proceed to the next long-task stage only when all required CI gate conditions are true:

```text
workflow status = completed
workflow conclusion = success
required tests / validators = PASS
fail count = 0
summary is readable
run URL is recorded
current task status label is accurate and not hardcoded from another project
distance vector is updated
NEXT_SHORT_STEP is unique
```

If any required condition is false, the task must not proceed to the next feature or milestone.

## 7. Failure Routing

When CI fails, the next task must be a FullFix task unless the failure is explicitly proven to be external infrastructure only.

FullFix naming rule:

```text
<CurrentTaskID>_CIReadback_FullFix
```

Required failure evidence:

```text
workflow name
workflow status
workflow conclusion
run URL
failed step name
failed command
exit code
relevant error excerpt
files likely involved
recommended FullFix scope
```

## 8. Long-task Closeout Requirement

Every completed implementation or contract task that changes repository artifacts must include a CI readback section or explicitly state why CI readback is not applicable.

Required closeout fields:

```text
CI_READBACK_STATUS
workflow_name
workflow_status
workflow_conclusion
run_url
test_or_validator_summary
fail_count
task_status
reading_system_progress_update_or_not_applicable
distance_vector_update
NEXT_SHORT_STEP
```

## 9. Anti-Scope-Creep Rule

CI0 tasks must follow the approved middle-task order unless a bug, missing dependency, connector failure, repository conflict, or CI failure blocks progression.

Approved middle-task order:

```text
E4S-CI0-M0  Scope / Governance Lock
E4S-CI0-M1  Current Test Surface Inventory
E4S-CI0-M2  CI Workflow Contract Design
E4S-CI0-M3  CI Workflow Implementation
E4S-CI0-M4  CI Readback Response Contract
E4S-CI0-M5  Long-task Closeout Integration
E4S-CI0-M6  FullFix Routing Policy
E4S-CI0-M7  Pilot CI Run / Readback QA
E4S-CI0-M8  Closeout / Handoff
```

The operator has approved automatic progression in this order unless a bug is encountered.

## 10. M0 Gate Check

```text
PASS: Epic ID and purpose are defined.
PASS: CI0 is scoped as governance / verification, not ReadingV1 feature work.
PASS: non-goals are explicitly listed.
PASS: CI readback is defined as the authoritative verification source for normal closeout.
PASS: failure routes to FullFix instead of next feature work.
PASS: approved middle-task order is recorded.
PASS: NEXT_SHORT_STEP is defined.
```

## 11. Distance Vector

```text
Epic:
E4S-CI0_GitHubActionsCIReadbackGateSystem

Current Middle Task:
E4S-CI0-M0_ScopeGovernanceLock -> COMPLETED_BY_POLICY_FILE

Remaining Middle Tasks:
E4S-CI0-M1
E4S-CI0-M2
E4S-CI0-M3
E4S-CI0-M4
E4S-CI0-M5
E4S-CI0-M6
E4S-CI0-M7
E4S-CI0-M8

D_middle_remaining = 8
```

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-CI0-M1_CurrentTestSurfaceInventory_DesignScan

Unique execution action:
Inspect the repository for currently available tests, validators, builders, JSON artifacts, and CI-eligible verification surfaces, then write docs/ulga/E4S_CI_TEST_SURFACE_INVENTORY.md.
```
