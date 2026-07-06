# R7-M14 B1_PLUS Mode-B Candidate Surface Planning Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M14 B1_PLUS Mode-B candidate surface planning scan

Branch:
codex/r7-m14-b1p-surface

Status:
PLANNING_SCAN_ONLY
```

R7-M14 proposes a capped B1_PLUS candidate surface under the R7-M13 Mode-B staging policy.

## 2. Prior Gate

```text
R7-M13 selected:
B1_PLUS_STAGING_POLICY = MODE_B_BRIDGE_FROM_B1_TO_B2_PREVIEW
```

Mode-B means B1_PLUS extends stable B1 control toward B2-like complexity without treating preview as B2 mastery.

## 3. Scope Lock

Allowed in R7-M14:

```text
- propose a capped B1_PLUS candidate surface
- identify dependency anchors from the closed B1 graph
- assign evidence-search intent
- keep all proposed records planning-only
```

Forbidden in R7-M14:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Proposed B1_PLUS Candidate Surface

These are proposed planning rows only. They are not implemented in `grammar_nodes.json`.

| Proposed grammar_id | Bridge family | B1 anchor | B2-preview direction | Evidence search intent | Planning status |
|---|---|---|---|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_B1PLUS` | reported speech | `GRAMMAR_REPORTED_SPEECH_BASIC` | reported questions and embedded question order | search EGP reported speech rows for question/reporting expansion | PLANNING_ONLY |
| `GRAMMAR_REPORTED_COMMANDS_REQUESTS_B1PLUS` | reported speech | `GRAMMAR_REPORTED_SPEECH_BASIC` | reporting commands and requests | search EGP reported speech rows for commands/requests | PLANNING_ONLY |
| `GRAMMAR_CONDITIONAL_MIXED_CONTROL_B1PLUS` | conditional | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | conditional contrast and controlled clause variation | search EGP conditional rows beyond basic first/second conditional | PLANNING_ONLY |
| `GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS` | conditional | `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B2-oriented third conditional preview without mastery claim | search EGP conditional rows for third conditional evidence | PLANNING_ONLY |
| `GRAMMAR_PASSIVE_AGENT_BY_PHRASE_B1PLUS` | passive | `GRAMMAR_PASSIVE_PRESENT_PAST_EXPANDED_SUBJECTS_B1` | passive with agent, reason, or context expansion | search EGP passive rows beyond simple present/past affirmative | PLANNING_ONLY |
| `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | relative clause | `GRAMMAR_RELATIVE_CLAUSES_PLACE_TIME_OBJECT_B1` | non-defining or more complex relative-clause preview | search EGP relative-clause rows beyond defining basics | PLANNING_ONLY |
| `GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS` | modality | `GRAMMAR_MODAL_DEDUCTION_BASIC` | may/might/could for certainty and possibility contrast | search EGP modality rows for certainty/possibility nuance | PLANNING_ONLY |
| `GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS` | perfect aspect | `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` and `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | perfect simple vs continuous contrast and discourse use | search EGP present perfect rows for contrast/extended use | PLANNING_ONLY |
```

## 5. Candidate Count

```text
proposed_b1plus_candidates = 8
implementation_cap_status = WITHIN_CAP
```

This stays below the earlier B1/B1_PLUS candidate planning cap of 5-10 proposals.

## 6. Implementation Readiness

```text
R7-M14_IMPLEMENTATION_READINESS = NOT_READY_SOURCE_REF_VERIFICATION_REQUIRED
```

Reason:

```text
The surface is defined, but concrete EGP source_ref rows are not verified yet. Candidate-node implementation remains blocked.
```

## 7. Required Next Verification

A later task must verify, for each proposed row:

```text
[ ] concrete source_ref exists
[ ] source_role is authority_source or normalized_authority_artifact
[ ] evidence level supports B1_PLUS bridge policy
[ ] B1 anchor dependency is valid
[ ] preview does not claim B2 mastery
[ ] authority_status remains candidate
[ ] confidence remains operator_review_required
[ ] generated_content = false
[ ] learner_state_write = false
```

## 8. Gate & Distance Update

```text
[PASS] R7-M14 remains planning-only.
[PASS] Mode-B policy is applied.
[PASS] 8 B1_PLUS candidate planning rows proposed.
[PASS] All rows have a B1 anchor.
[PASS] No grammar source artifact modified.
[PASS] No derived artifact rebuilt.
[PASS] No CI expectation changed.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] B1_PLUS implementation requires concrete source_ref verification.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M15 B1_PLUS Mode-B concrete source-ref verification scan
```

R7-M15 must remain evidence-verification only. It may map R7-M14 rows to concrete source_ref candidates, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.
