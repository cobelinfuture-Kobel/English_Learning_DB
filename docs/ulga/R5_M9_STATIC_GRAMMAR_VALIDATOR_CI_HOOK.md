# R5-M9 Static Grammar Validator CI Hook

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M9 wire validator into CI-safe discovery or test target

Branch:
codex/r5-m9-validator-ci-hook

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/validators/validate_static_grammar_artifacts.py
- ulga/reports/grammar_artifact_validation_report.json

Deliverable:
- tests/ulga/test_static_grammar_artifacts.py
- docs/ulga/R5_M9_STATIC_GRAMMAR_VALIDATOR_CI_HOOK.md
```

## 2. Core Execution

### Files created

```text
tests/ulga/test_static_grammar_artifacts.py
docs/ulga/R5_M9_STATIC_GRAMMAR_VALIDATOR_CI_HOOK.md
```

### Test behavior

The CI-safe pytest hook imports:

```text
ulga.validators.validate_static_grammar_artifacts.validate
```

and asserts:

```text
report.status = PASS
report.summary.fail_count = 0
report.summary.node_count = 6
report.summary.edge_count = 5
report.scope.learner_facing_practice = false
report.scope.learner_state_write = false
```

It also confirms the validator exposes the expected check surfaces:

```text
EDGE_REFS_RESOLVE
ORDERING_CONSTRAINTS_SATISFIED
COVERAGE_COVERS_NODES
COVERAGE_STAGE_KEYS_COMPLETE
COVERAGE_STAGE_ROLE_COUNTS
QUERY_COVERS_NODES
QUERY_STAGE_ROLE_SURFACE_COMPLETE
LEARNER_STATE_WRITE_FALSE
```

### Scope control

```text
R5-M9 only wires the R5-M8 validator into a CI-safe pytest target.
R5-M9 does not generate learner-facing practice.
R5-M9 does not write learner state.
R5-M9 does not modify grammar_nodes.json, grammar_edges.json, grammar_order_table.json, grammar_coverage_matrix.json, grammar_query_index.json, or grammar_artifact_validation_report.json.
R5-M9 does not start R5-M10.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] CI-safe pytest hook created.
[PASS] Hook imports R5-M8 validator directly.
[PASS] Hook asserts validation report status = PASS.
[PASS] Hook asserts fail_count = 0.
[PASS] Hook asserts learner-facing practice remains false.
[PASS] Hook asserts learner_state_write remains false.
[PASS] Hook checks required validation surfaces.
[PASS] No learner-facing practice artifact created.
[PASS] No learner state write path added.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

### Local validation evidence

```text
pytest target added: tests/ulga/test_static_grammar_artifacts.py
validator import path = ulga.validators.validate_static_grammar_artifacts.validate
expected test count = 2
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M10 = 1 task left

Current sub-task status:
R5-M9 -> COMPLETED
```

### English Grammar System Progress

```text
Grammar Authority ............ IN_PROGRESS
Pattern Authority ............ PARTIAL
Question / Practice Contract . NOT_STARTED
Validation Layer ............. IN_PROGRESS
Practice Generation .......... NOT_STARTED
Practice Export .............. NOT_STARTED
CI / Readback Sync ........... NOT_STARTED
Production Readiness ......... NOT_STARTED
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

Reason: this task created a CI-safe pytest hook and local structural checks passed, but GitHub Actions CI readback was not confirmed at file creation time.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M10 close R5 pilot implementation readiness readback

唯一執行動作:
Produce the R5 pilot implementation readiness readback, confirming R5-M1 through R5-M9 artifacts, CI status, remaining risks, and handoff boundary before R6 expansion.
```
