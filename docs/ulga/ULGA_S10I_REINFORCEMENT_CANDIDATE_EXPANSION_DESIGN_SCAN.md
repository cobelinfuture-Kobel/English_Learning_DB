# ULGA-S10I Reinforcement Candidate Expansion Design Scan

## 1. Scope

S10I is a read-only design scan for **Reinforcement Candidate Expansion** after S10G, S10H, S8X, and S8Y.

Question:

```text
How should ULGA produce planner-eligible reinforcement candidates when current positive reinforcement signals are all dependency-blocked?
```

This scan does not implement:

- builders
- validators
- graph outputs
- reports
- schema changes
- learner-state changes
- planner changes
- reinforcement block changes

S10I keeps S10E fail-closed. It does not force planner selection and does not weaken dependency readiness.

## 2. Inputs Reviewed

Runtime artifacts reviewed:

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/reinforcement_signal.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/graph/antigravity_plan.json`
- `ulga/graph/reading_stub_authority.json`
- `ulga/learner_state/learner_state.json`
- `ulga/schema/learning_signal_policy.json`

Reports reviewed:

- `ulga/reports/reinforcement_signal_summary.json`
- `ulga/reports/dependency_readiness_resolution_summary.json`
- `ulga/reports/antigravity_planner_reinforcement_audit.json`
- `ulga/reports/antigravity_plan_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/learning_opportunity_summary.json`

Design and implementation documents reviewed:

- `docs/ulga/ULGA_S10F_REINFORCEMENT_SIGNAL_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10G_REINFORCEMENT_SIGNAL_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10H_PLANNER_REAUDIT_WITH_REINFORCEMENT_SIGNAL.md`
- `docs/ulga/ULGA_S8X_DEPENDENCY_READINESS_RESOLUTION_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8Y_DEPENDENCY_READINESS_RESOLUTION_IMPLEMENTATION.md`

Missing optional inputs:

```text
None
```

## 3. Current Reinforcement Candidate Gap

Current S10G summary:

```text
total_signals = 1344
signals_with_score_gt_zero = 7
planner_eligible_count = 0
eligible_with_score_gt_zero = 0
dependency_unknown_blocked_count = 7
```

Current positive signal split:

```text
positive reinforcement signals count = 7
ready positive count = 0
blocked positive count after S8Y = 7
unknown positive count after S8Y = 0
```

S8Y resolution summary:

```text
Unknown Inputs = 7
Resolved Ready = 0
Resolved Blocked = 7
Still Unknown = 0
Resolution Type = explicit_requires_level_blocked: 7
```

This means the original blocker is no longer merely `dependency_unknown`. The resolved state is stricter:

```text
All current positive reinforcement candidates are level-blocked.
```

S10H correctly reports no planner failure:

```text
planner_failure = false
signal_failure = false
structural_fallback_detected = true
```

The current gap is:

```text
S10G can score reinforcement, and S10E can degrade safely,
but the system has no expansion layer that finds alternative
dependency-ready, content-deliverable reinforcement candidates.
```

## 4. Candidate Source Taxonomy

S10I recommends five candidate source classes:

1. Direct Review Candidates
2. Mastery Gap Candidates
3. Related Opportunity Candidates
4. Dependency Parent Reinforcement Candidates
5. Theme Spiral Revisit Candidates

These are candidate sources, not automatic planner approvals. Every expanded candidate must still pass:

- prior exposure evidence
- dependency readiness
- reading/content delivery readiness
- level ceiling
- recent repetition guard
- mastered-state guard

## 5. Direct Review Candidates

Direct review candidates come from learner-state records with review timing evidence.

Current usable fields:

- `review_due_at`
- `mastery_band`
- `last_seen_at`
- `last_success_at`
- `exposure_count`
- `correct_count`
- `incorrect_count`

Current artifact facts:

```text
learner_state records = 9
records with review_due_at = 8
records with last_seen_at = 9
records with last_success_at = 3
mastery bands = practicing: 5, seen: 2, functional: 1, mastered: 1
```

Current blocker:

```text
0 learner_state node_id values map directly to current learning opportunity focus or reinforces refs.
```

Design implication:

Direct review is viable only after a mapping layer can connect learner-state refs such as dialogue, morphology, skill, sentence_pattern, and theme records to mounted learning opportunity refs.

Recommended S10J behavior:

- emit direct review candidates only when at least one learner-state node maps to a deliverable opportunity target
- keep unmapped review-due records in an audit queue
- never fabricate opportunity-level reinforcement from review_due alone

## 6. Mastery Gap Candidates

Mastery gap candidates come from weak-but-known learner-state evidence.

Candidate evidence:

- `mastery_score < threshold`
- `mastery_band in seen/practicing`
- sufficient exposure or attempt evidence
- low success ratio when counts are available

Current artifact facts:

```text
seen/practicing records = 7
mapped seen/practicing records = 0
```

Key design distinction:

```text
reinforcement != remediation
```

Use reinforcement when the learner has prior exposure and a related opportunity can strengthen the same target without bypassing hard gates.

Use remediation when evidence indicates failure, prerequisite gap, or diagnostic repair. Remediation may later become a separate candidate stream and should not be silently mixed into ordinary reinforcement.

Recommended S10J behavior:

- classify weak mapped records as `mastery_gap`
- classify failed prerequisite evidence separately as `remediation_candidate`
- require a concrete target ref before opportunity promotion

## 7. Related Opportunity Candidates

Related opportunity candidates use graph and opportunity overlap to find a safe opportunity that reinforces a previously seen node or context.

Valid relation types:

- same concrete vocabulary ref
- same concrete grammar ref
- same pattern ref or accepted pattern-family mapping
- same chunk ref
- same theme plus prior exposure plus concrete node overlap

Example:

```text
prior target: house
related opportunities: kitchen / bedroom / There is a kitchen.
```

Important boundary:

```text
same theme alone is not reinforcement
```

Current opportunity facts:

```text
total opportunities = 1344
dependency-ready opportunities = 1337
reading delivery-ready opportunity coverage = 1344
ready opportunities with reading delivery = 1337
theme specificity = 1.0
```

The system has enough ready, deliverable opportunities to search. The missing piece is a conservative mapping and expansion policy that can connect prior exposure to those opportunities.

Recommended S10J behavior:

- build node-to-opportunity indexes for vocabulary, grammar, pattern, chunk, and theme
- prefer exact node matches before family/theme matches
- cap same-theme-only expansion to non-eligible audit records unless concrete prior exposure exists

## 8. Dependency Parent Reinforcement

Dependency parent reinforcement targets a prerequisite or parent node that supports future child opportunities.

Pattern:

```text
child opportunity depends on parent prerequisite
parent is weak / due / recently failed
deliver parent through a ready opportunity
```

Example:

```text
there are
requires
there is / be verb
```

S8Y changed the immediate interpretation of current positive signals:

```text
The 7 current positive signals are not usable dependency parent reinforcement.
They are child opportunities with required A2 grammar above an A1 opportunity ceiling.
```

Recommended S10J behavior:

- do not use blocked child opportunities as reinforcement delivery candidates
- search for ready parent/prerequisite opportunities instead
- preserve a separate `blocked_by_dependency` or `blocked_by_level` reason for child records
- treat dependency parent reinforcement as candidate expansion, not dependency override

## 9. Theme Spiral Revisit

Theme Spiral revisit candidates use theme continuity as a preference for returning to a known context.

Valid pattern:

```text
Home A1 -> Family A1 -> Home revisit
```

Required evidence:

- prior exposure to the theme or a concrete node inside the theme
- a ready opportunity under that theme
- reading/content delivery readiness
- not recently repeated

Safety rule:

```text
theme continuity alone cannot create eligible reinforcement
```

Theme revisit is useful as a tiebreaker or explanation after concrete review/mastery/dependency evidence exists.

## 10. Candidate Expansion Schema Draft

Proposed future artifact:

```text
ulga/graph/reinforcement_candidate_expansion.json
```

Draft top-level shape:

```json
{
  "metadata": {
    "source": "ULGA_S10J_REINFORCEMENT_CANDIDATE_EXPANSION",
    "version": "1.0",
    "generated_at": "2026-06-18T00:00:00Z"
  },
  "candidates": [
    {
      "candidate_id": "RCE_000001",
      "opportunity_id": "LO_A1_HOME_000001",
      "candidate_source": "dependency_parent",
      "target_refs": {
        "vocabulary": [],
        "grammar": [],
        "pattern": [],
        "theme": [],
        "chunk": []
      },
      "evidence": {
        "prior_exposure": true,
        "review_due": false,
        "mastery_gap": 0.0,
        "dependency_parent": false,
        "theme_revisit": false
      },
      "dependency_status": "ready",
      "planner_eligible": true,
      "confidence": 0.0,
      "warnings": []
    }
  ]
}
```

Recommended additional fields for implementation:

- `reading_delivery_ready`
- `level_ceiling_passed`
- `recent_repetition_blocked`
- `already_mastered_blocked`
- `blocked_reason`
- `source_refs`
- `learner_id`

## 11. Expansion Policy

Required policy gates:

```text
prior exposure required
dependency readiness required
reading delivery required
level ceiling required
not recently repeated
not already mastered unless review_due
```

Recommended candidate status outcomes:

- `eligible`
- `blocked_by_dependency`
- `blocked_by_level`
- `blocked_by_missing_mapping`
- `blocked_by_missing_reading`
- `blocked_by_recent_repetition`
- `blocked_by_mastered_state`
- `audit_only_insufficient_evidence`

Minimal V1 eligibility rule:

```text
planner_eligible =
  prior_exposure
  and dependency_status == ready
  and reading_delivery_ready
  and level_ceiling_passed
  and not recent_repetition_blocked
  and not already_mastered_blocked
  and concrete target_refs are non-empty
```

## 12. Integration With Reinforcement Signal Authority

S10I recommends adding candidate expansion before or inside a future S10G rebuild path:

```text
learner_state + opportunity indexes + dependency readiness + reading delivery
-> reinforcement_candidate_expansion.json
-> reinforcement_signal.json
-> S10E planner
```

S10G should not merely read every expanded candidate as positive signal. It should:

- score eligible expansion candidates
- preserve blocked candidates for diagnostics
- distinguish `review_due`, `mastery_gap`, `related_opportunity`, `dependency_parent`, and `theme_revisit`
- continue to fail closed on dependency and level blocks

Recommended S10G signal behavior:

```text
positive score + planner_eligible = real reinforcement signal
positive score + blocked = diagnostic blocked signal
zero score = no_positive_signal
```

## 13. Impact on Antigravity Planner

S10E should not change first.

Current S10E behavior is safe:

- it keeps a reinforcement block structurally
- it does not claim ineligible reinforcement evidence
- it warns when no eligible reinforcement exists

Recommended planner path:

1. Implement candidate expansion.
2. Rebuild reinforcement signals from expanded candidates.
3. Re-run S10H audit.
4. Only then consider S10E consumption changes.

S10E should continue to consume `reinforcement_signal.json`, not raw expansion candidates.

## 14. QA / Audit Plan

Required summary metrics:

- `expanded_candidate_count`
- `candidate_source_distribution`
- `prior_exposure_coverage`
- `dependency_ready_count`
- `reading_delivery_ready_count`
- `planner_eligible_count`
- `blocked_by_level_count`
- `blocked_by_dependency_count`
- `blocked_by_recent_repetition_count`
- `false_reinforcement_guard_count`

Additional recommended metrics:

- `mapped_learner_state_record_count`
- `unmapped_learner_state_record_count`
- `ready_deliverable_candidate_count`
- `theme_only_candidate_count`
- `same_theme_only_blocked_count`
- `already_mastered_blocked_count`
- `remediation_separated_count`
- `deterministic_candidate_hash`

Required audits:

- every eligible candidate has concrete target refs
- every eligible candidate maps to an existing opportunity
- every eligible candidate has delivery-ready reading/content
- no blocked S8Y dependency record becomes planner eligible
- no same-theme-only record becomes eligible
- no recently repeated record becomes eligible
- no mastered record becomes eligible unless review_due is true
- candidate ordering is deterministic

## 15. Safety Rules

Hard safety rules:

- Do not treat all same-theme opportunities as reinforcement.
- Do not treat high-ranked opportunities as reinforcement without target evidence.
- Do not bypass dependency readiness.
- Do not bypass level ceiling.
- Do not let planner demand create a fake signal.
- Do not silently mix remediation into reinforcement.
- Do not use reading availability alone as reinforcement evidence.
- Do not use Theme Spiral alone as reinforcement evidence.
- Do not promote S8Y `blocked` records into S10G planner eligibility.

Operational risks and mitigations:

- API failure or timeout: future external learner-history services must fail closed and preserve local artifact fallback.
- Empty data: emit zero eligible candidates plus warnings, not fabricated reinforcement.
- Duplicate execution: use stable `candidate_id` ordering from source type, opportunity id, learner id, and target refs.
- Process restart: deterministic ordering and generated timestamps fixed by build policy.
- Resource growth: cap related-opportunity expansion by exact-match priority and per-source limits.
- Invalid polling: do not poll for learner evidence; consume versioned local artifacts or explicit input snapshots.

## 16. Recommended Implementation Path

Recommended next task:

```text
ULGA-S10J_ReinforcementCandidateExpansion_Implementation
```

Minimal S10J implementation:

1. Build read-only indexes from learner state, learning opportunities, reading stubs, and dependency readiness.
2. Emit `reinforcement_candidate_expansion.json`.
3. Emit `reinforcement_candidate_expansion_summary.json`.
4. Keep unmapped learner-state records as audit records.
5. Require concrete target refs for eligibility.
6. Apply dependency, level, reading, repetition, and mastered-state guards.
7. Add validator and deterministic tests.

Optional prerequisite if mapping risk is considered too high:

```text
ULGA-S9?_LearnerExposureEvidence_DesignScan
```

Use this if the team wants a dedicated design scan for mapping learner-state node types such as dialogue, morphology, sentence_pattern, skill, assessment, and theme into mounted ULGA opportunity refs before S10J.

## 17. Final Verdict

S10I is design-ready.

The current zero eligible reinforcement state is not a planner bug and not a dependency resolver bug.

Current facts:

```text
positive reinforcement signals = 7
ready positive signals = 0
S8Y blocked positive signals = 7
planner eligible positive signals = 0
```

The next system need is a conservative candidate expansion layer that searches for alternative ready, deliverable, prior-exposure-backed reinforcement opportunities.

```text
S10I_STATUS: DESIGN_READY
```

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S10I_REINFORCEMENT_CANDIDATE_EXPANSION_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- `learning_opportunities.json`
- `ranked_learning_opportunities.json`
- `reinforcement_signal.json`
- `dependency_readiness_resolution.json`
- `antigravity_plan.json`
- `reading_stub_authority.json`
- `learner_state.json`
- `learning_signal_policy.json`
- S10F/S10G/S10H and S8X/S8Y docs
- S10G/S8Y/S10H/S10E/S10C/S10B reports

Candidate Gap Summary:

- 7 positive reinforcement signals exist.
- 0 positive signals are dependency-ready.
- S8Y resolves all 7 current positive cases as blocked by level ceiling.
- Learner state has review/mastery evidence, but current learner-state refs do not directly map to opportunity focus or reinforces refs.

Candidate Source Model:

- Direct Review Candidates
- Mastery Gap Candidates
- Related Opportunity Candidates
- Dependency Parent Reinforcement Candidates
- Theme Spiral Revisit Candidates

Key Safety Decisions:

- Prior exposure is required.
- Concrete target refs are required.
- Dependency readiness is required.
- Reading/content delivery is required.
- Level ceiling is required.
- Same-theme alone is not reinforcement.
- Remediation must stay separate from reinforcement.

Final Verdict:

```text
S10I_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
ULGA-S10J_ReinforcementCandidateExpansion_Implementation
```
