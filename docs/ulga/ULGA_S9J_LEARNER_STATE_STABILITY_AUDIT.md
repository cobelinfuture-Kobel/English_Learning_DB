# ULGA-S9J Learner State Stability Audit

## Files Created

- `ulga/audits/audit_learner_state_stability.py`
- `ulga/reports/learner_state_stability_audit.json`
- `tests/ulga/test_learner_state_stability_audit.py`
- `docs/ulga/ULGA_S9J_LEARNER_STATE_STABILITY_AUDIT.md`

## Files Modified

- None.

## Scope Confirmation

This task performs a read-only stability audit of the current guarded Learner State system.

Not performed in this task:

- builder changes
- guardrail changes
- learner-state regeneration
- schema changes
- graph changes

## Audit Result

`PASS_WITH_WARNINGS`

Commands executed:

- `python ulga/audits/audit_learner_state_stability.py`
- `python -m pytest tests/ulga/test_learner_state_stability_audit.py -q`
- `python ulga/validators/validate_learner_state_guardrail_output.py`
- `python -m pytest tests/ulga/test_learner_state_guardrail_qa_audit.py tests/ulga/test_learner_state_stability_audit.py -q`

Results:

- stability audit: `PASS_WITH_WARNINGS`
- stability audit tests: `11 passed in 0.13s`
- guardrail validator: `PASS`
- combined audit tests: `22 passed in 0.21s`

## Ranking Readiness

`74 / 100`

Interpretation: `Limited Production`

Current learner-state output is suitable as an authority source for `S10A_CandidateRanking_DesignScan`, with caution around sparse records, derived node types, and dialogue.

## Planner Readiness

`57 / 100`

Interpretation: `Experimental`

Planner use remains too risky because true decay, graph-aware aggregation, and dialogue stability are unresolved.

## Direct Node Scores

- `grammar`: `82`
- `vocabulary`: `68`
- `chunk`: `76`
- `sentence_pattern`: `62`

## Derived Node Scores

- `theme`: `54`
- `morphology`: `56`
- `skill`: `55`
- `assessment`: `52`
- `dialogue`: `50`
- `reading`: `45`
- `exercise_type`: `40`

## Dialogue Assessment

`dialogue:DIALOGUE_ORDERING_FOOD_A1_001` remains the main stability risk.

- risk level: `high`
- future ranking impact: `medium_to_high`
- future planner impact: `high`
- recommendation: `tighten`

## Missing Components

- `critical`: true decay
- `high`: theme resolver
- `high`: morphology resolver
- `high`: graph-aware aggregation
- `medium`: productive vs recognition evidence separation
- `medium`: cold-start handling

## Future Failure Modes

- `critical`: missing decay
- `high`: dialogue inflation
- `high`: data sparsity
- `medium`: overestimated readiness
- `medium`: underestimated readiness
- `medium`: morphology inflation
- `medium`: cold-start learners
- `low`: theme inflation

## PASS / WARN / BLOCKER

### PASS

- deterministic rebuild, idempotency, replay safety, and rebuild safety are stable enough for design-stage candidate ranking work
- direct node readiness is stronger than derived node readiness
- guarded output is materially safer than S9E pre-guardrail output
- ranking readiness exceeds planner readiness

### WARN

- guardrail stability is still `borderline` for future multi-event behavior
- dialogue exception remains a high-risk stability item
- true decay and graph-aware aggregation are missing
- derived node types remain experimental as ranking signals

### BLOCKER

- None.

## Recommended Next Task

`S10A_CandidateRanking_DesignScan`

Decision: `Yes with warnings`
