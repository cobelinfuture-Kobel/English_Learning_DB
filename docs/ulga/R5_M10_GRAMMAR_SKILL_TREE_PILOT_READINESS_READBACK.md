# R5-M10 GrammarSkillTree Pilot Implementation Readiness Readback

## 1. Current State

```text
Epic ID:
R5_GrammarSkillTree_PilotImplementation

Sub-task ID:
R5-M10 close R5 pilot implementation readiness readback

Branch:
codex/r5-m10-readiness-readback

Readback Status:
R5_PILOT_IMPLEMENTATION_READY_FOR_R6_DESIGN_REVIEW
```

R5 is a static/offline GrammarSkillTree pilot implementation line. It establishes the first contract-bound chain from grammar node schema through CI-safe validation, without creating learner-facing practice or learner-state writes.

## 2. Completed R5 Milestones

```text
R5-M1  grammar_node.schema.json                              COMPLETED_AND_MERGED
R5-M2  grammar_edge.schema.json                              COMPLETED_AND_MERGED
R5-M3  grammar_nodes.json small pilot                        COMPLETED_AND_MERGED
R5-M4  grammar_edges.json small pilot                        COMPLETED_AND_MERGED
R5-M5  static grammar_order_table generator/artifact          COMPLETED_AND_MERGED
R5-M6  static grammar_coverage_matrix generator/artifact      COMPLETED_AND_MERGED
R5-M7  static grammar_query_index generator/artifact          COMPLETED_AND_MERGED
R5-M8  static grammar artifact validator/report              COMPLETED_AND_MERGED
R5-M9  CI-safe validator pytest hook                          COMPLETED_AND_MERGED
R5-M10 pilot implementation readiness readback                IN_PROGRESS_THIS_DOC
```

## 3. R5 Artifact Inventory

### Schemas

```text
ulga/schemas/grammar_node.schema.json
ulga/schemas/grammar_edge.schema.json
```

### Static source artifacts

```text
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_edges.json
```

### Derived static artifacts

```text
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
```

### Builders

```text
ulga/builders/build_static_grammar_order_table.py
ulga/builders/build_static_grammar_coverage_matrix.py
ulga/builders/build_static_grammar_query_index.py
```

### Validator and report

```text
ulga/validators/validate_static_grammar_artifacts.py
ulga/reports/grammar_artifact_validation_report.json
```

### CI-safe test hook

```text
tests/ci/test_static_grammar_artifacts.py
```

### Closeout / readback docs

```text
docs/ulga/R5_M1_GRAMMAR_NODE_SCHEMA_IMPLEMENTATION.md
docs/ulga/R5_M2_GRAMMAR_EDGE_SCHEMA_IMPLEMENTATION.md
docs/ulga/R5_M3_GRAMMAR_NODES_PILOT_SEED.md
docs/ulga/R5_M4_GRAMMAR_EDGES_PILOT_SEED.md
docs/ulga/R5_M5_STATIC_GRAMMAR_ORDER_TABLE_GENERATOR.md
docs/ulga/R5_M6_STATIC_GRAMMAR_COVERAGE_MATRIX_GENERATOR.md
docs/ulga/R5_M6_CI_FAILURE_FIX_READBACK.md
docs/ulga/R5_M7_STATIC_GRAMMAR_QUERY_INDEX_GENERATOR.md
docs/ulga/R5_M8_STATIC_GRAMMAR_ARTIFACT_VALIDATOR.md
docs/ulga/R5_M9_STATIC_GRAMMAR_VALIDATOR_CI_HOOK.md
docs/ulga/R5_M10_GRAMMAR_SKILL_TREE_PILOT_READINESS_READBACK.md
```

## 4. Static Pilot Coverage

The R5 pilot currently contains:

```text
grammar_nodes = 6
grammar_edges = 5
order_table_rows = 6
coverage_matrix_nodes = 6
coverage_matrix_stages = 7
query_index_nodes = 6
validation_checks = 22
validation_failures = 0
```

Current static grammar nodes:

```text
GRAMMAR_BE_VERB_BASIC
GRAMMAR_SUBJECT_PRONOUNS
GRAMMAR_CAN_STATEMENT
GRAMMAR_THIS_IS
GRAMMAR_THERE_IS
GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

Current stage surface:

```text
A1
A1_PLUS
A2
A2_PLUS
B1
B1_PLUS
B2
```

Current query surfaces:

```text
by_stage
by_stage_role
by_category
by_authority_status
node_summaries
```

## 5. Validation and CI Readiness

R5-M8 created the static artifact validator. R5-M9 wired the validator into the repository's CI-safe pytest target under:

```text
tests/ci/test_static_grammar_artifacts.py
```

The CI-safe hook checks:

```text
validator report status = PASS
fail_count = 0
node_count = 6
edge_count = 5
learner_facing_practice = false
learner_state_write = false
required validator check surfaces exist
```

Required validator surfaces include:

```text
EDGE_REFS_RESOLVE
ORDERING_CONSTRAINTS_SATISFIED
COVERAGE_COVERS_NODES
COVERAGE_STAGE_KEYS_COMPLETE
COVERAGE_STAGE_ROLE_COUNTS
QUERY_COVERS_NODES
QUERY_STAGE_ROLE_SURFACE_COMPLETE
LEARNER_STATE_WRITE_FALSE
```

## 6. Scope Boundary

R5 remains static/offline and pilot-only.

```text
R5 does not generate learner-facing practice.
R5 does not write learner state.
R5 does not implement adaptive learner gates.
R5 does not implement runtime scheduling.
R5 does not implement Reading / Writing / Listening / Speaking systems.
R5 does not perform R6 A1-B2 expansion.
R5 does not promote candidate grammar content automatically.
```

Allowed R5 outputs are limited to schema, static seed artifacts, deterministic derived static artifacts, validator/report, CI-safe test hook, and closeout/readback documentation.

## 7. Known Risks and R6 Handoff Notes

### R6 expansion risks

```text
R6 must expand grammar_nodes.json beyond the 6-node pilot.
R6 must expand grammar_edges.json beyond the 5-edge pilot.
R6 must preserve static/offline boundaries unless explicitly approved.
R6 must keep learner_state_write=false until a separate learner-state milestone is approved.
R6 must not generate learner-facing practice as a side effect of expansion.
R6 must update derived artifacts through builders, not by manual drift.
R6 must run validate_static_grammar_artifacts.py after any node/edge/order/coverage/query changes.
R6 must keep tests/ci/test_static_grammar_artifacts.py passing.
```

### Candidate handling

```text
GRAMMAR_PRESENT_CONTINUOUS_BASIC remains candidate / operator_review_required in the pilot.
Candidate nodes and edges must not be auto-promoted by generators or validators.
R6 may add more candidate records, but must preserve review-required semantics.
```

### Artifact drift control

```text
If grammar_nodes.json or grammar_edges.json changes, rebuild:
1. grammar_order_table.json
2. grammar_coverage_matrix.json
3. grammar_query_index.json
4. grammar_artifact_validation_report.json

Then run the CI-safe validator test.
```

## 8. Gate & Distance Update

### Gate Metrics

```text
[PASS] R5-M1 through R5-M9 artifacts are present on main before this readback branch.
[PASS] R5 static artifact chain is complete from schema to CI-safe validator hook.
[PASS] Validation report status is PASS.
[PASS] Validation report fail_count = 0.
[PASS] CI-safe pytest hook exists under tests/ci.
[PASS] R5 scope does not include learner-facing practice generation.
[PASS] R5 scope does not include learner-state writes.
[PASS] R5-M10 only adds readiness readback documentation.
[NOT_CHECKED] GitHub Actions CI readback for this documentation-only branch was not available at file creation time.
```

### Distance Vector

```text
R5 remaining tasks after this readback:
0

R5 pilot implementation line:
READY_TO_CLOSE_AFTER_CI

Next epic candidate:
R6 GrammarSkillTree A1-B2 expansion planning / design review
```

### English Grammar System Progress

```text
Grammar Authority ............ PILOT_READY
Pattern Authority ............ PARTIAL
Question / Practice Contract . NOT_STARTED
Validation Layer ............. PILOT_READY
Practice Generation .......... NOT_STARTED
Practice Export .............. NOT_STARTED
CI / Readback Sync ........... PENDING_THIS_BRANCH
Production Readiness ......... NOT_STARTED
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

Reason: R5-M10 is a readback-only documentation branch. R5-M1 through R5-M9 are already merged and CI-validated, but this R5-M10 branch still needs GitHub Actions readback before final closure.

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
Run GitHub Actions CI for this R5-M10 readiness readback branch.

If CI success:
merge R5-M10 and mark R5 pilot implementation line CLOSED_AS_PILOT_READY.

If CI failure:
stop and patch only the failing documentation / CI surface.
```

## 10. R6 Boundary

```text
R6 is not started by this document.
R6 should begin only after R5-M10 is merged and R5 is explicitly closed.
R6 first step should be a design/readiness scan, not direct expansion writes.
```
