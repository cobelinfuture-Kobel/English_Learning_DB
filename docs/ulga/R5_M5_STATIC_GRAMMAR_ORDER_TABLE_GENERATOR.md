# R5-M5 Static Grammar Order Table Generator

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M5 build static grammar order table generator

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/schemas/grammar_node.schema.json
- ulga/schemas/grammar_edge.schema.json
- ulga/grammar/grammar_nodes.json
- ulga/grammar/grammar_edges.json

Deliverable:
- ulga/builders/build_static_grammar_order_table.py
- ulga/grammar/grammar_order_table.json
- docs/ulga/R5_M5_STATIC_GRAMMAR_ORDER_TABLE_GENERATOR.md
```

## 2. Core Execution

### Files inspected

```text
AGENTS.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
ulga/schemas/grammar_node.schema.json
ulga/schemas/grammar_edge.schema.json
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_edges.json
```

### Files created

```text
ulga/builders/build_static_grammar_order_table.py
ulga/grammar/grammar_order_table.json
docs/ulga/R5_M5_STATIC_GRAMMAR_ORDER_TABLE_GENERATOR.md
```

### Generator behavior

`build_static_grammar_order_table.py` reads:

```text
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_edges.json
```

and writes:

```text
ulga/grammar/grammar_order_table.json
```

The generator implements a deterministic static order pass:

```text
REQUIRES: target must appear before source
PRECEDES: source must appear before target
REINFORCES / CONTRASTS_WITH / CONFUSABLE_WITH: ignored for first-order sequencing
```

It also checks:

```text
duplicate grammar_id values
unknown edge source grammar_id
unknown edge target grammar_id
unsupported edge relation
order-cycle detection
```

### Derived order table artifact

The first derived order-table artifact contains 6 ordered grammar nodes:

```text
1. GRAMMAR_BE_VERB_BASIC
2. GRAMMAR_SUBJECT_PRONOUNS
3. GRAMMAR_CAN_STATEMENT
4. GRAMMAR_THIS_IS
5. GRAMMAR_THERE_IS
6. GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

### Scope control

```text
R5-M5 only creates the static order-table generator and first derived order table.
R5-M5 does not create a validator.
R5-M5 does not implement coverage-matrix generation.
R5-M5 does not generate learner-facing practice.
R5-M5 does not write learner state.
R5-M5 does not modify node or edge pilot seeds.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] Static grammar order-table generator created.
[PASS] First derived grammar_order_table.json artifact created.
[PASS] order table contains 6 ordered rows.
[PASS] REQUIRES constraints are represented as prerequisite-before-dependent order constraints.
[PASS] PRECEDES constraints are represented as source-before-target order constraints.
[PASS] Derived table preserves learner_state_write = false.
[PASS] No validator / coverage matrix / learner-facing practice artifact created.
[PASS] No learner state write path added.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

### Local validation evidence

```text
python local dry-run of build_order_table(nodes, edges) = PASS
ordered_node_count = 6
edge_count = 5
all order constraints satisfied = PASS
cycle detection path exists in generator = PASS
learner_state_write flags remain false = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M6 through R5-M10 = 5 tasks left

Current sub-task status:
R5-M5 -> COMPLETED
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

Reason: this task created generator and derived order-table artifacts and local structural checks passed, but GitHub Actions CI readback was not confirmed at file creation time.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M6 build grammar coverage matrix generator

唯一執行動作:
Create the static grammar coverage matrix generator that reads grammar_nodes.json and grammar_order_table.json and emits the first coverage-matrix artifact, without creating learner-facing practice or learner state writes.
```
