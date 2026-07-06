# R6-M11 A1 / A2 Expansion Readiness Closeout

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M11 close R6 A1/A2 expansion readiness readback

Branch:
codex/r6-m11-close-r6-a1-a2-readiness

Status:
R6_A1_A2_EXPANSION_CLOSEOUT_READBACK_ONLY
```

R6-M11 closes the current A1 / A1_PLUS and A2 / A2_PLUS GrammarSkillTree expansion line. This task does not add grammar nodes, add grammar edges, rebuild derived artifacts, change validator logic, change CI tests, generate learner-facing practice, or write learner state.

## 2. Closed Expansion Scope

R6 closed scope:

```text
A1 / A1_PLUS candidate expansion
A2 / A2_PLUS candidate expansion
static order / coverage / query rebuild
validator report sync
CI-safe pytest expectation sync
expansion QA / drift audit
```

R6 not closed scope:

```text
B1 / B1_PLUS / B2 implementation expansion
candidate-to-accepted authority promotion
learner-facing practice generation
adaptive planner runtime
Reading / Writing / Listening / Speaking implementation
commercial worksheet / public site work
```

## 3. Milestones Closed

```text
R6-M1: batch policy and source-evidence rules
R6-M2: A1 / A1_PLUS node batch
R6-M3: A1 / A1_PLUS matching edge batch
R6-M4: A1 / A1_PLUS derived rebuild
R6-M5: A1 / A1_PLUS validator / CI-safe test sync
R6-M6: A2 / A2_PLUS node batch
R6-M7: A2 / A2_PLUS matching edge batch
R6-M8: A2 / A2_PLUS derived rebuild
R6-M9: A2 / A2_PLUS validator / CI-safe test sync
R6-M10: expansion QA / drift audit
```

## 4. Current Artifact State

Static validation report is synchronized:

```text
status = PASS
node_count = 22
edge_count = 22
order_row_count = 22
coverage_node_count = 22
query_node_count = 22
check_count = 22
fail_count = 0
```

CI-safe test expectations are synchronized:

```text
EXPECTED_NODE_COUNT = 22
EXPECTED_EDGE_COUNT = 22
```

Authority boundary is unchanged:

```text
accepted = 5
candidate = 17
```

## 5. Usable State After R6

R6 output is usable as a static candidate grammar authority graph for A1 through A2_PLUS planning.

Usable surfaces:

```text
ulga/grammar/grammar_nodes.json
ulga/grammar/grammar_edges.json
ulga/grammar/grammar_order_table.json
ulga/grammar/grammar_coverage_matrix.json
ulga/grammar/grammar_query_index.json
ulga/reports/grammar_artifact_validation_report.json
tests/ci/test_static_grammar_artifacts.py
```

Allowed use:

```text
static grammar ordering reference
coverage / query surface inspection
candidate graph planning
future source-evidence review
future pattern / practice contract design
```

Blocked use:

```text
no direct learner-facing practice generation
no learner state write
no automatic promotion to accepted authority
no adaptive runtime gate activation
no B1 / B2 production expansion
```

## 6. Remaining Risks

```text
RISK-1: Candidate authority depth
Status: OPEN
Impact: Medium
Control: later source-evidence strengthening and candidate promotion audit.

RISK-2: Compact derived artifact rows
Status: OPEN
Impact: Low / Medium
Control: define query-index consumer contract before learner-facing use.

RISK-3: B1 / B1_PLUS / B2 not implemented
Status: OPEN / EXPECTED
Impact: Expected
Control: future B1/B2 work must start as candidate-only planning, not bulk implementation.
```

## 7. B1 / B2 Boundary Decision

The next B1 / B1_PLUS / B2 step must be candidate-only planning first.

```text
B1 / B1_PLUS / B2 direct source-artifact expansion: NOT_ALLOWED
B1 / B1_PLUS / B2 bulk implementation: NOT_ALLOWED
B1 / B1_PLUS / B2 candidate-only planning scan: ALLOWED
B1 / B1_PLUS / B2 source-evidence selection policy: ALLOWED
B1 / B1_PLUS / B2 implementation batch: requires a separate approved policy and cap
```

Reason:

```text
R6 intentionally closed only A1/A1_PLUS and A2/A2_PLUS expansion.
R6-M10 did not check full B1/B2 expansion readiness.
Candidate records are structurally usable but not accepted authority.
The project must remain small-batch and must not balloon into full A1-B2 implementation in one step.
```

## 8. Gate & Distance Update

```text
[PASS] R6 A1/A1_PLUS line closed.
[PASS] R6 A2/A2_PLUS line closed.
[PASS] validation report is PASS with fail_count=0.
[PASS] CI-safe pytest expectations are synced to 22 / 22.
[PASS] accepted / candidate boundary remains explicit.
[PASS] learner_state_write=false remains enforced.
[PASS] no learner-facing practice was generated.
[PASS] no B1 / B2 bulk expansion occurred.
[PASS] future B1 / B2 is restricted to candidate-only planning first.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 9. Closeout Decision

```text
R6_A1_A2_EXPANSION_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
R6_B1_B2_EXPANSION = NOT_STARTED
R6_B1_B2_NEXT_ALLOWED_MODE = CANDIDATE_ONLY_PLANNING
```

## 10. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M0 B1 / B2 candidate-only planning readiness scan
```

R7-M0 must not directly add B1 / B2 nodes or edges. It should only define the planning boundary, evidence requirements, batch caps, and promotion rules for future B1 / B2 candidate expansion.
