# R7-M9 Corrected B1 Candidate-edge Planning Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M9 corrected B1 candidate-edge planning scan

Branch:
codex/r7-m9-b1-planning-scan

Status:
EDGE_PLANNING_SCAN_ONLY
```

R7-M9 proposes matching candidate-edge relationships for the 10 R7-M8 corrected B1 candidate nodes. This task does not modify `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M8

R7-M8 added 10 corrected B1 candidate nodes and synced static artifacts to:

```text
node_count = 32
edge_count = 22
order_row_count = 32
coverage_node_count = 32
query_node_count = 32
```

R7-M8 explicitly did not modify `grammar_edges.json`.

## 3. Scope Lock

Allowed in R7-M9:

```text
- propose B1 candidate edges
- assign future edge IDs
- identify prerequisite / ordering rationale
- keep all edges planning-only
- produce implementation approval handoff
```

Forbidden in R7-M9:

```text
- no grammar_edges.json modification
- no grammar_nodes.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B1_PLUS or B2 implementation
```

## 4. Proposed Future Candidate Edges

These are proposed edge records only. They are not written to `grammar_edges.json` in R7-M9.

| Future edge_id | Source | Relation | Target | Rationale |
|---|---|---|---|---|
| `GEDGE_000023` | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | REQUIRES | `GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC` | experience use requires core past participle / past-form awareness |
| `GEDGE_000024` | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | REQUIRES | `GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS` | present perfect statements build on basic declarative clause control |
| `GEDGE_000025` | `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | result use should follow a first B1 present-perfect candidate anchor |
| `GEDGE_000026` | `GRAMMAR_PAST_CONTINUOUS_REASON_REPEATED_B1` | REQUIRES | `GRAMMAR_BE_VERB_BASIC` | past continuous form requires be-verb auxiliary control |
| `GEDGE_000027` | `GRAMMAR_PAST_CONTINUOUS_REASON_REPEATED_B1` | REQUIRES | `GRAMMAR_PAST_SIMPLE_REGULAR` | B1 background past use depends on basic completed-past contrast |
| `GEDGE_000028` | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | REQUIRES | `GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS` | first conditional if-clause uses present simple form control |
| `GEDGE_000029` | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | REQUIRES | `GRAMMAR_FUTURE_GOING_TO_BASIC` | future outcome meaning requires prior future-reference surface |
| `GEDGE_000030` | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | REQUIRES | `GRAMMAR_WH_QUESTIONS_BE_DO_BASIC` | relative clause forms reuse who / where / when / that reference awareness |
| `GEDGE_000031` | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | REQUIRES | `GRAMMAR_REGULAR_PLURAL_NOUNS` | noun-phrase reference and head-noun control are required |
| `GEDGE_000032` | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | REQUIRES | `GRAMMAR_BE_VERB_BASIC` | passive form requires be-verb auxiliary control |
| `GEDGE_000033` | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | REQUIRES | `GRAMMAR_PAST_SIMPLE_REGULAR` | past passive requires completed-past verb-form awareness |
| `GEDGE_000034` | `GRAMMAR_REPORTED_SPEECH_BASIC` | REQUIRES | `GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC` | reported statements require tense-shift awareness |
| `GEDGE_000035` | `GRAMMAR_REPORTED_SPEECH_BASIC` | REQUIRES | `GRAMMAR_WH_QUESTIONS_BE_DO_BASIC` | reporting requires basic clause and reference handling |
| `GEDGE_000036` | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | REQUIRES | `GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC` | second conditional uses past simple in imagined clauses |
| `GEDGE_000037` | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | REQUIRES | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | second conditional should follow first conditional conceptually |
| `GEDGE_000038` | `GRAMMAR_MODAL_DEDUCTION_BASIC` | REQUIRES | `GRAMMAR_CAN_STATEMENT` | modal deduction builds on basic modal form awareness |
| `GEDGE_000039` | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | REQUIRES | `GRAMMAR_PRESENT_CONTINUOUS_BASIC` | continuous aspect requires prior continuous-form control |
| `GEDGE_000040` | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | perfect continuous should follow a B1 present-perfect anchor |

## 5. Proposed Edge Count

```text
existing_edge_count = 22
proposed_new_edges = 18
future_edge_count_after_implementation = 40
```

This stays within the R7 planning cap because the proposed edge count is below 20.

## 6. Implementation Boundary

```text
R7-M9_IMPLEMENTATION_DECISION = NOT_STARTED_OPERATOR_APPROVAL_REQUIRED
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

## 7. Future Implementation Guardrails

If approved, the future edge implementation task must:

```text
- add only the 18 planned B1 candidate edges unless explicitly narrowed
- keep all edge records candidate-only / operator-review-required where the schema permits
- preserve existing 22 edges
- rebuild derived artifacts after edge implementation
- update validation report and CI-safe expected edge count
- avoid learner-facing practice and learner state writes
```

## 8. Gate & Distance Update

```text
[PASS] R7-M9 remains edge-planning only.
[PASS] 18 proposed B1 candidate edges defined.
[PASS] Future edge count is projected as 40.
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

## 9. Stop / Resume Handoff

Because the next logical task crosses from edge planning into source-artifact edge implementation, automatic progression must stop after R7-M9 merge unless the operator explicitly approves edge implementation.

```text
NEXT_SHORT_STEP:
R7-M10 corrected B1 candidate-edge implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M10 as a candidate-edge implementation batch that may modify grammar_edges.json and sync derived artifacts / validation / CI expectations.
```
