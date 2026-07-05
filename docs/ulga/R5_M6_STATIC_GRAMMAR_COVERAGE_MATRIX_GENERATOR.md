# R5-M6 Static Grammar Coverage Matrix Generator

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M6 build grammar coverage matrix generator

Branch:
codex/r5-m6-grammar-coverage-matrix

Status:
REPLAYED_ON_LATEST_MAIN_AFTER_CI_FAILURE
```

## 2. Core Execution

### Files created

```text
ulga/builders/build_static_grammar_coverage_matrix.py
ulga/grammar/grammar_coverage_matrix.json
docs/ulga/R5_M6_STATIC_GRAMMAR_COVERAGE_MATRIX_GENERATOR.md
```

### Generator behavior

`build_static_grammar_coverage_matrix.py` reads:

```text
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_order_table.json
```

and writes:

```text
ulga/grammar/grammar_coverage_matrix.json
```

The generator builds:

```text
stage_matrix: stage coverage by focus/recycle/preview/blocked/maintenance/out_of_scope
node_matrix: per grammar node stage-role coverage in static order-table order
summary: node count, stage count, category counts, authority status counts
```

The generator checks:

```text
grammar_nodes.json is a list
order table has rows[]
duplicate grammar_id values
order-table unknown grammar_id references
node IDs missing from order table
unsupported stage roles
```

### Derived coverage matrix artifact

```text
node_count = 6
stage_count = 7
category_counts:
  be_verb = 2
  existential_structure = 1
  modal = 1
  present_continuous = 1
  subject_pronoun = 1
authority_status_counts:
  accepted = 5
  candidate = 1
```

Stage-level role count summary:

```text
A1:      focus=4, recycle=0, preview=0, blocked=2, maintenance=0
A1_PLUS: focus=1, recycle=4, preview=1, blocked=0, maintenance=0
A2:      focus=1, recycle=5, preview=0, blocked=0, maintenance=0
A2_PLUS: focus=0, recycle=2, preview=0, blocked=0, maintenance=4
B1:      focus=0, recycle=1, preview=0, blocked=0, maintenance=5
B1_PLUS: focus=0, recycle=0, preview=0, blocked=0, maintenance=6
B2:      focus=0, recycle=0, preview=0, blocked=0, maintenance=6
```

### CI failure fix note

The first PR #11 run failed in `English DB CI Readback` at pytest while the branch was behind latest `main` by 9 commits. The branch was force-refreshed to the latest `main`, then the R5-M6 files were replayed on top of the updated base.

```text
original issue:
branch behind latest main = 9 commits
failed workflow = English DB CI Readback
failed step = Run pytest when tests directory exists

fix action:
refresh PR branch to latest main
replay R5-M6 generator, artifact, and closeout files
```

### Scope control

```text
R5-M6 only creates the static coverage-matrix generator and first derived coverage matrix.
R5-M6 does not create a validator.
R5-M6 does not generate learner-facing practice.
R5-M6 does not write learner state.
R5-M6 does not modify grammar_nodes.json, grammar_edges.json, or grammar_order_table.json.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] Static grammar coverage-matrix generator created.
[PASS] First derived grammar_coverage_matrix.json artifact created.
[PASS] coverage matrix contains 6 nodes and 7 stages.
[PASS] stage_matrix contains focus/recycle/preview/blocked/maintenance/out_of_scope buckets.
[PASS] node_matrix preserves static order-table order.
[PASS] Derived matrix preserves learner_state_write = false.
[PASS] No validator / learner-facing practice artifact created.
[PASS] No learner state write path added.
[NOT_CHECKED] GitHub Actions CI readback pending after replay on latest main.
```

### Local validation evidence

```text
json.loads(grammar_coverage_matrix.json) = PASS
stage_count = 7
node_count = 6
all node_matrix learner_state_write flags are false = PASS
all stage role count totals equal node_count = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M7 through R5-M10 = 4 tasks left

Current sub-task status:
R5-M6 -> COMPLETED_CI_RETRY_PENDING
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_PENDING
```

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
Wait for rerun CI on PR #11 latest head.

If CI success:
merge PR #11 and continue R5-M7.

If CI failure:
inspect failed pytest output and patch only the failing surface.
```
