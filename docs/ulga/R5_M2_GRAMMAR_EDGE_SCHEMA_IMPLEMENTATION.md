# R5-M2 Grammar Edge Schema Implementation

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M2 create grammar_edge.schema.json

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
- ulga/schemas/grammar_node.schema.json from R5-M1 branch context

Deliverable:
- ulga/schemas/grammar_edge.schema.json
- docs/ulga/R5_M2_GRAMMAR_EDGE_SCHEMA_IMPLEMENTATION.md
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
ulga/schemas/grammar_edge.schema.json
docs/ulga/R5_M2_GRAMMAR_EDGE_SCHEMA_IMPLEMENTATION.md
```

### Implementation summary

R5-M2 creates the canonical JSON Schema for one GrammarSkillTree dependency edge.

The schema defines:

```text
edge_id
source
target
relation
direction
authority_status
confidence
rationale
stage_scope
order_table_effect
learner_gate_policy
ai_edge_policy
source_evidence
traceability
```

Supported relation types:

```text
REQUIRES
PRECEDES
REINFORCES
CONTRASTS_WITH
CONFUSABLE_WITH
```

The schema preserves the R4-M3 edge design boundary:

```text
Dependency edges support future order-table computation.
AI-suggested edges remain candidate/operator-review-only.
Learner gate hints are allowed, but learner state writes are forbidden.
The schema does not seed grammar_edges.json.
```

### Scope control

```text
R5-M2 only creates grammar_edge.schema.json.
R5-M2 does not seed grammar_edges.json.
R5-M2 does not modify grammar_node.schema.json.
R5-M2 does not implement order-table generation.
R5-M2 does not implement validators.
R5-M2 does not generate learner-facing practice.
R5-M2 does not write learner state.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] grammar_edge.schema.json created.
[PASS] Schema is valid JSON.
[PASS] Draft 2020-12 schema check passed locally.
[PASS] Pilot REQUIRES edge object validated against the schema locally.
[PASS] No out-of-scope expansion.
[NOT_CHECKED] GitHub Actions CI readback was not available in this task response.
```

### Local validation evidence

```text
json.loads(grammar_edge.schema.json) = PASS
jsonschema.Draft202012Validator.check_schema = PASS
sample REQUIRES edge validation = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M3 through R5-M10 = 8 tasks left

Current sub-task status:
R5-M2 -> COMPLETED
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

Reason: this task created a schema artifact and local schema checks passed, but GitHub Actions CI readback was not confirmed in this response.

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
R5-M3 seed grammar_nodes.json small pilot

唯一執行動作:
Create ulga/grammar/grammar_nodes.json with a small pilot set that conforms to grammar_node.schema.json, without creating grammar_edges.json.
```
