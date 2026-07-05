# R5-M7 Static Grammar Query Index Generator

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M7 build static grammar query index generator

Branch:
codex/r5-m7-grammar-query-index

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/grammar/grammar_nodes.json
- ulga/grammar/grammar_order_table.json
- ulga/grammar/grammar_coverage_matrix.json

Deliverable:
- ulga/builders/build_static_grammar_query_index.py
- ulga/grammar/grammar_query_index.json
- docs/ulga/R5_M7_STATIC_GRAMMAR_QUERY_INDEX_GENERATOR.md
```

## 2. Core Execution

### Files created

```text
ulga/builders/build_static_grammar_query_index.py
ulga/grammar/grammar_query_index.json
docs/ulga/R5_M7_STATIC_GRAMMAR_QUERY_INDEX_GENERATOR.md
```

### Generator behavior

`build_static_grammar_query_index.py` reads:

```text
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
```

and writes:

```text
ulga/grammar/grammar_query_index.json
```

The generator builds static lookup surfaces:

```text
by_stage
by_stage_role
by_category
by_authority_status
node_summaries
```

The generator checks:

```text
grammar_nodes.json is a list
grammar_order_table.json has rows[]
grammar_coverage_matrix.json has node_matrix[]
duplicate grammar_id values across inputs
nodes missing from order table
nodes missing from coverage matrix
unsupported stage-role values
```

### Derived query index artifact

The first query-index artifact contains:

```text
node_count = 6
stage_count = 7
category_count = 5
authority_status_count = 2
```

Query surfaces:

```text
by_stage: stage -> grammar_id[]
by_stage_role: stage -> role -> grammar_id[]
by_category: category -> grammar_id[]
by_authority_status: authority_status -> grammar_id[]
node_summaries: grammar_id -> static lookup summary
```

### Scope control

```text
R5-M7 only creates the static query-index generator and first derived query index.
R5-M7 does not create a validator.
R5-M7 does not generate learner-facing practice.
R5-M7 does not write learner state.
R5-M7 does not modify grammar_nodes.json, grammar_edges.json, grammar_order_table.json, or grammar_coverage_matrix.json.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] Static grammar query-index generator created.
[PASS] First derived grammar_query_index.json artifact created.
[PASS] query index contains 6 nodes and 7 stages.
[PASS] stage/category/role/status lookup surfaces are present.
[PASS] node_summaries preserve order/prerequisite/stage-role data.
[PASS] Derived query index preserves learner_state_write = false.
[PASS] No validator / learner-facing practice artifact created.
[PASS] No learner state write path added.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

### Local validation evidence

```text
json.loads(grammar_query_index.json) = PASS
node_count = 6
stage_count = 7
all node_summaries learner_state_write flags are false = PASS
all by_stage_role stage buckets exist = PASS
all by_category IDs resolve to node_summaries = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M8 through R5-M10 = 3 tasks left

Current sub-task status:
R5-M7 -> COMPLETED
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

Reason: this task created generator and derived query-index artifacts and local structural checks passed, but GitHub Actions CI readback was not confirmed at file creation time.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M8 build static grammar artifact validator

唯一執行動作:
Create a static validator that checks grammar_nodes.json, grammar_edges.json, grammar_order_table.json, grammar_coverage_matrix.json, and grammar_query_index.json for parseability, reference resolution, ordering consistency, query-index coverage, and learner_state_write=false.
```
