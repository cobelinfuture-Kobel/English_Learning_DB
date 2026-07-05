# R6-M1 GrammarSkillTree Expansion Batch Policy

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M1 define expansion batch policy and source-evidence selection rules

Branch:
codex/r6-m1-expansion-batch-policy

Status:
CONTRACT_ONLY_NO_NODE_OR_EDGE_EXPANSION
```

R6-M1 locks the batch policy for future GrammarSkillTree expansion. It does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, or tests.

## 2. Baseline

R6-M0 defines R6 as small-batch, static/offline expansion. Future source-artifact changes must rebuild artifacts in this order:

```text
1. build_static_grammar_order_table.py
2. build_static_grammar_coverage_matrix.py
3. build_static_grammar_query_index.py
4. validate_static_grammar_artifacts.py
5. pytest tests/ci/test_static_grammar_artifacts.py
```

## 3. Batch Policy

Allowed batch types:

```text
NODE_BATCH: adds grammar nodes only.
EDGE_BATCH: adds grammar edges only.
DERIVED_REBUILD_BATCH: rebuilds order, coverage, query, and validation artifacts.
QA_BATCH: checks validator report and CI readback.
```

Required sequence:

```text
NODE_BATCH -> EDGE_BATCH -> DERIVED_REBUILD_BATCH -> QA_BATCH
```

Batch caps:

```text
First A1/A1_PLUS NODE_BATCH: 5 to 12 nodes.
First EDGE_BATCH: enough edges to connect each new node, recommended cap 20.
A2/A2_PLUS NODE_BATCH: 5 to 15 nodes.
B1/B1_PLUS/B2 planning batch: candidate-only unless separately approved.
```

R6 must not import a full A1-B2 graph in one commit.

## 4. Source-Evidence Rules

Allowed source roles:

```text
authority_source
normalized_authority_artifact
candidate_evidence
operator_design_contract
```

Every new node and edge must include non-empty `source_evidence`.

Accepted records require authority or normalized-authority evidence. Candidate records may use candidate evidence but must remain review-gated.

Blocked evidence use:

```text
Reading text alone must not promote a grammar node to accepted.
AI suggestion alone must not promote a grammar node to accepted.
Unreviewed generated examples must not become authority evidence.
```

## 5. First Expansion Candidate Surface

R6-M2 should focus on A1 / A1_PLUS gaps only. Candidate areas:

```text
articles: a / an / the basics
determiners: this / that / these / those contrast
regular plural nouns
possessive adjectives
object pronouns
simple prepositions
present simple statements
present simple negatives
present simple yes/no questions
WH questions with be / do
```

This is a planning surface only. R6-M1 does not add these nodes.

## 6. Future Record Checklist

New node requirements:

```text
grammar_id
label
category
description
authority_status
cefr_band
introduced_stage
stage_roles for all canonical stages
source_evidence
traceability.generated_content = false
traceability.learner_state_write = false
```

New edge requirements:

```text
edge_id
source
target
relation
direction
authority_status
confidence
source_evidence
traceability.generated_content = false
traceability.learner_state_write = false
```

## 7. Validation Requirements

After any future node or edge expansion:

```text
all grammar_id values are unique
all edge_id values are unique
all edge refs resolve
ordering constraints are satisfied
coverage matrix covers every node
query index covers every node
learner_state_write=false across all static artifacts
CI-safe pytest target passes
```

## 8. Out-of-Scope for R6-M1

```text
No grammar_nodes.json modification.
No grammar_edges.json modification.
No derived artifact rebuild.
No validator code change.
No CI test change.
No learner-facing practice generation.
No learner state write.
No Reading / Writing / Listening / Speaking implementation.
No direct A1-B2 bulk expansion.
```

## 9. Gate & Distance Update

```text
[PASS] Batch types are defined.
[PASS] Batch size caps are defined.
[PASS] Batch dependency sequence is defined.
[PASS] Source-evidence roles are defined.
[PASS] Accepted vs candidate policy is explicit.
[PASS] First expansion candidate surface is identified without adding nodes.
[PASS] Future node and edge checklists are defined.
[PASS] Validation requirements are defined.
[PASS] R6-M1 does not modify grammar source artifacts.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 10. Next Shortest Step

```text
NEXT_SHORT_STEP:
Run GitHub Actions CI for R6-M1 batch policy branch.

If CI success:
merge R6-M1 and proceed to R6-M2 planning.

If CI failure:
stop and patch only the failing documentation / CI surface.
```
