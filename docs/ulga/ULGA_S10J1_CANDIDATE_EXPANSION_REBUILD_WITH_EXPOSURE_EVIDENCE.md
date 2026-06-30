# ULGA-S10J1 Candidate Expansion Rebuild With Exposure Evidence

## 1. Scope

Rebuilt ULGA-S10J Reinforcement Candidate Expansion to consume S9Y Learner Exposure Evidence Authority.

S10J1 changes the source of prior exposure:

```text
Before: learner_state.json fields inferred prior_exposure locally.
After: learner_exposure_evidence.json is the authority for prior_exposure.
```

S10J1 does not modify:

- learner exposure evidence
- learner state
- learning opportunities
- reinforcement signal
- dependency readiness resolution
- antigravity plan
- reading stub authority
- dependency graph

## 2. Files Created

- `docs/ulga/ULGA_S10J1_CANDIDATE_EXPANSION_REBUILD_WITH_EXPOSURE_EVIDENCE.md`

## 3. Files Modified

- `ulga/builders/build_reinforcement_candidate_expansion.py`
- `ulga/validators/validate_reinforcement_candidate_expansion.py`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `tests/ulga/test_reinforcement_candidate_expansion.py`

## 4. Inputs Read

- `ulga/graph/learner_exposure_evidence.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/graph/reading_stub_authority.json`
- `ulga/learner_state/learner_state.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `docs/ulga/ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10J_REINFORCEMENT_CANDIDATE_EXPANSION_IMPLEMENTATION.md`

## 5. Exposure Evidence Integration

S10J1 supports a new candidate source:

```text
exposure_evidence
```

Input records must satisfy:

```text
target_type = opportunity
prior_exposure = true
target_id exists in learning_opportunities.json
```

Each emitted candidate carries:

- `candidate_source`
- `learner_id`
- `evidence_refs`
- `prior_exposure`
- `ineligible_reason`
- `level_safe`
- `dependency_status`
- `reading_ready`
- `confidence`

Current candidate source distribution:

```json
{
  "exposure_evidence": 2
}
```

## 6. Dependency Resolution Overlay

S10J1 applies `dependency_readiness_resolution.json` before falling back to `learning_opportunities[].dependency.status`.

Current mapped opportunities:

```text
LO_A1_000011 -> dependency_status = blocked
LO_A1_000012 -> dependency_status = blocked
```

Both are blocked by explicit requires level ceiling:

```text
resolution_type = explicit_requires_level_blocked
level_ceiling_passed = false
```

Therefore both candidates are correctly retained for diagnostics but not planner eligible.

## 7. Before Metrics

Before S10J1:

```text
candidate_count = 5
planner_eligible_count = 0
source_distribution = {
  dependency_parent: 1,
  direct_review: 2,
  theme_revisit: 2
}
```

Issue:

```text
prior_exposure was inferred locally from learner_state.json.
```

## 8. After Metrics

After S10J1:

```json
{
  "status": "PASS_WITH_WARNINGS",
  "candidate_count": 2,
  "planner_eligible_count": 0,
  "source_distribution": {
    "exposure_evidence": 2
  },
  "ineligible_reason_distribution": {
    "dependency_blocked": 2
  },
  "exposure_evidence_used_count": 2,
  "dependency_ready_count": 0,
  "reading_ready_count": 2,
  "warnings": [
    "candidate expansion produced candidates, but none are planner eligible"
  ]
}
```

The candidate count dropped from `5` to `2` because S10J1 now requires canonical opportunity-level exposure evidence instead of deriving exposure from learner-state records and dependency-parent heuristics.

## 9. Planner Eligibility Result

Current planner eligible count:

```text
0
```

Reason:

```text
Exposure evidence exists and is consumed, but both mapped opportunities are dependency_blocked and level_blocked.
```

This is expected fail-closed behavior:

```text
prior_exposure = true
reading_ready = true
dependency_status = blocked
level_safe = false
planner_eligible = false
```

## 10. Validator Result

Validator command:

```powershell
python ulga\validators\validate_reinforcement_candidate_expansion.py
```

Result:

```text
Reinforcement Candidate Expansion validation: PASS
```

Validator checks added or tightened:

- `exposure_evidence` is a valid candidate source
- `learner_id` exists when source is `exposure_evidence`
- `evidence_refs` exist in `learner_exposure_evidence.json`
- dependency overlay is applied
- `planner_eligible` is consistent with dependency, reading, prior exposure, and level safety
- `ineligible_reason` is consistent
- summary `ineligible_reason_distribution` matches candidate records
- summary `exposure_evidence_used_count` matches candidate records

## 11. Test Result

Focused command:

```powershell
python -m pytest tests\ulga\test_reinforcement_candidate_expansion.py -q
```

Result:

```text
10 passed
```

S9Y regression command:

```powershell
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
```

Result:

```text
8 passed
```

Full ULGA command:

```powershell
python -m pytest tests\ulga\ -q
```

Result:

```text
344 passed
```

## 12. Warnings

Current warning:

```text
candidate expansion produced candidates, but none are planner eligible
```

This is not a S10J1 blocker. It means the exposure authority is now consumed correctly, but current exposure coverage maps only to dependency-blocked opportunities.

## 13. Final Verdict

S10J1 successfully rebuilds candidate expansion around S9Y exposure evidence and preserves fail-closed dependency behavior.

```text
S10J1_STATUS: PASS_WITH_WARNINGS
```

Recommended next task:

```text
ULGA-S9Z_ExposureCoverageExpansion_DesignScan
```

Reason:

```text
planner_eligible_count = 0
```

Exposure evidence is now wired into candidate expansion, but exposure coverage is still too narrow and currently maps only to blocked opportunities.

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S10J1_CANDIDATE_EXPANSION_REBUILD_WITH_EXPOSURE_EVIDENCE.md`

Files Modified:

- `ulga/builders/build_reinforcement_candidate_expansion.py`
- `ulga/validators/validate_reinforcement_candidate_expansion.py`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `tests/ulga/test_reinforcement_candidate_expansion.py`

Commands Executed:

```powershell
python ulga\builders\build_reinforcement_candidate_expansion.py
python ulga\validators\validate_reinforcement_candidate_expansion.py
python -m pytest tests\ulga\test_reinforcement_candidate_expansion.py -q
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
python -m pytest tests\ulga\ -q
```

Before Metrics:

- `candidate_count`: `5`
- `planner_eligible_count`: `0`

After Metrics:

- `candidate_count`: `2`
- `planner_eligible_count`: `0`
- `exposure_evidence_used_count`: `2`
- `dependency_ready_count`: `0`
- `reading_ready_count`: `2`

Exposure Evidence Usage:

- `LEE_000001 -> LO_A1_000011`
- `LEE_000002 -> LO_A1_000012`

Planner Eligible Count:

- `0`

Validator Result:

- `PASS`

Test Result:

- `10 passed`
- `8 passed`
- `344 passed`

Warnings:

- `candidate expansion produced candidates, but none are planner eligible`

Final Verdict:

```text
S10J1_STATUS: PASS_WITH_WARNINGS
```

Recommended Next Task:

```text
ULGA-S9Z_ExposureCoverageExpansion_DesignScan
```
