# ULGA-S10G Reinforcement Signal Implementation

## 1. Scope

Implemented the ULGA-S10G Reinforcement Signal Authority V1.

S10G materializes derived reinforcement signals without back-writing any upstream authority.

Pipeline:

```text
Learning Opportunities
-> Ranked Learning Opportunities
-> Learner State
-> Dependency Gate
-> Reinforcement Signal Authority
```

S10G V1 emits one opportunity-level signal per learning opportunity.

## 2. Files Created

- `ulga/builders/build_reinforcement_signal.py`
- `ulga/validators/validate_reinforcement_signal.py`
- `ulga/graph/reinforcement_signal.json`
- `ulga/reports/reinforcement_signal_summary.json`
- `tests/ulga/test_reinforcement_signal.py`
- `docs/ulga/ULGA_S10G_REINFORCEMENT_SIGNAL_IMPLEMENTATION.md`

## 3. Files Modified

None outside the S10G files listed above.

## 4. Inputs Read

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/antigravity_plan.json`
- `ulga/graph/reading_stub_authority.json`
- `ulga/learner_state/learner_state.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/schema/learning_signal_policy.json`

All inputs are read-only.

## 5. Signal Model

Output path:

```text
ulga/graph/reinforcement_signal.json
```

Top-level shape:

```json
{
  "metadata": {
    "source": "ULGA_S10G_REINFORCEMENT_SIGNAL",
    "generated_at": "2026-06-18T00:00:00Z",
    "version": "1.0",
    "contract_version": "ULGA-S10G"
  },
  "signals": []
}
```

Each signal includes:

- `signal_id`
- `target_type`
- `target_id`
- `signal_score`
- `signal_band`
- `planner_eligible`
- `ineligible_reason`
- `signal_sources`
- `reason_codes`
- `reinforced_node_refs`
- `score_breakdown`
- `dependency.status`
- `source`

The V1 scoring formula is:

```text
0.30 * review_due_score
+ 0.25 * mastery_gap_score
+ 0.20 * time_decay_score
+ 0.15 * dependency_importance_score
+ 0.10 * theme_continuity_score
```

Theme continuity alone cannot create a positive signal. It only contributes when a concrete learner-state, dependency, or reinforced-node source already exists.

## 6. Dependency Gate

Planner eligibility is fail-closed:

```text
planner_eligible = dependency.status == ready and signal_score > 0
```

Dependency outcomes:

- `ready` with `signal_score > 0`: eligible
- `ready` with `signal_score == 0`: `no_positive_signal`
- `unknown`: `dependency_unknown`
- `blocked`: `dependency_blocked`

Unknown or blocked dependency records never become planner eligible.

## 7. Output Counts

Current output:

- Total signals: 1344
- Signals with score > 0: 7
- Signal band distribution:
  - `none`: 1337
  - `low`: 7

## 8. Planner Eligibility

Current planner eligibility:

- Planner eligible count: 0
- Ineligible count: 1344
- Eligible with score > 0: 0
- Dependency unknown/blocked count: 7

Current ineligible reason distribution:

- `dependency_unknown`: 7
- `no_positive_signal`: 1337

The 7 positive signals correspond to opportunities with concrete `reinforces` node refs, but all 7 have `dependency.status = unknown`.

## 9. Validator Result

Validator command:

```powershell
python ulga\validators\validate_reinforcement_signal.py
```

Result:

```text
Reinforcement Signal validation: PASS
```

Validator checks:

- `signal_id` unique
- one signal per learning opportunity
- `target_id` exists in `learning_opportunities.json`
- `signal_score` is within `0..1`
- `signal_band` matches score
- `planner_eligible` is boolean
- `ineligible_reason` is consistent
- `dependency.status` is valid
- unknown and blocked dependencies are not planner eligible
- positive score has reason codes
- summary metrics match the signal payload
- source is `ULGA_S10G_REINFORCEMENT_SIGNAL`

## 10. Test Result

Focused test command:

```powershell
python -m pytest tests\ulga\test_reinforcement_signal.py -q
python -m pytest tests\ulga\ -q
```

Result:

```text
9 passed
308 passed
```

Focused tests cover:

- builder runs
- validator passes
- signal count equals learning opportunity count
- score range is valid
- unknown dependency cannot be planner eligible
- ready dependency with positive signal may be planner eligible
- summary exists
- deterministic output
- upstream inputs are not modified

## 11. Warnings

Current summary warning:

```text
no planner-eligible positive reinforcement signals were generated
```

This is expected with the current artifacts. S10G confirms the S10F finding:

```text
positive reinforcement evidence exists only on dependency_unknown opportunities.
```

## 12. Final Verdict

S10G materializes reinforcement signals and preserves the hard dependency gate.

It does not modify Ranking, Planner, Learner State, Dependency Graph, Theme Spiral, or Reading Stub Authority.

```text
S10G_STATUS: PASS_WITH_WARNINGS
```

## Closeout Summary

Files Created:

- `ulga/builders/build_reinforcement_signal.py`
- `ulga/validators/validate_reinforcement_signal.py`
- `ulga/graph/reinforcement_signal.json`
- `ulga/reports/reinforcement_signal_summary.json`
- `tests/ulga/test_reinforcement_signal.py`
- `docs/ulga/ULGA_S10G_REINFORCEMENT_SIGNAL_IMPLEMENTATION.md`

Files Modified:

- None outside S10G outputs.

Commands Executed:

```powershell
python ulga\builders\build_reinforcement_signal.py
python ulga\validators\validate_reinforcement_signal.py
python -m pytest tests\ulga\test_reinforcement_signal.py -q
python -m pytest tests\ulga\ -q
```

Output Counts:

- Total signals: 1344
- Signals with score > 0: 7
- Signal band distribution: `none=1337`, `low=7`

Planner Eligibility Counts:

- Planner eligible: 0
- Ineligible: 1344
- Eligible with score > 0: 0
- Dependency unknown/blocked: 7

Validator Result:

- `PASS`

Test Result:

- `9 passed`
- `308 passed`

Warnings:

- `no planner-eligible positive reinforcement signals were generated`

Final Verdict:

```text
S10G_STATUS: PASS_WITH_WARNINGS
```

Recommended Next Task:

```text
ULGA-S10H_PlannerReAudit_WithReinforcementSignal
```
