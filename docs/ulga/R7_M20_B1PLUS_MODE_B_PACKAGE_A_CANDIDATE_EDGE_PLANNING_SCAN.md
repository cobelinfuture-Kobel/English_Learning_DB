# R7-M20 B1_PLUS Mode-B Package-A Candidate-edge Planning Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M20 B1_PLUS Mode-B Package-A candidate-edge planning scan

Branch:
codex/r7-m20-edges-plan

Status:
EDGE_PLANNING_SCAN_ONLY
```

R7-M20 proposes candidate edges for the 7 B1_PLUS Package-A candidate nodes added by R7-M19. This task does not modify `grammar_edges.json`, `grammar_nodes.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M19

```text
node_count = 39
edge_count = 40
added_B1_PLUS_candidate_nodes = 7
deferred_by_package_a = GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS
```

## 3. Scope Lock

Allowed in R7-M20:

```text
- propose candidate edge records for the 7 B1_PLUS nodes
- assign future edge IDs
- identify prerequisite / ordering rationale
- keep all edges planning-only
- produce implementation approval handoff
```

Forbidden in R7-M20:

```text
- no grammar_edges.json modification
- no grammar_nodes.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Proposed Future Candidate Edges

These are proposed edge records only. They are not written to `grammar_edges.json` in R7-M20.

| Future edge_id | Source | Relation | Target | Rationale |
|---|---|---|---|---|
| `GEDGE_000041` | `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | REQUIRES | `GRAMMAR_REPORTED_SPEECH_BASIC` | reported questions/requests should build from basic reported speech |
| `GEDGE_000042` | `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | REQUIRES | `GRAMMAR_WH_QUESTIONS_BE_DO_BASIC` | indirect questions reuse WH-question form awareness |
| `GEDGE_000043` | `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | REQUIRES | `GRAMMAR_MODAL_DEDUCTION_BASIC` | past deduction extends basic modal deduction |
| `GEDGE_000044` | `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_UNIQUE_EXPERIENCE_B1` | past modal deduction uses perfect-form awareness |
| `GEDGE_000045` | `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | REQUIRES | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | modal passive should follow core passive control |
| `GEDGE_000046` | `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | REQUIRES | `GRAMMAR_CAN_STATEMENT` | modal passive combines modal form with passive form |
| `GEDGE_000047` | `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | REQUIRES | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | non-defining preview extends B1 relative clause base |
| `GEDGE_000048` | `GRAMMAR_CONDITIONALS_UNLESS_AS_LONG_AS_B1PLUS` | REQUIRES | `GRAMMAR_FIRST_CONDITIONAL_BASIC` | advanced conditional linkers should follow first conditional control |
| `GEDGE_000049` | `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | aspect contrast requires present perfect continuous base |
| `GEDGE_000050` | `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | REQUIRES | `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | contrast also requires present perfect simple/result use |
| `GEDGE_000051` | `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | REQUIRES | `GRAMMAR_FUTURE_GOING_TO_BASIC` | future continuous preview follows future-reference base |
| `GEDGE_000052` | `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | REQUIRES | `GRAMMAR_PRESENT_CONTINUOUS_BASIC` | continuous-form awareness supports future continuous form |

## 5. Proposed Edge Count

```text
existing_edge_count = 40
proposed_new_edges = 12
future_edge_count_after_implementation = 52
```

## 6. Implementation Boundary

```text
R7-M20_IMPLEMENTATION_DECISION = NOT_STARTED_OPERATOR_APPROVAL_REQUIRED
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
- add only the 12 planned B1_PLUS Package-A candidate edges unless explicitly narrowed
- preserve existing 40 edges
- rebuild or sync derived artifacts after edge implementation
- update validation report and CI-safe expected edge count
- avoid learner-facing practice and learner state writes
```

## 8. Gate & Distance Update

```text
[PASS] R7-M20 remains edge-planning only.
[PASS] 12 proposed B1_PLUS Package-A candidate edges defined.
[PASS] Future edge count is projected as 52.
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

Because the next logical task crosses from edge planning into source-artifact edge implementation, automatic progression must stop after R7-M20 merge unless the operator explicitly approves edge implementation.

```text
NEXT_SHORT_STEP:
R7-M21 B1_PLUS Mode-B Package-A candidate-edge implementation batch

REQUIRED_OPERATOR_APPROVAL:
Approve R7-M21 as a candidate-edge implementation batch that may modify grammar_edges.json and sync derived artifacts / validation / CI expectations.
```
