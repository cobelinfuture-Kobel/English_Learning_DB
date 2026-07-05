# R6-M0 GrammarSkillTree A1-B2 Expansion Readiness Scan

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M0 GrammarSkillTree A1-B2 expansion planning / design readiness scan

Status:
DESIGN_READINESS_SCAN_ONLY
```

R5 is closed as pilot-ready. R6 may now be planned, but this milestone does not expand `grammar_nodes.json` or `grammar_edges.json`. It only defines the next expansion contract, acceptance gates, and safe execution boundary.

## 2. Source Baseline

R5 produced a static/offline pilot implementation chain:

```text
ulga/schemas/grammar_node.schema.json
ulga/schemas/grammar_edge.schema.json
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_edges.json
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/validators/validate_static_grammar_artifacts.py
ulga/reports/grammar_artifact_validation_report.json
tests/ci/test_static_grammar_artifacts.py
```

R5 pilot coverage:

```text
grammar_nodes = 6
grammar_edges = 5
stage_count = 7
validation_checks = 22
validation_failures = 0
```

## 3. R6 Objective

R6 should expand GrammarSkillTree from the R5 pilot seed toward a broader A1-B2 grammar authority graph while preserving static/offline boundaries.

R6 must answer:

```text
1. Which grammar nodes should be added first for A1 / A1+ / A2 readiness?
2. Which edge relations are mandatory before each new node can be ordered?
3. Which records remain accepted vs candidate / operator_review_required?
4. Which derived artifacts must be rebuilt after each expansion batch?
5. Which CI-safe checks must remain passing after every batch?
```

## 4. Proposed R6 Execution Boundary

R6 should use small batch expansion, not full A1-B2 bulk import in one commit.

Recommended R6 phases:

```text
R6-M0  Expansion readiness scan and contract lock
R6-M1  Define expansion batch policy and source-evidence selection rules
R6-M2  Add first A1 / A1_PLUS node expansion batch
R6-M3  Add matching edge expansion batch
R6-M4  Rebuild derived artifacts through builders
R6-M5  Run validator and CI-safe test hook
R6-M6  Add A2 / A2_PLUS expansion batch
R6-M7  Add B1 / B1_PLUS / B2 candidate-only planning batch
R6-M8  Expansion QA / drift audit
R6-M9  R6 closeout / R7 handoff
```

This sequencing is a proposed contract for R6. It does not perform any expansion in R6-M0.

## 5. Expansion Data Rules

Every new grammar node must include source evidence and preserve:

```text
traceability.generated_content = false
traceability.learner_state_write = false
```

Every new grammar edge must include source evidence and preserve:

```text
traceability.generated_content = false
traceability.learner_state_write = false
```

Candidate policy:

```text
AI may suggest candidates.
AI may not promote candidates to accepted.
operator_review_required records must remain review-gated.
candidate nodes / edges must not become learner-facing authority by default.
```

## 6. Artifact Rebuild Rule

If R6 changes `grammar_nodes.json` or `grammar_edges.json`, rebuild derived artifacts in this order:

```text
1. python ulga/builders/build_static_grammar_order_table.py
2. python ulga/builders/build_static_grammar_coverage_matrix.py
3. python ulga/builders/build_static_grammar_query_index.py
4. python ulga/validators/validate_static_grammar_artifacts.py
5. pytest tests/ci/test_static_grammar_artifacts.py
```

## 7. Acceptance Gates for First Expansion Batch

```text
[REQUIRED] Expansion batch size is capped.
[REQUIRED] Each new node has source_evidence.
[REQUIRED] Each new edge references existing or same-batch nodes.
[REQUIRED] No learner-facing practice is generated.
[REQUIRED] No learner state is written.
[REQUIRED] Derived artifacts are rebuilt after source artifact changes.
[REQUIRED] validate_static_grammar_artifacts.py exits PASS.
[REQUIRED] tests/ci/test_static_grammar_artifacts.py passes in CI.
```

Recommended first expansion batch size:

```text
new grammar nodes: 5 to 12
new grammar edges: enough to connect every new node to at least one prerequisite / ordering relation
```

## 8. Out-of-Scope for R6-M0

```text
No changes to grammar_nodes.json.
No changes to grammar_edges.json.
No derived artifact rebuild.
No validator code changes.
No CI test changes.
No learner-facing practice generation.
No learner state write.
No Reading / Writing / Listening / Speaking implementation.
No R6 bulk expansion.
```

## 9. Gate & Distance Update

```text
[PASS] R5 is closed as pilot-ready before R6 planning begins.
[PASS] R6-M0 is documentation-only.
[PASS] R6 expansion boundary is explicit.
[PASS] R6 artifact rebuild order is defined.
[PASS] R6 acceptance gates are defined.
[PASS] R6 does not start direct node / edge expansion.
[PASS] R6 keeps learner_state_write=false until separately approved.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 10. Next Shortest Step

```text
NEXT_SHORT_STEP:
Run GitHub Actions CI for R6-M0 readiness scan.

If CI success:
mark R6 planning ready.

If CI failure:
stop and patch only the failing documentation / CI surface.
```

## 11. Next Task After CI

```text
R6-M1 define expansion batch policy and source-evidence selection rules
```

R6-M1 should still be a contract task. Direct expansion of `grammar_nodes.json` and `grammar_edges.json` should begin only after the batch policy is locked.
