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
EDGE_BATCH_DRAFT_SUPERSEDED_BY_R6_M4_R6_M5_ON_SAME_BRANCH
```

R6-M3 adds matching edges for the R6-M2 A1 / A1_PLUS source-only node batch. It intentionally stays on the same branch and PR as R6-M2. R6-M4 and R6-M5 later rebuild derived artifacts and sync validation / CI expectations on this same branch.

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

Each R6-M2 node now has at least one edge connection.

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

## 6. Follow-up Sync

```text
R6-M4 rebuilt grammar_order_table.json, grammar_coverage_matrix.json, and grammar_query_index.json.
R6-M5 refreshed grammar_artifact_validation_report.json and tests/ci/test_static_grammar_artifacts.py.
```

## 7. Gate & Distance Update

```text
[PASS] Matching edge batch added on the same R6-M2 branch.
[PASS] 11 new edges added, under R6-M1 recommended cap of 20.
[PASS] Every R6-M2 node has at least one edge connection.
[PASS] All new edges are candidate records.
[PASS] All new edges preserve generated_content=false.
[PASS] All new edges preserve learner_state_write=false.
[PASS] Source evidence is non-empty for every new edge.
[PASS] R6-M4 / R6-M5 follow-up sync completed on the same branch.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
Run GitHub Actions CI for PR #18.

If CI success, mark PR #18 ready and merge.
If CI failure, stop and patch only the failing validation / CI surface.
```
