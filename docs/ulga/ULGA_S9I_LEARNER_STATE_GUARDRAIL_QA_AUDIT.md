# ULGA-S9I Learner State Guardrail QA Audit

## Files Created

- `ulga/audits/audit_learner_state_guardrails.py`
- `ulga/reports/learner_state_guardrail_qa_audit.json`
- `tests/ulga/test_learner_state_guardrail_qa_audit.py`
- `docs/ulga/ULGA_S9I_LEARNER_STATE_GUARDRAIL_QA_AUDIT.md`

## Files Modified

- None.

## Scope Confirmation

This task performs a read-only behavioral QA audit of the S9H learner-state guardrail implementation.

Not performed in this task:

- builder changes
- guardrail changes
- schema changes
- learner_state regeneration
- summary regeneration

## Commands Executed

- `python ulga/audits/audit_learner_state_guardrails.py`
- `python -m pytest tests/ulga/test_learner_state_guardrail_qa_audit.py -q`
- `python ulga/validators/validate_learner_state_guardrail_output.py`
- `python -m pytest tests/ulga/test_learner_state_guardrails.py tests/ulga/test_learner_state_guardrail_qa_audit.py -q`

## Audit Result

`PASS_WITH_WARNINGS`

Command:

- `python ulga/audits/audit_learner_state_guardrails.py`

Output summary:

- `Learner state guardrail QA audit: PASS_WITH_WARNINGS`
- built `ulga/reports/learner_state_guardrail_qa_audit.json`
- `Ranking readiness: 72`
- `Planner readiness: 58`
- `Blockers: 0`

## Key Findings

- `WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE` is `resolved`.
- `WARN_RATIO_OVERSTATEMENT_RISK` is `partially_resolved`; the remaining flagged record is `learner:cyndi|dialogue:DIALOGUE_ORDERING_FOOD_A1_001`.
- `WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY` is `partially_resolved`; the remaining flagged record is the same `dialogue` record.
- `WARN_DECAY_NOT_MODELED` and `WARN_EMPTY_LOG_LIMITATION` remain `unresolved`.
- `theme`, `assessment`, `morphology`, and `skill` now look behaviorally reasonable after guardrails.
- `dialogue:DIALOGUE_ORDERING_FOOD_A1_001` remains `functional` from a single `supporting_context` event and is assessed as `borderline`.

## Ranking Readiness

`72 / 100`

Interpretation:

- direct node reliability is `moderate_to_good`
- derived node reliability is `improved_but_mixed`
- current learner state can likely feed future ranking with caution, but should not be treated as fully stable

## Planner Readiness

`58 / 100`

Interpretation:

- planner readiness is lower than ranking readiness because decay, graph-aware aggregation, and dialogue exception behavior remain unresolved
- current output should not be treated as stable planner truth yet

## PASS / WARN / BLOCKER

### PASS

- guardrails removed all non-primary single-event `mastered` records
- `grammar:GRAMMAR_NODE_000123` remains legitimately `mastered`
- role ceilings now behave as expected for `coverage_signal`, `diagnostic_signal`, and `review_signal`
- `automatic` threshold is enforced; there are no automatic records
- no blockers were reported

### WARN

- `dialogue:DIALOGUE_ORDERING_FOOD_A1_001` remains `functional` from a single `supporting_context` event
- true decay is still missing
- graph-aware aggregation, theme resolver, and morphology resolver are still missing
- zero-event cold start remains unresolved
- current guardrail thresholds are effective but still heuristic

### BLOCKER

- None.

## Remaining Risks

- `High`: true decay missing
- `High`: graph-aware aggregation missing
- `High`: dialogue exception remains behaviorally borderline
- `Medium`: theme resolver missing
- `Medium`: morphology resolver missing
- `Medium`: zero-event cold start unresolved

## Recommended Next Task

`ULGA-S9J_LearnerState_Stability_Audit`
