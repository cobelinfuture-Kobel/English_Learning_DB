# R7-M1 B1 / B1_PLUS Candidate Planning Surface Definition

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M1 B1 / B1_PLUS candidate planning surface definition

Branch:
codex/r7-m1-b1-b1plus-candidate-surface

Status:
PLANNING_SURFACE_ONLY
```

R7-M1 defines a small B1 / B1_PLUS candidate planning surface. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M0

R7-M0 locked the B1 / B1_PLUS / B2 line to candidate-only planning first.

```text
B1 / B1_PLUS / B2 direct source-artifact expansion: NOT_ALLOWED
B1 / B1_PLUS / B2 bulk implementation: NOT_ALLOWED
B1 / B1_PLUS / B2 candidate-only planning scan: ALLOWED
B1 / B1_PLUS / B2 source-evidence selection policy: ALLOWED
B1 / B1_PLUS / B2 implementation batch: requires separate approved policy and cap
```

R7-M1 therefore remains a planning-only document.

## 3. Scope Lock

Allowed in R7-M1:

```text
- propose a small B1 / B1_PLUS candidate planning surface
- list proposed node IDs and labels
- classify each proposal by category and tentative stage
- list dependency hypotheses for future edge planning
- record source-evidence requirements
- produce a resumable next task
```

Forbidden in R7-M1:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Current Baseline To Protect

Current static grammar artifact baseline remains unchanged:

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

Current authority split remains unchanged:

```text
accepted = 5
candidate = 17
```

## 5. B1 Candidate Planning Surface

R7-M1 proposes 6 B1 candidate planning items. These are proposals only; they are not written to `grammar_nodes.json`.

| Proposed grammar_id | Label | Category | Tentative stage | Planning status |
|---|---|---|---|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | present perfect for experience | `perfect_aspect` | B1 | planning_candidate_only |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | present perfect for recent result | `perfect_aspect` | B1 | planning_candidate_only |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | past continuous basic statements | `past_simple` | B1 | planning_candidate_only |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | first conditional basic clauses | `conditional` | B1 | planning_candidate_only |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | basic defining relative clauses | `relative_clause` | B1 | planning_candidate_only |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | basic present / past passive | `passive` | B1 | planning_candidate_only |

## 6. B1_PLUS Candidate Planning Surface

R7-M1 proposes 4 B1_PLUS candidate planning items. These are proposals only; they are not written to `grammar_nodes.json`.

| Proposed grammar_id | Label | Category | Tentative stage | Planning status |
|---|---|---|---|---|
| `GRAMMAR_REPORTED_SPEECH_BASIC` | basic reported speech | `reported_speech` | B1_PLUS | planning_candidate_only |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | second conditional basic clauses | `conditional` | B1_PLUS | planning_candidate_only |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | basic modal deduction | `modal` | B1_PLUS | planning_candidate_only |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | present perfect continuous basic use | `perfect_aspect` | B1_PLUS | planning_candidate_only |

## 7. Candidate Count Check

```text
B1 proposed nodes = 6
B1_PLUS proposed nodes = 4
Total proposed planning surface = 10
```

This stays inside the R7-M0 planning cap:

```text
B1 candidate planning surface: 5 to 10 proposed nodes
B1_PLUS candidate planning surface: 5 to 10 proposed nodes
```

B1_PLUS has 4 proposals in this scan because R7-M1 intentionally keeps the first B1_PLUS surface conservative. A later R7-M1A extension may add one or two more B1_PLUS proposals if source-evidence review confirms priority.

## 8. Dependency Hypotheses For Future Edge Planning

These are planning hypotheses only. They are not `grammar_edges.json` records.

```text
GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC
  likely requires: GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC, GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS

GRAMMAR_PRESENT_PERFECT_RESULT_BASIC
  likely requires: GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC

GRAMMAR_PAST_CONTINUOUS_BASIC
  likely requires: GRAMMAR_PAST_SIMPLE_REGULAR, GRAMMAR_BE_VERB_BASIC

GRAMMAR_FIRST_CONDITIONAL_BASIC
  likely requires: GRAMMAR_FUTURE_GOING_TO_BASIC, GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS

GRAMMAR_RELATIVE_CLAUSES_BASIC
  likely requires: GRAMMAR_WH_QUESTIONS_BE_DO_BASIC

GRAMMAR_PASSIVE_PRESENT_PAST_BASIC
  likely requires: GRAMMAR_BE_VERB_BASIC, GRAMMAR_PAST_SIMPLE_REGULAR

GRAMMAR_REPORTED_SPEECH_BASIC
  likely requires: GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC, GRAMMAR_WH_QUESTIONS_BE_DO_BASIC

GRAMMAR_SECOND_CONDITIONAL_BASIC
  likely requires: GRAMMAR_PAST_SIMPLE_IRREGULAR_BASIC, GRAMMAR_FIRST_CONDITIONAL_BASIC

GRAMMAR_MODAL_DEDUCTION_BASIC
  likely requires: GRAMMAR_CAN_STATEMENT, GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC

GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC
  likely requires: GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC, GRAMMAR_PRESENT_CONTINUOUS_BASIC
```

## 9. Evidence Requirements Before Implementation

Before any proposed item can be written to `grammar_nodes.json`, a later task must attach source evidence.

Minimum evidence required:

```text
- authority_source or normalized_authority_artifact pointer
- CEFR / EGP level evidence or equivalent normalized authority evidence
- non-empty source_ref
- allowed_use including grammar_construct_reference and stage_reference
- blocked_use including learner_state_write and automatic_promotion
- confidence = operator_review_required unless evidence is normalized and reviewed
```

## 10. Promotion Boundary

These proposals must not be treated as accepted authority.

```text
planning_candidate_only -> allowed
candidate source-artifact implementation -> requires later approved batch
accepted authority promotion -> requires separate promotion audit
learner-facing practice use -> not allowed from this task
```

## 11. Risk Register

```text
RISK-1: B1 breadth expansion
Status: OPEN
Impact: Medium / High
Control: R7-M1 caps the first planning surface to 10 proposals.

RISK-2: B1_PLUS undercoverage
Status: OPEN
Impact: Low / Medium
Control: B1_PLUS is intentionally conservative; a later evidence-backed extension can add more planning proposals.

RISK-3: Evidence ambiguity
Status: OPEN
Impact: Medium
Control: source-evidence selection must occur before implementation.

RISK-4: premature source-artifact implementation
Status: OPEN
Impact: High
Control: this task forbids grammar_nodes.json and grammar_edges.json modifications.
```

## 12. Gate & Distance Update

```text
[PASS] R7-M1 remains planning-only.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[PASS] B1 / B1_PLUS planning surface is capped and conservative.
[PASS] Future implementation is blocked until source-evidence selection and approved batch policy.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 13. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M2 B1 / B1_PLUS source-evidence selection policy
```

R7-M2 must remain policy-only. It should define which sources can support the proposed B1 / B1_PLUS planning surface before any source-artifact implementation is allowed.
