# Agent Operating Rules

This repository is the private authority database for English learning materials, ULGA graph, RAZ corpus processing, tag registry, validators, and content authority reports.

All agents must follow the project-wide task expansion control policy:

- `docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md`

For English Grammar A1 / A1+ work, agents must also follow:

- `docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md`

## Default Task Rule

Each task must close one approved milestone only.

Do not expand a Grammar task into Reading, Writing, Listening, Speaking, adaptive learning, public site work, or commercial worksheet export unless the operator explicitly changes the epic.

## English Grammar Task Closeout

Every English Grammar task must end with:

```text
1. Current State
2. Core Execution
3. Gate & Distance Update
4. Next Shortest Step
```

The closeout must include:

```text
ENGLISH_GRAMMAR_STATUS = [status]
English Grammar System Progress = [progress block]
NEXT_SHORT_STEP = [one next task only]
```

## CI Evidence Rule

GitHub Actions CI is the primary remote validation evidence when available.

Use `PASS_CI_SYNCED_AND_CLEAN` only when GitHub Actions evidence confirms success.

Use `PASS_LOCAL_ONLY_CI_NOT_VERIFIED` when only local tests passed.

Use `DOCS_ONLY_CI_NOT_VERIFIED` when the task is documentation-only and no test command is applicable.
