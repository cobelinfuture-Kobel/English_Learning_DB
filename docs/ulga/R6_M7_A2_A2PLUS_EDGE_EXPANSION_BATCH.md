# R6-M7 A2 / A2_PLUS Grammar Edge Expansion Batch

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M7 add matching A2 / A2_PLUS edge expansion batch

Branch:
codex/r6-m6-a2-a2plus-node-batch

PR:
#19

Status:
A2_A2PLUS_EDGE_BATCH_DRAFT_ON_EXISTING_R6_M6_BRANCH
```

R6-M7 adds matching edges for the R6-M6 A2 / A2_PLUS node-only batch. It intentionally stays on the same branch and PR as R6-M6.

## 2. Scope Lock

```text
Allowed:
- modify ulga/grammar/grammar_edges.json
- add matching edges for the 6 R6-M6 candidate nodes
- keep all new edges candidate / operator_review_required
- keep learner_state_write=false
- keep generated_content=false

Forbidden in R6-M7:
- no grammar_nodes.json modification
- no derived artifact rebuild
- no validator code change
- no CI test change
- no learner-facing practice generation
- no learner state write
- no merge of PR #19
```

## 3. Edges Added

R6-M7 adds 6 candidate edges:

```text
GEDGE_000017  GRAMMAR_PAST_SIMPLE_REGULAR -> REQUIRES -> GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
GEDGE_000018  GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC -> REQUIRES -> GRAMMAR_PAST_SIMPLE_REGULAR
GEDGE_000019  GRAMMAR_FUTURE_GOING_TO_BASIC -> REQUIRES -> GRAMMAR_BE_VERB_BASIC
GEDGE_000020  GRAMMAR_COMPARATIVES_BASIC -> REQUIRES -> GRAMMAR_REGULAR_PLURAL_NOUNS
GEDGE_000021  GRAMMAR_COUNTABLE_UNCOUNTABLE_SOME_ANY -> REQUIRES -> GRAMMAR_REGULAR_PLURAL_NOUNS
GEDGE_000022  GRAMMAR_ADVERBS_OF_FREQUENCY_BASIC -> REQUIRES -> GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
```

## 4. Coverage Against R6-M6 Nodes

Each R6-M6 node now has at least one edge connection:

```text
GRAMMAR_PAST_SIMPLE_REGULAR: GEDGE_000017, GEDGE_000018
GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC: GEDGE_000018
GRAMMAR_FUTURE_GOING_TO_BASIC: GEDGE_000019
GRAMMAR_COMPARATIVES_BASIC: GEDGE_000020
GRAMMAR_COUNTABLE_UNCOUNTABLE_SOME_ANY: GEDGE_000021
GRAMMAR_ADVERBS_OF_FREQUENCY_BASIC: GEDGE_000022
```

## 5. Authority Status

All new R6-M7 edges are:

```text
authority_status = candidate
confidence = operator_review_required
direction = directed
relation = REQUIRES
traceability.generated_content = false
traceability.learner_state_write = false
```

R6-M7 does not promote candidate edges to accepted.

## 6. Known Artifact Drift

R6-M7 still does not rebuild derived artifacts. The following artifacts remain stale until R6-M8:

```text
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/reports/grammar_artifact_validation_report.json
tests/ci/test_static_grammar_artifacts.py
```

Therefore PR #19 remains draft and must not be merged until:

```text
R6-M8 rebuild derived artifacts through builders
R6-M9 run validator and CI-safe test sync
```

## 7. Gate & Distance Update

```text
[PASS] Matching edge batch added on the same R6-M6 branch.
[PASS] 6 new edges added, under R6-M1 recommended cap of 20.
[PASS] Every R6-M6 node has at least one edge connection.
[PASS] No derived artifacts rebuilt.
[PASS] All new edges are candidate records.
[PASS] All new edges preserve generated_content=false.
[PASS] All new edges preserve learner_state_write=false.
[PASS] Source evidence is non-empty for every new edge.
[EXPECTED_BLOCKED] Current CI validator will detect source/derived drift until R6-M8 / R6-M9.
```

```text
ENGLISH_GRAMMAR_STATUS = A2_A2PLUS_EDGE_BATCH_CI_EXPECTED_BLOCKED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
R6-M8 rebuild derived artifacts through builders on the same branch.

Do not merge PR #19 before R6-M8 and R6-M9 pass.
```
