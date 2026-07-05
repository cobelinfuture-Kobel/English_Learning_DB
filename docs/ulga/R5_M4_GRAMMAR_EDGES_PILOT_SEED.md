# R5-M4 Grammar Edges Pilot Seed

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M4 seed grammar_edges.json small pilot

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/schemas/grammar_edge.schema.json
- ulga/grammar/grammar_nodes.json

Deliverable:
- ulga/grammar/grammar_edges.json
- docs/ulga/R5_M4_GRAMMAR_EDGES_PILOT_SEED.md
```

## 2. Core Execution

### Files inspected

```text
AGENTS.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
ulga/schemas/grammar_edge.schema.json
ulga/grammar/grammar_nodes.json
```

### Files created

```text
ulga/grammar/grammar_edges.json
docs/ulga/R5_M4_GRAMMAR_EDGES_PILOT_SEED.md
```

### Pilot edge set

R5-M4 seeds a small GrammarSkillTree pilot edge set containing 5 dependency/order edges:

```text
GEDGE_000001: GRAMMAR_THIS_IS REQUIRES GRAMMAR_BE_VERB_BASIC
GEDGE_000002: GRAMMAR_CAN_STATEMENT REQUIRES GRAMMAR_SUBJECT_PRONOUNS
GEDGE_000003: GRAMMAR_THERE_IS REQUIRES GRAMMAR_BE_VERB_BASIC
GEDGE_000004: GRAMMAR_PRESENT_CONTINUOUS_BASIC REQUIRES GRAMMAR_BE_VERB_BASIC
GEDGE_000005: GRAMMAR_CAN_STATEMENT PRECEDES GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

The pilot intentionally covers:

```text
REQUIRES dependency behavior
PRECEDES order-hint behavior
accepted edge status
candidate edge status
operator_review_required confidence
order_table_effect hints
learner_gate_policy hints
source_evidence traceability
learner_state_write = false
```

### Self-fix during task

An initial draft of `GEDGE_000005` had its PRECEDES direction expressed inconsistently. The file was rewritten so that the source/target direction now matches the rationale:

```text
source = GRAMMAR_CAN_STATEMENT
target = GRAMMAR_PRESENT_CONTINUOUS_BASIC
relation = PRECEDES
```

### Scope control

```text
R5-M4 only seeds grammar_edges.json.
R5-M4 does not modify grammar_nodes.json.
R5-M4 does not implement order-table generation.
R5-M4 does not implement coverage-matrix generation.
R5-M4 does not implement validators.
R5-M4 does not generate learner-facing practice.
R5-M4 does not write learner state.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] grammar_edges.json created.
[PASS] Small pilot contains 5 grammar edges.
[PASS] Each edge follows grammar_edge.schema.json field contract.
[PASS] Each source / target references a grammar_id from grammar_nodes.json.
[PASS] Directed relation semantics checked for REQUIRES and PRECEDES.
[PASS] Every edge has source_evidence.
[PASS] Every edge has traceability.generated_content = false.
[PASS] Every edge has traceability.learner_state_write = false.
[PASS] No generator / validator / practice artifact created.
[PASS] No out-of-scope expansion.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

### Local validation evidence

```text
json.loads(grammar_edges.json) = PASS
pilot edge count = 5
all edge_id values are unique = PASS
all source / target grammar IDs resolve to R5-M3 pilot nodes = PASS
all REQUIRES and PRECEDES edges are directed = PASS
all source_evidence arrays are non-empty = PASS
all learner_state_write flags are false = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M5 through R5-M10 = 6 tasks left

Current sub-task status:
R5-M4 -> COMPLETED
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

Reason: this task created a pilot edge artifact and structural checks passed, but GitHub Actions CI readback was not confirmed at file creation time.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M5 build static grammar order table generator

唯一執行動作:
Create the static grammar order table generator that reads grammar_nodes.json and grammar_edges.json and emits the first derived order-table artifact, without creating learner-facing practice or learner state writes.
```
