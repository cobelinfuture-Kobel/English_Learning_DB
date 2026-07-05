# R6-M2 A1 / A1_PLUS Grammar Node Expansion Batch

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M2 add first A1 / A1_PLUS node expansion batch

Branch:
codex/r6-m2-a1-a1plus-node-batch

Status:
SOURCE_ONLY_BATCH_DRAFT_SUPERSEDED_BY_R6_M3_ON_SAME_BRANCH
```

R6-M2 adds the first A1 / A1_PLUS grammar node batch to `grammar_nodes.json` only. It intentionally does not add edges and does not rebuild derived artifacts. R6-M3 later adds matching edges on the same branch.

## 2. Scope Lock

```text
Allowed:
- modify ulga/grammar/grammar_nodes.json
- add 5 to 12 new A1 / A1_PLUS candidate nodes
- keep learner_state_write=false
- keep generated_content=false

Forbidden in R6-M2:
- no grammar_edges.json modification
- no derived artifact rebuild
- no validator code change
- no CI test change
- no learner-facing practice generation
- no learner state write
```

## 3. New Nodes Added

R6-M2 adds 10 source-only candidate nodes:

```text
GRAMMAR_ARTICLES_BASIC
GRAMMAR_DEMONSTRATIVES_CONTRAST
GRAMMAR_REGULAR_PLURAL_NOUNS
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
GRAMMAR_OBJECT_PRONOUNS_BASIC
GRAMMAR_BASIC_PREPOSITIONS_PLACE
GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
GRAMMAR_PRESENT_SIMPLE_NEGATIVES
GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS
GRAMMAR_WH_QUESTIONS_BE_DO_BASIC
```

## 4. Authority Status

All new R6-M2 nodes are `candidate`, not `accepted`.

Reason:

```text
R6-M2 uses the R6-M1 candidate planning surface as source evidence.
R6-M2 does not promote AI-authored expansion records to accepted authority.
Accepted promotion requires later authority / normalized-authority evidence review.
```

## 5. Stage Placement

A1 focus candidates:

```text
GRAMMAR_ARTICLES_BASIC
GRAMMAR_REGULAR_PLURAL_NOUNS
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
GRAMMAR_BASIC_PREPOSITIONS_PLACE
```

A1_PLUS focus candidates:

```text
GRAMMAR_DEMONSTRATIVES_CONTRAST
GRAMMAR_OBJECT_PRONOUNS_BASIC
GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS
GRAMMAR_PRESENT_SIMPLE_NEGATIVES
GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS
GRAMMAR_WH_QUESTIONS_BE_DO_BASIC
```

## 6. Known Artifact Drift

R6-M2 is intentionally source-only. Because derived artifacts are not rebuilt in this milestone, the following artifacts still reflect the previous 6-node pilot until R6-M4:

```text
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/reports/grammar_artifact_validation_report.json
```

Therefore this branch should remain draft / unmerged until the follow-up sequence restores consistency:

```text
R6-M3 add matching edge expansion batch
R6-M4 rebuild derived artifacts through builders
R6-M5 run validator and CI-safe test hook
```

## 7. Gate & Distance Update

```text
[PASS] 10 new nodes added, within R6-M1 cap of 5 to 12.
[PASS] No edges added during R6-M2.
[PASS] No derived artifacts rebuilt.
[PASS] All new nodes are candidate records.
[PASS] All new nodes preserve generated_content=false.
[PASS] All new nodes preserve learner_state_write=false.
[PASS] Source evidence is non-empty for every new node.
[EXPECTED_BLOCKED] Current CI validator will detect source/derived drift until R6-M4.
```

```text
ENGLISH_GRAMMAR_STATUS = SOURCE_ONLY_BATCH_CI_EXPECTED_BLOCKED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
R6-M4 rebuild derived artifacts through builders on the same branch.

R6-M3 has already added matching edges on this branch.
Do not merge PR #18 before R6-M4 and R6-M5 pass.
```
