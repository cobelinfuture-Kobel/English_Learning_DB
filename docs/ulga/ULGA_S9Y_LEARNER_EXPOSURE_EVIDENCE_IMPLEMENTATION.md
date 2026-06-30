# ULGA-S9Y Learner Exposure Evidence Implementation

## 1. Scope

Implemented ULGA-S9Y Learner Exposure Evidence Authority V1.

S9Y materializes a canonical exposure evidence layer:

```text
Learner State Node
-> Exposure Evidence Authority
-> Learning Opportunity
```

S9Y does not modify:

- learner state
- learning opportunities
- reinforcement candidate expansion
- reinforcement signal
- dependency readiness resolution
- antigravity plan
- dependency graph
- planner behavior

## 2. Files Created

- `ulga/builders/build_learner_exposure_evidence.py`
- `ulga/validators/validate_learner_exposure_evidence.py`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `tests/ulga/test_learner_exposure_evidence.py`
- `docs/ulga/ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE_IMPLEMENTATION.md`

## 3. Files Modified

None outside the S9Y files listed above.

## 4. Inputs Read

- `ulga/learner_state/learner_state.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `docs/ulga/ULGA_S9X_LEARNER_EXPOSURE_EVIDENCE_DESIGN_SCAN.md`

Optional inputs are read as available. Missing optional inputs are handled as warnings rather than hard failures.

## 5. Exposure Model

S9Y V1 keeps exposure separate from success, mastery, review due, and planner eligibility.

Exposure sources used:

- `last_seen_at`
- `exposure_count` as the current learner-state equivalent of `attempt_count`
- `mastery_band`

Exposure sources intentionally not used as exposure proof:

- `review_due_at`
- `last_success_at`

Confidence bands:

| Band | Rule |
|---|---|
| `weak` | `attempt_count = 1`, or current `exposure_count = 1` |
| `medium` | `attempt_count >= 2`, or current `exposure_count >= 2` |
| `strong` | `attempt_count >= 3` and `mastery_band != seen` |

Opportunity exposure score:

```text
base exposure score by confidence band
* mapping weight
```

Current weights:

| Source type | Mapping weight |
|---|---:|
| `vocabulary` | `1.0` |
| `grammar` | `1.0` |
| `theme` | `0.67` |

Theme-only exposure is therefore retained as weak, conservative evidence.

## 6. Mapping Model

S9Y V1 maps:

- vocabulary learner-state records to opportunity focus-node vocabulary refs
- grammar learner-state records to opportunity focus-node grammar refs
- theme learner-state records to opportunity theme refs

Current observed mapping:

```text
theme:a1_daily_life_and_routines
-> LO_A1_000011
-> LO_A1_000012
```

The current learner-state vocabulary and grammar records do not directly match opportunity focus nodes, so V1 produces only theme-overlap opportunity evidence.

Dependency status is copied into each evidence record for downstream diagnostics, but it does not affect whether exposure evidence is materialized.

## 7. Output Counts

Current summary:

```json
{
  "status": "PASS",
  "evidence_count": 2,
  "opportunity_mapping_count": 2,
  "weak_count": 2,
  "medium_count": 0,
  "strong_count": 0,
  "coverage_rate": 0.001488,
  "warnings": []
}
```

Current evidence records:

```text
LEE_000001 -> learner:james -> LO_A1_000011 -> weak theme exposure
LEE_000002 -> learner:james -> LO_A1_000012 -> weak theme exposure
```

Both mapped opportunities currently have:

```text
dependency_status = blocked
```

This is diagnostic only. S9Y does not make dependency-blocked opportunities planner eligible.

## 8. Coverage Metrics

Current coverage:

```text
evidence_count = 2
opportunity_mapping_count = 2
coverage_rate = 0.001488
```

Interpretation:

```text
S9Y confirms that opportunity exposure mapping is non-zero, but current coverage is very narrow and theme-only.
```

This matches S9X:

```text
direct opportunity focus-node mapping = 0
theme mapping = 1 learner-state node
```

## 9. Validator Result

Validator command:

```powershell
python ulga\validators\validate_learner_exposure_evidence.py
```

Result:

```text
Learner Exposure Evidence validation: PASS
```

Validator checks:

- `evidence_id` unique
- learner exists
- opportunity exists
- score range is valid
- confidence band is valid
- `prior_exposure` is boolean and matches positive score
- evidence source is valid
- mapping type is valid
- summary counts match evidence records
- coverage rate matches mapped opportunity count

## 10. Test Result

Focused test command:

```powershell
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
```

Result:

```text
8 passed
```

Full ULGA test command:

```powershell
python -m pytest tests\ulga\ -q
```

Result:

```text
342 passed
```

Focused tests cover:

- builder runs
- validator passes
- evidence exists
- mapping count is greater than zero
- summary exists
- sources and scores are valid
- deterministic output
- upstream inputs are not modified

## 11. Warnings

Current warnings:

```text
None
```

Operational risks still tracked for the next task:

- coverage is low
- current exposure is theme-only
- mapped opportunities are dependency-blocked
- S10J still needs a rebuild step to consume this authority instead of inferring exposure locally

## 12. Final Verdict

S9Y successfully materializes canonical learner exposure evidence without mutating upstream authority artifacts or weakening dependency gates.

```text
S9Y_STATUS: PASS
```

Recommended next task:

```text
ULGA-S10J1_CandidateExpansion_Rebuild_WithExposureEvidence
```

Reason:

```text
opportunity_mapping_count > 0
```

## Closeout Summary

Files Created:

- `ulga/builders/build_learner_exposure_evidence.py`
- `ulga/validators/validate_learner_exposure_evidence.py`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `tests/ulga/test_learner_exposure_evidence.py`
- `docs/ulga/ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE_IMPLEMENTATION.md`

Files Modified:

- None outside S9Y.

Commands Executed:

```powershell
python ulga\builders\build_learner_exposure_evidence.py
python ulga\validators\validate_learner_exposure_evidence.py
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
python -m pytest tests\ulga\ -q
```

Evidence Count:

- `2`

Opportunity Mapping Count:

- `2`

Coverage Rate:

- `0.001488`

Validator Result:

- `PASS`

Test Result:

- `8 passed`
- `342 passed`

Warnings:

- None

Final Verdict:

```text
S9Y_STATUS: PASS
```

Recommended Next Task:

```text
ULGA-S10J1_CandidateExpansion_Rebuild_WithExposureEvidence
```
