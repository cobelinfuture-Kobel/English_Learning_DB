# R5-M1 Grammar Node Schema Implementation

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M1 create grammar_node.schema.json

Data Sources:
- docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
- AGENTS.md
- docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md

Deliverable:
- ulga/schemas/grammar_node.schema.json
- docs/ulga/R5_M1_GRAMMAR_NODE_SCHEMA_IMPLEMENTATION.md
```

## 2. Core Execution

### Files inspected

```text
AGENTS.md
docs/governance/ENGLISH_GRAMMAR_PROJECT_GOVERNANCE.md
docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
```

### Files created

```text
ulga/schemas/grammar_node.schema.json
docs/ulga/R5_M1_GRAMMAR_NODE_SCHEMA_IMPLEMENTATION.md
```

### Implementation summary

R5-M1 creates the canonical JSON Schema for one GrammarSkillTree grammar node.

The schema defines:

```text
grammar_id
label
category
description
authority_status
cefr_band
egp_evidence_refs
introduced_stage
recycle_stages
blocked_before
stage_roles
example_patterns
links
source_evidence
ai_tagging_policy
mastery_gate_hints
traceability
```

The schema preserves the R4 design boundary:

```text
CEFR / EGP = level and construct evidence
GrammarSkillTree = internal teaching-order authority
AI output = candidate suggestion only
Learner state write = forbidden in this milestone
```

### Scope control

```text
R5-M1 only creates grammar_node.schema.json.
R5-M1 does not create grammar_edge.schema.json.
R5-M1 does not seed grammar_nodes.json.
R5-M1 does not implement generators.
R5-M1 does not implement validators.
R5-M1 does not generate learner-facing practice.
R5-M1 does not write learner state.
```

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] grammar_node.schema.json created.
[PASS] Schema is valid JSON.
[PASS] Draft 2020-12 schema check passed locally.
[PASS] Pilot sample object validated against the schema locally.
[PASS] No out-of-scope expansion.
[NOT_CHECKED] GitHub Actions CI readback was not available in this task response.
```

### Local validation evidence

```text
json.loads(grammar_node.schema.json) = PASS
jsonschema.Draft202012Validator.check_schema = PASS
sample grammar node validation = PASS
```

### Distance Vector

```text
Total remaining R5 tasks:
R5-M2 through R5-M10 = 9 tasks left

Current sub-task status:
R5-M1 -> COMPLETED
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
R5-M2 create grammar_edge.schema.json

唯一執行動作:
Create ulga/schemas/grammar_edge.schema.json using the R4-M3 dependency edge contract, without seeding grammar_edges.json.
```
