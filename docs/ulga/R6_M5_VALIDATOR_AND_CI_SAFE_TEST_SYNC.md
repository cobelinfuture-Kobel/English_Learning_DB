# R6-M5 Validator and CI-safe Test Sync

## 1. Current State

```text
Epic ID:
R6_GrammarSkillTree_A1_B2_Expansion

Sub-task ID:
R6-M5 run validator and CI-safe test hook sync

Branch:
codex/r6-m2-a1-a1plus-node-batch

Status:
VALIDATOR_AND_CI_TEST_SYNCED_PENDING_CI
```

R6-M5 completes the R6-M2 through R6-M5 expansion sequence on PR #18 by syncing the validation report and CI-safe pytest expectations after the R6-M4 derived artifact rebuild.

## 2. Scope Lock

```text
Allowed:
- refresh ulga/reports/grammar_artifact_validation_report.json
- update tests/ci/test_static_grammar_artifacts.py expectations

Forbidden in R6-M5:
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no learner-facing practice generation
- no learner state write
```

## 3. Validation Report Sync

The refreshed validation report now reflects the R6 A1 / A1_PLUS expansion state:

```text
status = PASS
node_count = 16
edge_count = 16
order_row_count = 16
coverage_node_count = 16
query_node_count = 16
check_count = 22
fail_count = 0
```

## 4. CI-safe Test Sync

`tests/ci/test_static_grammar_artifacts.py` now uses:

```text
EXPECTED_NODE_COUNT = 16
EXPECTED_EDGE_COUNT = 16
```

and asserts:

```text
report.status = PASS
report.summary.fail_count = 0
report.summary.node_count = 16
report.summary.edge_count = 16
report.summary.order_row_count = 16
report.summary.coverage_node_count = 16
report.summary.query_node_count = 16
learner_facing_practice = false
learner_state_write = false
```

## 5. Full Sequence Covered By PR #18

```text
R6-M2: add 10 A1 / A1_PLUS candidate grammar nodes
R6-M3: add 11 matching candidate grammar edges
R6-M4: rebuild order / coverage / query derived artifacts
R6-M5: refresh validation report and CI-safe pytest expectations
```

## 6. Gate & Distance Update

```text
[PASS] Validation report refreshed to 16 nodes / 16 edges.
[PASS] CI-safe test expectations updated to 16 nodes / 16 edges.
[PASS] Validator surfaces still include edge refs, ordering, coverage, query, and learner_state_write checks.
[PASS] No learner-facing practice artifact created.
[PASS] No learner state write path added.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 7. Next Shortest Step

```text
NEXT_SHORT_STEP:
Run GitHub Actions CI for PR #18.

If CI success:
mark PR #18 ready and merge.

If CI failure:
stop and patch only the failing validation / CI surface.
```
