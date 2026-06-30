# ULGA-S9K Dialogue Exception Tightening

## Files Modified

- `ulga/builders/build_learner_state.py`

## Files Created

- `ulga/reports/dialogue_exception_tightening_summary.json`
- `ulga/validators/validate_dialogue_exception_tightening.py`
- `tests/ulga/test_dialogue_exception_tightening.py`
- `docs/ulga/ULGA_S9K_DIALOGUE_EXCEPTION_TIGHTENING.md`

## Scope Confirmation

This task only tightens the single-event non-primary dialogue exception.

Not implemented in this task:

- decay
- resolver
- ranking
- planner
- schema changes
- graph changes

## Before / After

`dialogue:DIALOGUE_ORDERING_FOOD_A1_001`

- before: `0.62 functional`
- after: `0.49 practicing`
- strongest role: `supporting_context`
- exposure count: `1`
- guardrail reason: `single_event_ceiling`

Summary:

- `records_evaluated`: `9`
- `dialogue_records_evaluated`: `1`
- `records_modified`: `1`

## Validator Result

`PASS`

Command:

- `python ulga/validators/validate_dialogue_exception_tightening.py`

Output summary:

- `Dialogue exception tightening validation: PASS`
- validated `ulga/learner_state/learner_state.json`
- validated `ulga/reports/dialogue_exception_tightening_summary.json`

## Test Result

`PASS`

Commands:

- `python -m pytest tests/ulga/test_dialogue_exception_tightening.py -q`
- `python -m pytest tests/ulga/test_learner_state_guardrails.py tests/ulga/test_dialogue_exception_tightening.py -q`

Results:

- `8 passed in 0.23s`
- `24 passed in 0.46s`

## PASS / WARN / BLOCKER

### PASS

- Single-event non-primary `dialogue` records now use the standard `0.49` ceiling.
- The current `dialogue:DIALOGUE_ORDERING_FOOD_A1_001` record is now `practicing`.
- Single-event `primary_target` dialogue remains allowed to reach `functional`.
- Multi-event dialogue is not capped by the single-event rule.
- S9C validation and guardrail validation still pass.

### WARN

- Windows file replacement produced a transient `Access denied` during repeated CLI rebuild tests; the builder atomic write now retries short-lived `PermissionError` failures.
- True decay, resolver logic, ranking, and planner remain out of scope.

### BLOCKER

- None.

## Recommended Next Task

`ULGA-S9L_PostTightening_Readiness_Audit`
