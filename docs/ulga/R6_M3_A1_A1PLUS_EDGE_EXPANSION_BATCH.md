# R6-M3 A1 / A1_PLUS Grammar Edge Expansion Batch

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M3 add matching edge expansion batch

Branch:
codex/r6-m2-a1-a1plus-node-batch

Status:
EDGE_BATCH_DRAFT_ON_EXISTING_R6_M2_BRANCH
```

R6-M3 adds matching edges for the R6-M2 A1 / A1_PLUS source-only node batch. It intentionally stays on the same branch and PR as R6-M2.

## 2. Scope Lock

```text
Allowed:
- modify ulga/grammar/grammar_edges.json
- add matching edges for the 10 R6-M2 candidate nodes
- keep all new edges candidate / operator_review_required
- keep learner_state_write=false
- keep generated_content=false

Forbidden in R6-M3:
- no grammar_nodes.json modification
- no derived artifact rebuild
- no validator code change
- no CI test change
- no learner-facing practice generation
- no learner state write
- no merge of PR #18
```

## 3. Edges Added

R6-M3 adds 11 candidate edges:

```text
GEDGE_000006  GRAMMAR_ARTICLES_BASIC -> REQUIRES -> GRAMMAR_THIS_IS
GEDGE_000007  GRAMMAR_DEMONSTRATIVES_CONTRAST -> REQUIRES -> GRAMMAR_THIS_IS
GEDGE_000008  GRAMMAR_REGULAR_PLURAL_NOUNS -> REQUIRES -> GRAMMAR_ARTICLES_BASIC
GEDGE_000009  GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC -> REQUIRES -> GRAMMAR_SUBJECT_PRONOUNS
GEDGE_000010  GRAMMAR_OBJECT_PRONOUNS_BASIC -> REQUIRES -> GRAMMAR_SUBJECT_PRONOUNS
GEDGE_000011  GRAMMAR_BASIC_PREPOSITIONS_PLACE -> REQUIRES -> GRAMMAR_BE_VERB_BASIC
GEDGE_000012  GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS -> REQUIRES -> GRAMMAR_SUBJECT_PRONOUNS
GEDGE_000013  GRAMMAR_PRESENT_SIMPLE_NEGATIVES -> REQUIRES -> GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
GEDGE_000014  GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS -> REQUIRES -> GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
GEDGE_000015  GRAMMAR_WH_QUESTIONS_BE_DO_BASIC -> REQUIRES -> GRAMMAR_BE_VERB_BASIC
GEDGE_000016  GRAMMAR_WH_QUESTIONS_BE_DO_BASIC -> REQUIRES -> GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS
```

## 4. Coverage Against R6-M2 Nodes

Each R6-M2 node now has at least one edge connection:

```text
GRAMMAR_ARTICLES_BASIC: GEDGE_000006, GEDGE_000008
GRAMMAR_DEMONSTRATIVES_CONTRAST: GEDGE_000007
GRAMMAR_REGULAR_PLURAL_NOUNS: GEDGE_000008
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC: GEDGE_000009
GRAMMAR_OBJECT_PRONOUNS_BASIC: GEDGE_000010
GRAMMAR_BASIC_PREPOSITIONS_PLACE: GEDGE_000011
GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS: GEDGE_000012, GEDGE_000013, GEDGE_000014
GRAMMAR_PRESENT_SIMPLE_NEGATIVES: GEDGE_000013
GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS: GEDGE_000014, GEDGE_000016
GRAMMAR_WH_QUESTIONS_BE_DO_BASIC: GEDGE_000015, GEDGE_000016
```

## 5. Authority Status

All new R6-M3 edges are:

```text
authority_status = candidate
confidence = operator_review_required
direction = directed
relation = REQUIRES
traceability.generated_content = false
traceability.learner_state_write = false
```

R6-M3 does not promote candidate edges to accepted.

## 6. Known Artifact Drift

R6-M3 still does not rebuild derived artifacts. The following artifacts remain stale until R6-M4:

```text
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/reports/grammar_artifact_validation_report.json
```

Therefore PR #18 remains draft and must not be merged until:

```text
R6-M4 rebuild derived artifacts through builders
R6-M5 run validator and CI-safe test hook
```

## 7. Gate & Distance Update

```text
[PASS] Matching edge batch added on the same R6-M2 branch.
[PASS] 11 new edges added, under R6-M1 recommended cap of 20.
[PASS] Every R6-M2 node has at least one edge connection.
[PASS] No derived artifacts rebuilt.
[PASS] All new edges are candidate records.
[PASS] All new edges preserve generated_content=false.
[PASS] All new edges preserve learner_state_write=false.
[PASS] Source evidence is non-empty for every new edge.
[EXPECTED_BLOCKED] Current CI validator will detect source/derived drift until R6-M4.
```

```text
ENGLISH_GRAMMAR_STATUS = EDGE_BATCH_CI_EXPECTED_BLOCKED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
R6-M4 rebuild derived artifacts through builders on the same branch.

Do not merge PR #18 before R6-M4 and R6-M5 pass.
```
