# R6-M4 Rebuild Derived Grammar Artifacts

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M4 rebuild derived artifacts through builders

Branch:
codex/r6-m2-a1-a1plus-node-batch

Status:
DERIVED_ARTIFACTS_REBUILT_AND_R6_M5_SYNCED
```

R6-M4 rebuilds the static derived artifacts after the R6-M2 node batch and R6-M3 edge batch. It stays on PR #18.

## 2. Scope Lock

```text
Allowed:
- rebuild ulga/grammar/grammar_order_table.json
- rebuild ulga/grammar/grammar_coverage_matrix.json
- rebuild ulga/grammar/grammar_query_index.json

Forbidden in R6-M4:
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no validator code change
- no CI test change
- no learner-facing practice generation
- no learner state write
- no merge of PR #18
```

## 3. Rebuilt Artifacts

```text
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
```

## 4. Rebuild Summary

```text
grammar_order_table.summary.node_count = 16
grammar_order_table.summary.edge_count = 16
grammar_order_table.summary.ordered_node_count = 16

grammar_coverage_matrix.summary.node_count = 16
grammar_coverage_matrix.summary.stage_count = 7
grammar_coverage_matrix.summary.authority_status_counts.accepted = 5
grammar_coverage_matrix.summary.authority_status_counts.candidate = 11

grammar_query_index.summary.node_count = 16
grammar_query_index.summary.stage_count = 7
grammar_query_index.summary.category_count = 14
grammar_query_index.summary.authority_status_count = 2
```

## 5. Resulting Static Order

```text
1. GRAMMAR_BE_VERB_BASIC
2. GRAMMAR_SUBJECT_PRONOUNS
3. GRAMMAR_CAN_STATEMENT
4. GRAMMAR_THIS_IS
5. GRAMMAR_ARTICLES_BASIC
6. GRAMMAR_BASIC_PREPOSITIONS_PLACE
7. GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
8. GRAMMAR_REGULAR_PLURAL_NOUNS
9. GRAMMAR_THERE_IS
10. GRAMMAR_DEMONSTRATIVES_CONTRAST
11. GRAMMAR_OBJECT_PRONOUNS_BASIC
12. GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
13. GRAMMAR_PRESENT_SIMPLE_NEGATIVES
14. GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS
15. GRAMMAR_WH_QUESTIONS_BE_DO_BASIC
16. GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

## 6. R6-M5 Follow-up

R6-M5 refreshed:

```text
ulga/reports/grammar_artifact_validation_report.json
tests/ci/test_static_grammar_artifacts.py
```

The branch now awaits GitHub Actions CI readback.

## 7. Gate & Distance Update

```text
[PASS] order table rebuilt to 16 nodes / 16 edges.
[PASS] coverage matrix rebuilt to 16 nodes / 7 stages.
[PASS] query index rebuilt to 16 nodes / 14 categories.
[PASS] learner_state_write=false preserved in derived artifacts.
[PASS] No source node / edge edits made in R6-M4.
[PASS] No learner-facing practice artifact created.
[PASS] No learner state write path added.
[PASS] R6-M5 validator / CI-safe test sync completed on the same branch.
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
