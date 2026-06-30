# ULGA-S9F Learner State Builder QA Audit

## Files Created

- `ulga/audits/audit_learner_state_builder.py`
- `ulga/reports/learner_state_builder_qa_audit.json`
- `docs/ulga/ULGA_S9F_LEARNER_STATE_BUILDER_QA_AUDIT.md`
- `tests/ulga/test_learner_state_builder_qa_audit.py`

## Files Modified

- None.

## Scope Confirmation

This task performs a read-only QA audit of the existing S9E LearnerStateBuilder output and scoring behavior.

Not performed in this task:

- builder fixes
- formula changes
- schema changes
- sample event changes
- learner_state output regeneration
- graph changes
- validator changes

## Commands Executed

- `python ulga/audits/audit_learner_state_builder.py`
- `python -m pytest tests/ulga/test_learner_state_builder_qa_audit.py -q`
- `python ulga/validators/validate_learner_state_builder_output.py`
- `python -m pytest tests/ulga/test_learner_state_builder.py tests/ulga/test_learner_state_builder_qa_audit.py -q`

## Audit Result

`PASS_WITH_WARNINGS`

Command:

- `python ulga/audits/audit_learner_state_builder.py`

Output summary:

- `Learner state builder QA audit: PASS_WITH_WARNINGS`
- built `ulga/reports/learner_state_builder_qa_audit.json`
- `Warnings: 18`
- `Blockers: 0`

## Validator Result

`PASS`

Command:

- `python ulga/validators/validate_learner_state_builder_output.py`

Output summary:

- `Learner state builder output validation: PASS`
- validated `ulga/learner_state/learner_state.json`
- validated `ulga/reports/learner_state_builder_summary.json`

## Test Result

`PASS`

Commands:

- `python -m pytest tests/ulga/test_learner_state_builder_qa_audit.py -q`
- `python -m pytest tests/ulga/test_learner_state_builder.py tests/ulga/test_learner_state_builder_qa_audit.py -q`

Results:

- `11 passed in 0.15s`
- `26 passed in 0.42s`

## PASS / WARN / BLOCKER

### PASS

- S9E output remains contract-valid under the S9C learner-state validator.
- Builder summary metrics match actual `learner_state.json`.
- No duplicate `learner_id + node_id` pairs were found.
- No duplicate output `processing_idempotency_key` values were found.
- James and Cyndi remain isolated; no shared node IDs appear across learners in the current output.
- No candidate-ranking or planner fields appear in learner-state output.

### WARN

- Ratio-formula overstatement risk exists for single-event non-primary records, including `dialogue`, `vocabulary` via `prerequisite`, `assessment`, `morphology`, `sentence_pattern`, `skill`, and `theme`.
- Low-authority roles currently produce high mastery bands:
  - `review_signal` -> `assessment` functional
  - `diagnostic_signal` -> `morphology` functional
  - `supporting_context` -> `sentence_pattern` mastered
  - `coverage_signal` -> `theme` mastered
- `decay_adjusted_score == mastery_score` for all records, so true retention decay is not modeled.
- Zero-event global cold start is still not naturally supported because S9C collections are non-empty by contract.

### BLOCKER

- None.

## Key Warnings

- `WARN_ROLE_HIGH_BAND_LOW_AUTHORITY_ROLE` triggered for 4 records.
- `WARN_RATIO_OVERSTATEMENT_RISK` triggered for 6 records.
- `WARN_SINGLE_EVENT_DERIVED_NODE_MASTERY` triggered for 5 records.
- `theme:a1_daily_life_and_routines` reached `mastered` from a single `coverage_signal` event.
- `sentence_pattern:PATTERN_NODE_000014` reached `mastered` from a single `supporting_context` event.
- `assessment:SHORT_WRITING_CHECK_A2_001` and `morphology:word_family_read` reached `functional` from `review_signal` and `diagnostic_signal` evidence respectively.

## Runtime Graph Safety

Confirmed: no runtime graph files were modified in this task.

## Schema Safety

Confirmed: S9B and S9C schema files were not modified in this task.

## S9E Artifact Safety

Confirmed: S9E builder and existing output artifacts were not modified in this task.

## Recommended Next Task

`ULGA-S9G_LearnerStateBuilder_Guardrail_DesignScan`
