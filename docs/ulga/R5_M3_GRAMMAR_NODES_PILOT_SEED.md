# R5-M3 Grammar Nodes Pilot Seed

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M3 seed grammar_nodes.json small pilot

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/schemas/grammar_node.schema.json from R5-M1 branch context

Deliverable:
- ulga/grammar/grammar_nodes.json
- docs/ulga/R5_M3_GRAMMAR_NODES_PILOT_SEED.md
```

## 2. Core Execution

### Files inspected

```text
AGENTS.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
ulga/schemas/grammar_node.schema.json
```

### Files created

```text
ulga/grammar/grammar_nodes.json
docs/ulga/R5_M3_GRAMMAR_NODES_PILOT_SEED.md
```

### Pilot node set

R5-M3 seeds a small GrammarSkillTree pilot set containing 6 grammar nodes:

```text
GRAMMAR_BE_VERB_BASIC
GRAMMAR_SUBJECT_PRONOUNS
GRAMMAR_THIS_IS
GRAMMAR_CAN_STATEMENT
GRAMMAR_THERE_IS
GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

The pilot intentionally covers:

```text
A1 focus examples
A1_PLUS staged introduction
A2 candidate expansion
blocked-before behavior
focus / recycle / preview / blocked / maintenance stage roles
source_evidence traceability
AI candidate guardrails
learner_state_write = false
```

### Scope control

```text
R5-M3 only seeds grammar_nodes.json.
R5-M3 does not create grammar_edges.json.
R5-M3 does not implement order-table generation.
R5-M3 does not implement coverage-matrix generation.
R5-M3 does not implement validators.
R5-M3 does not generate learner-facing practice.
R5-M3 does not write learner state.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] grammar_nodes.json created.
[PASS] Small pilot contains 6 grammar nodes.
[PASS] Each pilot node follows grammar_node.schema.json field contract.
[PASS] Every node has source_evidence.
[PASS] Every node has traceability.generated_content = false.
[PASS] Every node has traceability.learner_state_write = false.
[PASS] No grammar_edges.json seeded in this milestone.
[PASS] No out-of-scope expansion.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

### Local validation evidence

```text
json.loads(grammar_nodes.json) = PASS
pilot node count = 6
all grammar_id values are unique = PASS
all source_evidence arrays are non-empty = PASS
all learner_state_write flags are false = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M4 through R5-M10 = 7 tasks left

Current sub-task status:
R5-M3 -> COMPLETED
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

Reason: this task created a pilot data artifact and structural checks passed, but GitHub Actions CI readback was not confirmed at file creation time.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M4 seed grammar_edges.json small pilot

唯一執行動作:
Create ulga/grammar/grammar_edges.json with a small pilot edge set that conforms to grammar_edge.schema.json and references only grammar_id values present in grammar_nodes.json.
```
