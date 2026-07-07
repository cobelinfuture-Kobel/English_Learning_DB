# R7-M30 B2 Package-A Candidate-edge Planning Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M30 B2 Package-A candidate-edge planning scan

Branch:
codex/r7m30-edge-plan

Status:
EDGE_PLANNING_SCAN_ONLY
```

R7-M30 proposes candidate edges for the 7 B2 Package-A candidate nodes added by R7-M29. This task does not modify `grammar_edges.json`, `grammar_nodes.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M29

```text
node_count = 46
edge_count = 52
added_B2_candidate_nodes = 7
deferred_by_package_a = GRAMMAR_MIXED_CONDITIONALS_B2
```

## 3. Scope Lock

Allowed in R7-M30:

```text
- propose future candidate edge records for the 7 B2 Package-A nodes
- assign future edge IDs
- identify prerequisite / ordering rationale
- keep all edges planning-only
- produce implementation approval handoff
```

Forbidden in R7-M30:

```text
- no grammar_edges.json modification
- no grammar_nodes.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
```

## 4. Proposed Future Candidate Edges

These are proposed edge records only. They are not written to `grammar_edges.json` in R7-M30.

| Future edge_id | Source | Relation | Target | Rationale |
|---|---|---|---|---|
| `GEDGE_000053` | `GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2` | REQUIRES | `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | passive reporting should follow B1_PLUS passive extension control |
| `GEDGE_000054` | `GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2` | REQUIRES | `GRAMMAR_REPORTED_SPEECH_BASIC` | reporting passive combines passive and reported-speech concepts |
| `GEDGE_000055` | `GRAMMAR_ADVANCED_MODAL_SPECULATION_B2` | REQUIRES | `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | advanced speculation extends B1_PLUS past modal deduction |
| `GEDGE_000056` | `GRAMMAR_ADVANCED_MODAL_SPECULATION_B2` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | modal perfect / aspect speculation needs perfect-continuous awareness |
| `GEDGE_000057` | `GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2` | REQUIRES | `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | B2 preposition / whose control extends B1_PLUS relative-clause preview |
| `GEDGE_000058` | `GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2` | REQUIRES | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | B1 relative-clause control remains the base prerequisite |
| `GEDGE_000059` | `GRAMMAR_FUTURE_PERFECT_B2` | REQUIRES | `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | future perfect follows the B1_PLUS future-form expansion line |
| `GEDGE_000060` | `GRAMMAR_FUTURE_PERFECT_B2` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | future perfect requires completed-result / perfect-form awareness |
| `GEDGE_000061` | `GRAMMAR_REPORTED_SPEECH_ADVANCED_B2` | REQUIRES | `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | advanced reported speech extends B1_PLUS reported question/request control |
| `GEDGE_000062` | `GRAMMAR_REPORTED_SPEECH_ADVANCED_B2` | REQUIRES | `GRAMMAR_REPORTED_SPEECH_BASIC` | B1 reported speech remains the base prerequisite |
| `GEDGE_000063` | `GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | B2 advanced aspect contrast extends the B1_PLUS contrast node |
| `GEDGE_000064` | `GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | perfect-continuous base remains required |
| `GEDGE_000065` | `GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2` | REQUIRES | `GRAMMAR_WH_QUESTIONS_BE_DO_BASIC` | inversion relies on auxiliary / subject order awareness |
| `GEDGE_000066` | `GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2` | REQUIRES | `GRAMMAR_ADVERBS_OF_FREQUENCY_BASIC` | negative adverbial placement builds from adverbial-position awareness |

## 5. Proposed Edge Count

```text
existing_edge_count = 52
proposed_new_edges = 14
future_edge_count_after_implementation = 66
```

## 6. Deferred Item Confirmation

```text
GRAMMAR_MIXED_CONDITIONALS_B2 = DEFERRED_BY_PACKAGE_A
```

No future edge is proposed for the deferred item in R7-M30.

## 7. Implementation Boundary

```text
R7-M30_IMPLEMENTATION_DECISION = NOT_STARTED_OPERATOR_APPROVAL_REQUIRED
```

A later implementation task may modify `grammar_edges.json` only after explicit operator approval.

Still forbidden in this scan:

```text
- no grammar_edges.json write
- no derived rebuild
- no validation report update
- no accepted authority promotion
- no learner-facing generation
- no learner state write
```

## 8. Future Implementation Guardrails

If approved, the future edge implementation task must:

```text
- add only the 14 planned B2 Package-A candidate edges unless explicitly narrowed
- preserve existing 52 edges
- rebuild or sync derived artifacts after edge implementation
- update validation report and CI-safe expected edge count
- avoid learner-facing practice and learner state writes
```

## 9. Gate & Distance Update

```text
[PASS] R7-M30 remains edge-planning only.
[PASS] 14 proposed B2 Package-A candidate edges defined.
[PASS] Future edge count is projected as 66.
[PASS] No grammar_edges.json changes.
[PASS] No grammar_nodes.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 10. Stop / Resume Handoff

Because the next logical task crosses from edge planning into source-artifact edge implementation, automatic progression must stop after R7-M30 merge unless the operator explicitly approves edge implementation.

```text
NEXT_SHORT_STEP:
R7-M31 B2 Package-A candidate-edge implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M31 as a candidate-edge implementation batch that may modify grammar_edges.json and sync derived artifacts / validation / CI expectations.
```
