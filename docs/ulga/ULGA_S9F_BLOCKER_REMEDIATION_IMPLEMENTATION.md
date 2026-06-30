# ULGA-S9F Blocker Remediation Implementation

## 1. Scope

Implemented the S9F blocker remediation identified in:

- `docs/ulga/ULGA_S9F_BLOCKER_DESIGN_SCAN.md`

The remediation aligns `audit_learner_state_builder.py` review-anchor validation with the audit's own expected-review policy and the current builder policy.

This task did not modify:

- `ulga/learner_state/learner_state.json`
- `ulga/builders/*`
- `ulga/graph/*`
- `ulga/schema/*`

## 2. Root Cause

The S9F audit had contradictory review-due logic.

Expected-review policy allowed:

```text
mastery_band = practicing
review anchor = last_success_at or last_seen_at
```

But the blocker rule rejected:

```text
last_success_at is null
review_due_at exists
mastery_band != seen
```

That incorrectly marked valid `practicing` records with `last_seen_at` anchors as blockers.

## 3. Files Modified

- `ulga/audits/audit_learner_state_builder.py`
- `tests/ulga/test_learner_state_builder_qa_audit.py`
- `ulga/reports/learner_state_builder_qa_audit.json`

## 4. Logic Changed

Added a policy helper:

```python
def has_valid_review_anchor(record):
    ...
```

The blocker condition changed from:

```text
last_success_at is null AND review_due_at exists AND mastery_band != seen
```

to:

```text
review_due_at exists AND not has_valid_review_anchor(record)
```

Current policy:

- `seen`: `last_seen_at` or `last_success_at`
- `practicing`: `last_success_at` or `last_seen_at`
- `functional`, `mastered`, `automatic`: `last_success_at`
- `unknown`: no non-null review due anchor

The audit also preserves pre-guardrail S9F role/ratio risk reporting from `learner_state_guardrail_summary.json`, marked with:

```text
audit_scope: pre_guardrail
```

This keeps historical S9F risk visibility without reclassifying guarded current output as blocker.

## 5. False Positive Blockers Removed

Removed the 4 false-positive blockers:

- `learner:cyndi dialogue:DIALOGUE_ORDERING_FOOD_A1_001`
- `learner:cyndi vocabulary:VOCAB_NODE_004210`
- `learner:james morphology:word_family_read`
- `learner:james skill:writing_revision`

All 4 are `practicing` records with `last_seen_at` and valid `review_due_at`.

## 6. True Blocker Behavior Preserved

Focused tests now verify:

- `practicing + last_seen_at + review_due_at` is allowed
- `practicing + no anchor + review_due_at` is blocked
- `mastered + no last_success_at + review_due_at` is blocked
- `seen + last_seen_at + review_due_at` is allowed

Review-due mismatches remain blockers.

## 7. Commands Executed

```powershell
python ulga\audits\audit_learner_state_builder.py
python -m pytest tests\ulga\test_learner_state_builder_qa_audit.py -q
python -m pytest tests\ulga\test_learner_state_builder.py tests\ulga\test_learner_state_guardrails.py tests\ulga\test_learner_state_stability_audit.py -q
python -m pytest tests\ulga\ -q
```

## 8. Audit Result

```text
Learner state builder QA audit: PASS_WITH_WARNINGS
Warnings: 18
Blockers: 0
```

Generated report:

- `ulga/reports/learner_state_builder_qa_audit.json`

## 9. Test Result

Focused S9F audit tests:

```text
15 passed
```

Learner-state related regression group:

```text
42 passed
```

Full ULGA test suite:

```text
287 passed
```

## 10. Remaining Warnings

Remaining warnings are expected and non-blocking:

- pre-guardrail role high-band low-authority risks
- pre-guardrail ratio overstatement risks
- pre-guardrail single-event derived-node mastery risks
- `WARN_DECAY_NOT_MODELED`
- `WARN_EMPTY_LOG_LIMITATION`

The pre-guardrail warnings are retained for QA traceability. Current guarded learner-state output remains blocker-free under S9F audit.

## 11. Final Verdict

```text
S9F_REMEDIATION_STATUS: PASS
```

Recommended next task:

```text
ULGA-S10E_AntigravityPlanner_Implementation
```
