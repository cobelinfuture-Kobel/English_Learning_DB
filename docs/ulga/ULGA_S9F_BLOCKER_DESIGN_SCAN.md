# ULGA-S9F Blocker Design Scan

## 1. Scope

This document performs a full root cause analysis for the current failures in:

```text
tests/ulga/test_learner_state_builder_qa_audit.py
```

This is design scan only.

Not performed:

- no builder fix
- no guardrail fix
- no audit fix
- no schema fix
- no pytest expectation change
- no PASS threshold change
- no blocker count change
- no attempt to make tests green

Allowed output:

- `docs/ulga/ULGA_S9F_BLOCKER_DESIGN_SCAN.md`

## 2. Inputs Reviewed

Tests reviewed:

- `tests/ulga/test_learner_state_builder.py`
- `tests/ulga/test_learner_state_guardrails.py`
- `tests/ulga/test_learner_state_stability_audit.py`
- `tests/ulga/test_learner_state_builder_qa_audit.py`

Learner-state artifacts reviewed:

- `ulga/learner_state/learner_state.json`
- `ulga/learner_state/sample_evidence_events.json`

Reports reviewed:

- `ulga/reports/learner_state_builder_summary.json`
- `ulga/reports/learner_state_guardrail_summary.json`
- `ulga/reports/learner_state_builder_qa_audit.json`

Implementation/audit code reviewed for RCA context:

- `ulga/builders/build_learner_state.py`
- `ulga/audits/audit_learner_state_builder.py`

Related S9 documents reviewed:

- `docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9F_LEARNER_STATE_BUILDER_QA_AUDIT.md`
- `docs/ulga/ULGA_S9G_LEARNER_STATE_BUILDER_GUARDRAIL_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9I_LEARNER_STATE_GUARDRAIL_QA_AUDIT.md`
- `docs/ulga/ULGA_S9J_LEARNER_STATE_STABILITY_AUDIT.md`
- `docs/ulga/ULGA_S9L_POST_TIGHTENING_READINESS_AUDIT.md`

## 3. Current Audit State

Current failing expectation:

```text
Expected: PASS_WITH_WARNINGS
Actual: BLOCKER
Blockers: 4
```

Current `ulga/reports/learner_state_builder_qa_audit.json` status:

```json
{
  "contract_version": "ULGA-S9F",
  "status": "BLOCKER",
  "warnings": [
    "WARN_DECAY_NOT_MODELED: decay_adjusted_score equals mastery_score for all S9E V1 records; true retention decay is not modeled yet",
    "WARN_EMPTY_LOG_LIMITATION: S9C collection is non-empty, so zero-event global cold start is not naturally supported"
  ],
  "blockers": [
    "record without last_success_at emitted review_due_at outside allowed policy: learner:cyndi dialogue:DIALOGUE_ORDERING_FOOD_A1_001",
    "record without last_success_at emitted review_due_at outside allowed policy: learner:cyndi vocabulary:VOCAB_NODE_004210",
    "record without last_success_at emitted review_due_at outside allowed policy: learner:james morphology:word_family_read",
    "record without last_success_at emitted review_due_at outside allowed policy: learner:james skill:writing_revision"
  ]
}
```

Important observation:

- `review_due_findings` reports `PASS` for all 9 records.
- There is no `review_due_at mismatch`.
- The 4 blockers are emitted by an additional invariant in `audit_review_due`: if `last_success_at is None`, `review_due_at is not None`, and `mastery_band != "seen"`, append a blocker.

The audit therefore contradicts itself:

```text
expected_review_due_at == actual_review_due_at
but
extra last_success_at rule marks the same record as BLOCKER
```

## 4. Blocker Inventory

### Blocker 1

```text
record without last_success_at emitted review_due_at outside allowed policy:
learner:cyndi dialogue:DIALOGUE_ORDERING_FOOD_A1_001
```

Record facts:

- `node_type`: `dialogue`
- `mastery_score`: `0.49`
- `mastery_band`: `practicing`
- `exposure_count`: `1`
- `correct_count`: `0`
- `last_success_at`: `null`
- `last_seen_at`: `2026-06-17T09:15:10Z`
- `review_due_at`: `2026-06-20T09:15:10Z`
- strongest role: `supporting_context`

Classification:

```text
False Positive Audit
Audit Logic
```

Truth judgment:

```text
False Blocker
```

### Blocker 2

```text
record without last_success_at emitted review_due_at outside allowed policy:
learner:cyndi vocabulary:VOCAB_NODE_004210
```

Record facts:

- `node_type`: `vocabulary`
- `mastery_score`: `0.49`
- `mastery_band`: `practicing`
- `exposure_count`: `1`
- `correct_count`: `0`
- `last_success_at`: `null`
- `last_seen_at`: `2026-06-17T09:15:10Z`
- `review_due_at`: `2026-06-20T09:15:10Z`
- strongest role: `prerequisite`

Classification:

```text
False Positive Audit
Audit Logic
```

Truth judgment:

```text
False Blocker
```

### Blocker 3

```text
record without last_success_at emitted review_due_at outside allowed policy:
learner:james morphology:word_family_read
```

Record facts:

- `node_type`: `morphology`
- `mastery_score`: `0.49`
- `mastery_band`: `practicing`
- `exposure_count`: `1`
- `correct_count`: `0`
- `last_success_at`: `null`
- `last_seen_at`: `2026-06-17T11:00:00Z`
- `review_due_at`: `2026-06-20T11:00:00Z`
- strongest role: `diagnostic_signal`

Classification:

```text
False Positive Audit
Audit Logic
```

Truth judgment:

```text
False Blocker
```

### Blocker 4

```text
record without last_success_at emitted review_due_at outside allowed policy:
learner:james skill:writing_revision
```

Record facts:

- `node_type`: `skill`
- `mastery_score`: `0.49`
- `mastery_band`: `practicing`
- `exposure_count`: `1`
- `correct_count`: `0`
- `last_success_at`: `null`
- `last_seen_at`: `2026-06-17T11:00:00Z`
- `review_due_at`: `2026-06-20T11:00:00Z`
- strongest role: `supporting_context`

Classification:

```text
False Positive Audit
Audit Logic
```

Truth judgment:

```text
False Blocker
```

## 5. Root Cause Analysis

### Shared root cause

The 4 blockers share one root cause:

```text
S9F audit contains a stale extra invariant that treats practicing records without last_success_at as illegal when review_due_at is present.
```

This invariant is stale because current builder and audit expected-review logic both explicitly allow `practicing` records to anchor review scheduling on `last_seen_at` when `last_success_at` is unavailable.

Relevant behavior:

- `ulga/builders/build_learner_state.py` computes `practicing` review due with `last_success_at or last_seen_at`.
- `ulga/audits/audit_learner_state_builder.py` computes expected `practicing` review due with the same `last_success_at or last_seen_at`.
- The same audit then separately declares these records blockers because `last_success_at` is missing.

This is not a data mismatch.

Evidence:

```text
review_due_findings status: PASS for all 9 records
```

The blocker condition is therefore not checking consistency with computed review policy. It is checking an older or narrower policy assumption:

```text
Only seen records may have review_due_at without last_success_at.
```

That assumption no longer matches current S9A/S9G direction.

### Why current output changed from S9F expectations

The original `ULGA_S9F_LEARNER_STATE_BUILDER_QA_AUDIT.md` was written before S9H/S9K guardrail tightening.

Original S9F expected:

- `PASS_WITH_WARNINGS`
- 18 warnings
- 0 blockers
- role-risk warnings present
- ratio-risk warnings present

Current guarded output:

- guardrails lower low-authority high-band records to `seen` or `practicing`
- role-risk warnings no longer trigger because the audit only warns on `functional`, `mastered`, or `automatic` for low-authority roles
- ratio-risk warnings no longer trigger because the audit threshold is `mastery_score >= 0.50`, while several guarded records are now `0.49`
- the remaining issue is not overstatement into high bands, but stale audit treatment of review due scheduling

So two things are true at the same time:

1. The old S9F tests are stale relative to the post-guardrail system.
2. The 4 blockers are false positives caused by contradictory audit logic.

### Blocker 1 Root Cause

`dialogue:DIALOGUE_ORDERING_FOOD_A1_001` was lowered by guardrails from pre-S9K `functional` risk to `practicing`.

Root cause:

```text
Audit invariant does not allow a practicing dialogue record to schedule review from last_seen_at when last_success_at is null.
```

Why this is not a true data blocker:

- `review_due_at` matches the audit's own expected value.
- S9L confirms S9K removed the single-event non-primary dialogue `functional+` risk.
- The remaining record is a weak/practicing exposure that should be reviewed soon, not ignored.

### Blocker 2 Root Cause

`vocabulary:VOCAB_NODE_004210` is a prerequisite-role vocabulary record from a dialogue event.

Root cause:

```text
Audit invariant treats non-success practicing prerequisite evidence as ineligible for review scheduling, even though current review policy uses last_seen_at fallback for practicing.
```

Why this is not a true data blocker:

- Vocabulary was not marked mastered or functional.
- Guardrails cap it at `0.49 practicing`.
- A review due date based on recent exposure is reasonable for weak prerequisite evidence.

### Blocker 3 Root Cause

`morphology:word_family_read` is a diagnostic-signal derived record from teacher input.

Root cause:

```text
Audit invariant treats diagnostic practicing records without last_success_at as illegal when scheduled for review, while S9G says diagnostic/review signals should shape remediation and review urgency more than mastery.
```

Why this is not a true data blocker:

- Morphology is capped at `0.49 practicing`.
- No high-band derived-node mastery remains.
- Review scheduling is consistent with a diagnostic signal needing follow-up.

### Blocker 4 Root Cause

`skill:writing_revision` is a supporting-context skill record from teacher input.

Root cause:

```text
Audit invariant treats supporting-context practicing records without success as illegal for review scheduling.
```

Why this is not a true data blocker:

- Skill is capped at `0.49 practicing`.
- It does not claim functional/mastered readiness.
- A near-term review date reflects weak evidence requiring follow-up.

## 6. Severity Matrix

| Blocker | Category | True/False | Learning Correctness Severity | CI/Process Severity | Final Severity |
|---|---|---|---|---|---|
| Blocker 1: dialogue no-success practicing review due | False Positive Audit | False | Low | Medium | Low |
| Blocker 2: vocabulary no-success practicing review due | False Positive Audit | False | Low | Medium | Low |
| Blocker 3: morphology no-success practicing review due | False Positive Audit | False | Low | Medium | Low |
| Blocker 4: skill no-success practicing review due | False Positive Audit | False | Low | Medium | Low |

Severity counts:

```text
Critical Count: 0
High Count: 0
Medium Count: 0
Low Count: 4
```

Rationale:

- They are not learner-state data corruption.
- They are not builder output mismatches.
- They are not schema violations.
- They are not duplicate/idempotency failures.
- They do break the S9F audit test suite and create process friction, but the blocker labels themselves are not product-truth blockers.

## 7. Impact on Ranking

### S10C Ranking

Impact of these 4 blockers:

```text
Low
```

Reason:

- S10C currently uses global ranking and only reads learner state as a weak global mastery-gap hook where matching focus-node state exists.
- These 4 blockers are about review scheduling of weak practicing records, not hard dependency truth or opportunity ranking order.
- The guarded scores are conservative: `0.49`, not inflated functional/mastered values.

Residual ranking risk not caused by these blockers:

- true decay is still missing
- learner-state sample remains tiny
- graph-aware aggregation is missing
- derived node state should remain weak evidence

Verdict for S10C:

```text
The 4 blockers should not invalidate S10C global ranking.
```

## 8. Impact on Planner

### S10D Planner

Impact of these 4 blockers:

```text
Low for global planner design
Medium for learner/session planner policy if misinterpreted as true learner-state failure
```

Reason:

- S10D already says learner/session modes must fail closed when required learner context is unavailable or unsafe.
- The 4 blockers do not show that `review_due_at` is inconsistent; they show that the audit has stale policy logic.
- Planner should still not rely on S9F audit blocker labels until S9F audit is aligned with post-guardrail behavior.

Broader planner risk remains real:

- S9J planner readiness was `57 / 100`.
- S9L planner readiness was `60 / 100`.
- S9L explicitly says planner implementation should remain blocked until decay and graph-aware aggregation are designed.

That broader risk is not the same as these 4 S9F blockers.

## 9. Impact on Learner Mode

### S10E Learner Mode

Impact of these 4 blockers:

```text
Medium
```

Reason:

- Learner mode will care about `review_due_at`, `mastery_band`, `decay_adjusted_score`, and evidence confidence.
- These false blockers could cause developer confusion by marking valid weak-review scheduling as illegal.
- However, the actual records are conservative and do not claim high mastery.

True learner-mode blockers that remain outside this 4-blocker set:

- true decay is not modeled
- graph-aware aggregation is missing
- data sparsity remains high
- productive vs recognition evidence is not separated
- zero-event cold-start remains unresolved

Conclusion:

```text
The 4 blockers are false positives, but S10E learner mode should still be gated separately by S9J/S9L readiness risks.
```

## 10. Repair Strategy

No repair is performed in this task.

Recommended repair groups:

### Repair Group A: Audit Fix

Goal:

- align `audit_learner_state_builder.py` review-due blocker logic with the current expected-review policy.

Candidate design:

- remove or revise the extra blocker condition:

```text
last_success_at is None and review_due_at is not None and mastery_band != seen
```

- replace it with policy-specific checks:

```text
seen may anchor on last_seen_at
practicing may anchor on last_success_at or last_seen_at
functional/mastered/automatic should require last_success_at if review_due_at is emitted
```

Expected result:

- these 4 false blockers disappear
- real `review_due_at` mismatches remain blockers

### Repair Group B: Test Expectation Refresh

Goal:

- update S9F audit tests to reflect post-S9H/S9K guarded output.

Do not do this by lowering thresholds blindly.

Required design:

- tests should no longer require role/ratio warnings that guardrails intentionally resolved
- tests should assert current stable facts:
  - review due findings match expected policy
  - no forbidden planner/ranking fields
  - no duplicate learner-node pairs
  - no duplicate idempotency keys
  - remaining warnings include decay and empty-log limitations

### Repair Group C: Builder Review Policy Clarification

Goal:

- document and, if needed, encode the intended review scheduling semantics.

Recommended policy:

- `seen`: review from `last_seen_at`
- `practicing`: review from `last_success_at` if present, otherwise `last_seen_at`
- `functional+`: review should normally require `last_success_at`; if absent, either emit `null` or downgrade the band

Current builder already follows the first two points.

### Repair Group D: Guardrail / Learner Mode Readiness

Goal:

- address real learner-mode risks separately from false S9F blockers.

Future work:

- true decay model
- graph-aware aggregation
- sparse evidence handling
- productive vs recognition evidence separation
- cold-start handling

These are real roadmap risks, but not the root cause of the current 4 blockers.

## 11. Recommended Repair Order

1. Audit Fix

   Fix the contradictory S9F review-due blocker rule first. It is the direct cause of the 4 blockers.

2. Test Expectation Refresh

   Refresh S9F QA tests to match post-guardrail behavior. Do not restore old warning expectations just to match obsolete S9F output.

3. Builder Review Policy Documentation

   Add explicit policy documentation around `last_seen_at` fallback for `practicing`.

4. Learner Mode Readiness Work

   Address true decay and graph-aware aggregation before enabling S10E learner/session modes.

## 12. Should S10E Be Blocked?

```text
NO
```

Reason:

- The 4 current S9F blockers are false-positive audit blockers, not true learner-state data blockers.
- They should not block a conservative `S10E_AntigravityPlanner_Implementation` if S10E remains scoped to global mode or explicitly excludes learner/session personalization.
- S10E learner mode must still be gated by separate readiness checks for decay, graph-aware aggregation, sparse learner data, and cold-start handling.

Operational interpretation:

```text
S10E global-mode implementation: not blocked by these 4 S9F blockers.
S10E learner/session mode: should remain blocked or fail-closed until the broader S9J/S9L risks are remediated.
```

## 13. Final Verdict

The current 4 blockers are not true builder/data/schema blockers.

They are stale audit-logic false positives caused by a contradiction inside S9F audit review-due policy:

```text
expected_review_due_at allows practicing fallback to last_seen_at
but blocker rule forbids review_due_at without last_success_at for practicing
```

Final status:

```text
S9F_BLOCKER_STATUS: MOSTLY_FALSE_POSITIVES
Critical Count: 0
High Count: 0
Medium Count: 0
Low Count: 4
```

Recommended next task:

```text
ULGA-S9F_Blocker_Remediation_Implementation
```
