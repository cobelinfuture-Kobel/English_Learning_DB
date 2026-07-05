# English Grammar Project Governance

## 1. Primary Goal

The current primary objective of the English Grammar track is to build the English Grammar A1 / A1+ learning system.

All design decisions, data modeling, validators, generated artifacts, and implementation tasks must be evaluated against this objective.

A task should only be accepted if it contributes directly or indirectly to the English Grammar learning system.

## 2. Core Scope

This track focuses on:

- A1 / A1+ grammar authority
- Cambridge / CEFR-aligned grammar progression
- sentence pattern mapping
- grammar-tagged practice items
- validator-driven grammar checks
- source-grounded and traceable learning materials
- local/private practice output when applicable

This track must not expand into unrelated systems unless explicitly approved.

Deferred systems include:

- full ReadingV1 system
- full Writing system
- full Listening system
- full Speaking system
- adaptive learner engine
- commercial worksheet export
- public GitHub Pages learning site

## 3. Progress Tracking Policy

Every completed task must explicitly report its contribution to the English Grammar system.

Progress must be measured by system readiness, not by the number of completed tasks.

Each task must update this progress block:

```text
English Grammar System Progress

Grammar Authority ............ NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Pattern Authority ............ NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Question / Practice Contract . NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Validation Layer ............. NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Practice Generation .......... NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Practice Export .............. NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
CI / Readback Sync ........... NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
Production Readiness ......... NOT_STARTED / IN_PROGRESS / PARTIAL / COMPLETE
```

Each completed task must also report:

- what changed
- why it matters for the English Grammar system
- which files were modified or created
- which tests or validators passed
- remaining blockers
- next shortest task

## 4. CI / GitHub Actions Readback Policy

GitHub Actions CI is the primary remote validation evidence for this track.

A task is not considered fully synced unless the GitHub Actions workflow has completed successfully.

When CI evidence is available, the final readback must include:

```text
CI Readback

workflow status = completed
workflow conclusion = success
test command = PASS
test exit code = 0
working tree = clean, if confirmed
```

If CI passes, use:

```text
ENGLISH_GRAMMAR_STATUS = PASS_CI_SYNCED_AND_CLEAN
```

Do not use:

```text
PASS_LOCAL_SYNCED_AND_CLEAN
```

unless the evidence comes only from local execution and GitHub Actions was not used.

If local tests pass but GitHub Actions has not been checked, use:

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

If GitHub Actions fails, use:

```text
ENGLISH_GRAMMAR_STATUS = FAILED_CI_ACTIONS
```

If no test command is applicable because the task is documentation-only, use:

```text
ENGLISH_GRAMMAR_STATUS = DOCS_ONLY_CI_NOT_VERIFIED
```

and record the reason no test command was run.

## 5. Required Task Response Format

Every implementation, design scan, QA, fullfix, or closeout task in this track must use this structure.

### 5.1 Current State

```text
Epic ID:
[English Grammar epic ID]

Sub-task ID:
[Current sub-task only]

Data Sources:
[List exact files, specs, prompts, or authority sources used]

Deliverable:
[Exact artifact or code change expected from this task]
```

### 5.2 Core Execution

```text
Only execute the current sub-task.

Do not implement future tasks.
Do not expand scope.
Do not introduce unrelated UI, reading, writing, listening, speaking, or adaptive features unless explicitly approved.
```

### 5.3 Gate & Distance Update

```text
Gate Metrics:
[PASS / FAIL] GitHub write or artifact update completed
[PASS / FAIL] Validator or test passed, if applicable
[PASS / FAIL] GitHub Actions CI completed successfully, if available
[PASS / FAIL] No out-of-scope expansion

Distance Vector:
Total remaining tasks:
Current sub-task status:
English Grammar System Progress:
```

### 5.4 Next Shortest Step

```text
NEXT_SHORT_STEP:
[One and only one next task]

唯一執行動作:
[The exact next command, prompt, or file to create]
```

## 6. Anti-Scope-Creep Rule

Each conversation must complete one clearly defined milestone.

The project must not expand from English Grammar A1 / A1+ into a full four-skill learning platform unless the operator explicitly changes the epic.

Future systems may be documented as deferred, but they must not block the current English Grammar milestone.

This policy inherits the project-wide task expansion control policy in `docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md`.

## 7. Development Principle

When multiple implementation choices exist, choose the option that improves:

- grammar correctness
- CEFR / Cambridge alignment
- traceability
- validator coverage
- queryability
- CI-verifiable output
- long-task continuity

## 8. Default Closeout Template

Use this closeout template when finishing a task:

```text
1. Current State
Epic ID:
Sub-task ID:
Data Sources:
Deliverable:

2. Core Execution
Files inspected:
Files changed:
Scope control:

3. Gate & Distance Update
GitHub write/artifact update:
Validator/test result:
GitHub Actions CI:
No out-of-scope expansion:
ENGLISH_GRAMMAR_STATUS:
English Grammar System Progress:

4. Next Shortest Step
NEXT_SHORT_STEP:
唯一執行動作:
```
