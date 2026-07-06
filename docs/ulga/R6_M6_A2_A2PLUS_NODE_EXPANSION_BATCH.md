# R6-M6 A2 / A2_PLUS Grammar Node Expansion Batch

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M6 add A2 / A2_PLUS expansion batch

Branch:
codex/r6-m6-a2-a2plus-node-batch

Status:
A2_A2PLUS_NODE_ONLY_BATCH_DRAFT
```

R6-M6 adds a small A2 / A2_PLUS grammar node-only batch to `grammar_nodes.json`. It does not add edges, rebuild derived artifacts, generate learner-facing practice, or write learner state.

## 2. Scope Lock

```text
Allowed:
- modify ulga/grammar/grammar_nodes.json
- add 5 to 15 A2 / A2_PLUS candidate nodes
- keep learner_state_write=false
- keep generated_content=false

Forbidden in R6-M6:
- no grammar_edges.json modification
- no derived artifact rebuild
- no validator code change
- no CI test change
- no learner-facing practice generation
- no learner state write
- no B1 / B2 bulk expansion
```

## 3. New Nodes Added

R6-M6 adds 6 source-only candidate nodes:

```text
GRAMMAR_PAST_SIMPLE_REGULAR
GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC
GRAMMAR_FUTURE_GOING_TO_BASIC
GRAMMAR_COMPARATIVES_BASIC
GRAMMAR_COUNTABLE_UNCOUNTABLE_SOME_ANY
GRAMMAR_ADVERBS_OF_FREQUENCY_BASIC
```

## 4. Stage Placement

A2 focus candidates:

```text
GRAMMAR_PAST_SIMPLE_REGULAR
GRAMMAR_FUTURE_GOING_TO_BASIC
GRAMMAR_COMPARATIVES_BASIC
GRAMMAR_ADVERBS_OF_FREQUENCY_BASIC
```

A2_PLUS focus candidates:

```text
GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC
GRAMMAR_COUNTABLE_UNCOUNTABLE_SOME_ANY
```

## 5. Authority Status

All new R6-M6 nodes are:

```text
authority_status = candidate
confidence = operator_review_required
traceability.generated_content = false
traceability.learner_state_write = false
```

R6-M6 does not promote any candidate node to accepted authority.

## 6. Known Artifact Drift

R6-M6 is intentionally node-only. Because edges and derived artifacts are not updated in this milestone, the following artifacts still reflect the prior 16-node / 16-edge R6-M5 state:

```text
ulga/grammar/grammar_edges.json
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/reports/grammar_artifact_validation_report.json
tests/ci/test_static_grammar_artifacts.py
```

Therefore this branch should remain draft / unmerged until a follow-up sequence restores consistency:

```text
R6-M7 add matching A2 / A2_PLUS edge expansion batch
R6-M8 rebuild derived artifacts through builders
R6-M9 run validator and CI-safe test sync
```

## 7. Gate & Distance Update

```text
[PASS] 6 new nodes added, within R6-M1 A2/A2_PLUS cap of 5 to 15.
[PASS] No B1 / B2 bulk expansion.
[PASS] No edges added.
[PASS] No derived artifacts rebuilt.
[PASS] All new nodes are candidate records.
[PASS] All new nodes preserve generated_content=false.
[PASS] All new nodes preserve learner_state_write=false.
[PASS] Source evidence is non-empty for every new node.
[EXPECTED_BLOCKED] Current CI validator will detect source/derived drift until R6-M8 / R6-M9.
```

```text
ENGLISH_GRAMMAR_STATUS = A2_A2PLUS_NODE_BATCH_CI_EXPECTED_BLOCKED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
R6-M7 add matching A2 / A2_PLUS edge expansion batch on the same branch.

Do not merge this PR before R6-M7, R6-M8, and R6-M9 pass.
```
