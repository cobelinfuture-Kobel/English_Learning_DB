# Project Task Expansion Control Policy

## 1. Purpose

This policy prevents task expansion across the English Learning DB project.

It applies to all tracks, including Reading Authority, RAZ, ULGA, Grammar Authority, Vocabulary Authority, source adapters, validators, generated artifacts, query layers, Learning Opportunity Binding, documentation, and QA/readback tasks.

The default rule is:

```text
A task may only close the approved current-stage scope.
New findings must be classified before action.
Only current-task blockers may be fixed inside the current task.
```

## 2. Problem This Policy Prevents

The project must avoid this pattern:

```text
do A -> discover B -> implement B -> discover C -> open C -> patch D -> expand into E
```

The correct pattern is:

```text
do A -> validate A -> classify B/C/D -> fix only A blockers -> defer everything else
```

## 3. Finding Classification

Every finding discovered during a task must be classified before implementation.

| Class | Meaning | May fix in current task? |
|---|---|---|
| `CURRENT_TASK_BLOCKER` | Current task cannot be accepted unless fixed | Yes |
| `CURRENT_TASK_WARNING` | Current task can pass with documented warning | No, unless explicitly approved |
| `FUTURE_WORK` | Valid issue outside current scope | No |
| `IGNORE_OR_NON_ISSUE` | Not actionable or not relevant | No |

Only `CURRENT_TASK_BLOCKER` may be implemented inside the current task.

## 4. Expansion Ban

The following expansions are forbidden unless explicitly approved as a new task:

- builder task expands into promotion task
- readback QA expands into source adapter implementation
- validator task expands into schema redesign
- generated artifact task expands into storage architecture
- warning analysis expands into full historical cleanup
- source discovery issue expands into broad corpus migration
- local QA expands into runtime integration
- candidate layer expands into final authority promotion
- documentation task expands into code changes
- patch task expands into unrelated refactor

## 5. Required Task Header

Every future implementation, fix, QA, readback, design scan, or closeout task must begin with this header:

```text
Task:
Scope:
Allowed files:
Forbidden files:
Current-task blockers:
Warning policy:
Generated artifact policy:
Runtime impact:
Promotion impact:
Stop condition:
Deferred issues register:
```

If the header is missing, the task is not ready to start.

## 6. Stop Condition Requirement

Each task must define a stop condition before work starts.

A valid stop condition must state:

1. which files may be changed
2. which files must not be changed
3. which commands must pass
4. which warnings are acceptable
5. which warnings block the current task
6. whether generated artifacts may be committed
7. whether promotion is allowed
8. which issues must be deferred

If the task has no stop condition, do not implement it.

## 7. PASS_WITH_WARNINGS Policy

`PASS_WITH_WARNINGS` is not automatically acceptable.

Warnings must be classified as one of:

- harmless warning
- current-task blocker
- source adapter defect
- traceability defect
- promotion blocker
- artifact management issue
- future cleanup item

A warning may block only the stage it actually affects.

Example:

```text
A promotion blocker does not automatically block an intake/query-only stage.
A source adapter cleanup issue does not automatically expand a builder task.
```

## 8. Generated Artifact Policy

Large generated artifacts must not be committed by default.

Default behavior:

```text
commit code / validators / tests / docs
keep large generated JSON as local evidence
use Google Drive only if persistence is required
do not git add .
do not merge generated artifacts unless explicitly approved
```

A task must explicitly say whether generated artifacts are allowed in GitHub.

If not stated, generated artifacts are not allowed in the commit.

## 9. Candidate / Authority / Promotion Control

Query-ready does not mean authority-ready.

Candidate-only means:

- searchable
- auditable
- usable for downstream inspection
- not final authority
- not promoted
- not learner-facing unless later approved

No candidate artifact may become final authority unless a promotion-readiness task explicitly approves it.

## 10. FullFix Boundary

`FullFix` means full fix inside the approved task boundary.

`FullFix` does not mean:

- fix every adjacent issue
- redesign downstream architecture
- expand into the next stage
- clean all historical artifacts
- promote candidate data
- refactor unrelated modules

If an issue is real but outside scope, record it as `FUTURE_WORK`.

## 11. Deferred Issues Register

Every out-of-scope finding must be recorded instead of implemented.

Use this format:

```text
issue_id:
severity:
affected_file_or_artifact:
classification:
why_deferred:
recommended_future_task:
blocks_current_task: yes/no
```

Do not implement deferred issues inside the current task.

## 12. Project-Wide Default

For all future tasks:

```text
Do not expand the task.
Do not commit large generated artifacts by default.
Do not promote candidate artifacts by implication.
Do not convert warnings into new implementation work unless they block the approved current task.
Do not mix unrelated local changes into the current PR.
```

## 13. Operational Checklist

Before starting a task, verify:

```text
[ ] Task header exists
[ ] Allowed files are listed
[ ] Forbidden files are listed
[ ] Generated artifact policy is stated
[ ] Runtime impact is stated
[ ] Promotion impact is stated
[ ] Stop condition is stated
[ ] Deferred issues register exists
```

Before closing a task, verify:

```text
[ ] Only allowed files changed
[ ] Required commands passed
[ ] Warnings classified
[ ] Generated artifacts handled according to policy
[ ] No unrelated findings were implemented
[ ] Deferred issues were recorded but not expanded
```
