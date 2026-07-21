# Agent Operating Rules

This repository is the private authority database for English learning materials, ULGA graph, RAZ corpus processing, tag registry, validators, and content authority reports.

All agents must follow the project-wide task expansion control policy:

- `docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md`

For English Grammar A1 / A1+ work, agents must also follow:

- `docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md`

For project-wide CI readback and long-task remote verification, agents must also follow:

- `docs/ulga/E4S_CI_READBACK_GATE_POLICY.md`
- `docs/ulga/E4S_CI_READBACK_RESPONSE_CONTRACT.md`

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

## E4S CI Readback Gate

For repository-changing long tasks, agents must use the E4S CI readback gate as the default remote verification policy.

A task may proceed to the next long-task stage only when the required CI evidence is available and passes, or when the task explicitly qualifies for a documented docs-only / CI-not-applicable status.

Required CI readback fields are defined in:

```text
docs/ulga/E4S_CI_READBACK_RESPONSE_CONTRACT.md
```

If GitHub Actions fails, the next task must be a scoped FullFix task using this naming rule:

```text
<CurrentTaskID>_CIReadback_FullFix
```

Do not continue to the next feature, authority build, generated artifact, ReadingV1 milestone, GrammarSkillTree milestone, or promotion task while the required CI gate is failing.

## Long-task Auto-progression Rule

When the operator approves automatic progression for a task line, agents may continue through the approved middle-task order without asking for confirmation at every middle task.

Auto-progression must stop when any of the following occurs:

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

When auto-progression stops, the agent must report:

```text
where it stopped
which gate failed
what evidence supports the stop
recommended next shortest FullFix or clarification task
```

## A1FS-V1 Canonical Content Production Rule

All A1 / A1+ sentence, passage, dialogue, question, media, and four-skill content work must follow:

- `docs/governance/A1FS_V1_CANONICAL_CONTENT_PRODUCTION_GOVERNANCE.md`
- `ulga/contracts/a1fs_v1_canonical_content_production_policy.json`

The non-negotiable source-of-truth rules are:

```text
CANONICAL_SOURCE = APPROVED_CANONICAL_JSON
FOUR_SKILL_SOURCE = VALIDATED_APPROVED_JSON
EXCEL_ROLE = DERIVED_REFERENCE_ONLY
EXCEL_EXPORT_DIRECTION = JSON_TO_EXCEL_ONLY
EXCEL_TO_CANONICAL_WRITEBACK = FORBIDDEN
POLICY_BOUND_ARTIFACT_REQUIRED = TRUE
```

Builders or generators produce candidate JSON. Validators independently check candidates and may not generate replacement candidate content. Only an explicit admission gate may produce approved canonical JSON.

Listening, Speaking, Reading, and Writing builders must consume validated approved JSON. Excel and CSV files are downstream reference exports only and may not write back into canonical content.

All newly created or modified protected A1FS-V1 / E4S-A1V1 / A1-A1+ builders must declare `A1FS_CONTENT_POLICY_MODE`. Content-producing builders must use:

```text
ulga/builders/build_a1fs_v1_policy_bound_content_artifact.py
```

Every resulting candidate, approved canonical, projection, media, or Excel reference manifest must pass:

```text
ulga/validators/validate_a1fs_v1_policy_bound_content_artifact.py
```

Before closing any affected task, run:

```text
python ulga/validators/validate_a1fs_v1_canonical_content_production_policy.py
python -m pytest -q tests/ulga/test_a1fs_v1_canonical_content_production_policy.py
python -m pytest -q tests/ulga/test_a1fs_v1_policy_bound_content_artifact.py
```

The required GitHub Actions status is produced by:

```text
.github/workflows/a1fs-v1-canonical-content-governance.yml
```
