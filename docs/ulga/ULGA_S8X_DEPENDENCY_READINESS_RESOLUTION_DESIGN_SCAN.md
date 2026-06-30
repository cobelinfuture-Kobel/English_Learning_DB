# ULGA-S8X Dependency Readiness Resolution Design Scan

## 1. Scope

S8X is a read-only root cause design scan for the current Dependency Readiness gap surfaced by S10G and S10H.

This document does not implement a builder, validator, schema, report, planner change, ranking change, learner-state change, or dependency graph mutation.

Question:

```text
Why do all positive reinforcement signals remain planner-ineligible?
```

Current answer:

```text
S10G can materialize reinforcement signals.
S10E degrades correctly.
The unresolved gap is upstream dependency readiness resolution.
```

## 2. Inputs Reviewed

Artifacts reviewed:

- `ulga/graph/dependency_graph.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/reinforcement_signal.json`
- `ulga/graph/antigravity_plan.json`
- `ulga/reports/reinforcement_signal_summary.json`
- `ulga/reports/antigravity_planner_reinforcement_audit.json`
- `ulga/reports/dependency_graph_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/learning_opportunity_summary.json`
- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8D_DEPENDENCY_AUTHORITY_QA_AUDIT.md`
- `docs/ulga/ULGA_S10F_REINFORCEMENT_SIGNAL_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10G_REINFORCEMENT_SIGNAL_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10H_PLANNER_REAUDIT_WITH_REINFORCEMENT_SIGNAL.md`
- `ulga/builders/build_learning_opportunities.py`

Missing optional inputs:

- None found for this scan.

## 3. Current Dependency Readiness Problem

S10H established:

```json
{
  "planner_failure": false,
  "signal_failure": false,
  "primary_cause": "UPSTREAM_DEPENDENCY_READINESS_GAP"
}
```

S10G summary:

- `total_signals`: 1344
- `signals_with_score_gt_zero`: 7
- `planner_eligible_count`: 0
- `eligible_with_score_gt_zero`: 0
- `dependency_unknown_blocked_count`: 7

S10B opportunity summary:

- `total_opportunities`: 1344
- `dependency_status_counts.ready`: 1337
- `dependency_status_counts.unknown`: 7

The 7 unknown opportunities are the only opportunities with positive reinforcement signal score.

The current S10B dependency metadata rule is conservative:

```text
if explicit requires exist:
  dependency.status = unknown
else:
  dependency.status = ready
```

This prevents planner false positives, but it also prevents any positive reinforcement signal from becoming planner eligible.

## 4. Unknown Inventory

All unknown-positive opportunities are A1 pattern-derived opportunities with grammar focus refs and explicit grammar `REQUIRES` refs.

| Opportunity | Level | Pattern | Theme refs | Focus grammar | Requires | Signal score | Ineligible reason |
|---|---|---|---|---|---|---:|---|
| `LO_A1_000003` | A1 | `SP_000003` | `theme:a1_personal_information_and_greetings` | `grammar:GRAMMAR_NODE_001187` | `grammar:GRAMMAR_NODE_000884`, `grammar:GRAMMAR_NODE_000970` | 0.19 | `dependency_unknown` |
| `LO_A1_000006` | A1 | `SP_000006` | `theme:a1_interests_and_abilities` | `grammar:GRAMMAR_NODE_000487`, `grammar:GRAMMAR_NODE_000492` | `grammar:GRAMMAR_NODE_000488`, `grammar:GRAMMAR_NODE_000489`, `grammar:GRAMMAR_NODE_000586` | 0.19 | `dependency_unknown` |
| `LO_A1_000007` | A1 | `SP_000007` | `theme:a1_interests_and_abilities` | `grammar:GRAMMAR_NODE_000488`, `grammar:GRAMMAR_NODE_000492` | `grammar:GRAMMAR_NODE_000488`, `grammar:GRAMMAR_NODE_000489`, `grammar:GRAMMAR_NODE_000586` | 0.19 | `dependency_unknown` |
| `LO_A1_000008` | A1 | `SP_000008` | `theme:a1_homes_and_neighborhoods` | `grammar:GRAMMAR_NODE_001211` | `grammar:GRAMMAR_NODE_001217` | 0.19 | `dependency_unknown` |
| `LO_A1_000009` | A1 | `SP_000009` | `theme:a1_homes_and_neighborhoods` | `grammar:GRAMMAR_NODE_001211` | `grammar:GRAMMAR_NODE_001217` | 0.19 | `dependency_unknown` |
| `LO_A1_000011` | A1 | `SP_000011` | `theme:a1_daily_life_and_routines` | `grammar:GRAMMAR_NODE_001187` | `grammar:GRAMMAR_NODE_000884`, `grammar:GRAMMAR_NODE_000970` | 0.19 | `dependency_unknown` |
| `LO_A1_000012` | A1 | `SP_000012` | `theme:a1_daily_life_and_routines` | `grammar:GRAMMAR_NODE_001187` | `grammar:GRAMMAR_NODE_000884`, `grammar:GRAMMAR_NODE_000970` | 0.19 | `dependency_unknown` |

Inventory observations:

- `missing_requires` is empty for all 7.
- Every `requires` node exists in `grammar_nodes.json`.
- Every focus grammar node exists in `grammar_nodes.json`.
- The `REQUIRES` edges exist in `dependency_graph.json` from focus grammar to required grammar.
- This is not a dangling-reference problem.
- This is not a missing dependency graph edge problem for the listed requirements.

## 5. Root Cause Classification

Classification summary:

| Class | Count | Applies? | Notes |
|---|---:|---|---|
| `MISSING_DEPENDENCY_METADATA` | 0 | No | The opportunities have dependency metadata. |
| `MISSING_REQUIRES_EDGE` | 0 | No | Required edges exist for the listed focus grammar refs. |
| `MISSING_NODE_MAPPING` | 0 | No | Focus and required grammar node refs resolve. |
| `PATTERN_DERIVED_WITHOUT_GRAMMAR` | 0 | No | The opportunities do have grammar refs. |
| `CHUNK_DERIVED_WITHOUT_DEPENDENCY` | 0 | No | These 7 cases are grammar/pattern opportunities, not chunk dependency cases. |
| `AUTHORITY_REFERENCE_MISMATCH` | 0 | No | No prefix or id mismatch found for the involved grammar refs. |
| `CONSERVATIVE_UNKNOWN_POLICY` | 7 | Yes | S10B marks all opportunities with explicit requires as unknown because no readiness resolver exists. |
| `OTHER` | 0 | No | No additional root cause needed. |

Primary root cause:

```text
CONSERVATIVE_UNKNOWN_POLICY
```

More precise description:

```text
Dependency graph evidence exists, but there is no Dependency Readiness Resolution Authority that can decide whether explicit requires are already safe, content-contained, learner-ready, or still blocking.
```

## 6. Dependency Readiness Semantics

S8X should define readiness statuses as planner-facing runtime metadata, not raw graph facts.

### `ready`

Meaning:

```text
The opportunity can be considered by planner consumers after dependency checks.
```

Allowed reasons:

- no explicit hard `REQUIRES`
- all required nodes are known ready for the planner context
- requires are content-contained and below a safe threshold
- dependency is a reinforcement/review relation, not a hard gate
- resolution authority emits accepted `resolved_dependency_status = ready`

### `blocked`

Meaning:

```text
The opportunity must not be selected until dependency remediation occurs.
```

Allowed reasons:

- required node is missing
- required node is explicitly unmet for learner mode
- dependency relation is hard gate and readiness evidence fails
- authority reference cannot be resolved
- required node is above allowed scope for the current delivery context

### `unknown`

Meaning:

```text
Dependency graph found explicit requires, but readiness cannot be safely decided from current evidence.
```

Unknown is not blocked.

Unknown is also not ready.

Planner-facing behavior:

- default fail-closed for hard-gated planner eligibility
- preserve diagnostic information
- allow design/audit tooling to propose resolution
- do not silently promote to ready

## 7. Resolution Policy

S8Y should implement a separate `DependencyReadinessResolution` layer rather than changing S10E or S10G directly.

Recommended V1 policies:

### `no_requires_ready`

If an opportunity has no explicit hard `REQUIRES`, resolve:

```text
ready
```

Confidence:

```text
0.95
```

### `all_refs_valid_requires_review`

If explicit `REQUIRES` exist and all required node refs resolve, keep:

```text
unknown
```

until one of the stricter readiness rules below applies.

Confidence:

```text
0.50
```

This is the current state for the 7 unknown-positive opportunities.

### `content_contained_requires_ready`

If an opportunity explicitly includes both the focus grammar and its required grammar in deliverable content or teaching scaffold, resolve:

```text
ready
```

Required evidence:

- valid pattern ref
- valid vocabulary refs
- valid theme refs
- valid required node refs
- required node covered by reading/dialogue/content authority or an explicit scaffold flag

Confidence:

```text
0.75-0.85
```

### `same_or_lower_level_requires_ready`

If all required nodes are same or lower CEFR than the opportunity focus and content authority can deliver them, resolve:

```text
ready
```

Required evidence:

- CEFR is not the only evidence
- graph edge is accepted hard `REQUIRES`
- required node resolves
- content authority can include or assume the required node

Confidence:

```text
0.70-0.80
```

### `higher_level_requires_unknown`

If any required node is higher CEFR than the opportunity focus or current opportunity level, keep:

```text
unknown
```

unless manually reviewed.

This is important for current inventory:

- `LO_A1_000003`, `LO_A1_000011`, and `LO_A1_000012` require `grammar:GRAMMAR_NODE_000884`, an A2 past simple affirmative node, from A1 main-verb opportunities.
- `LO_A1_000006` and `LO_A1_000007` require `grammar:GRAMMAR_NODE_000586`, an A2 `must` obligation node, from A1 `can` opportunities.
- `LO_A1_000008` and `LO_A1_000009` require `grammar:GRAMMAR_NODE_001217`, an A2 uncountable `there is` node, from A1 `there is` opportunities.

These should not be auto-promoted to ready without a targeted evidence audit.

### `missing_ref_blocked`

If required node refs do not resolve:

```text
blocked
```

Confidence:

```text
0.95
```

### `manual_review_required_unknown`

If edge semantics are valid but pedagogical direction is questionable, keep:

```text
unknown
```

and queue review.

## 8. Resolution Schema Draft

Proposed future artifact:

```text
ulga/graph/dependency_readiness_resolution.json
```

Draft schema:

```json
{
  "metadata": {
    "source": "ULGA_S8Y_DEPENDENCY_READINESS_RESOLUTION",
    "generated_at": "2026-06-18T00:00:00Z",
    "version": "1.0"
  },
  "resolutions": [
    {
      "resolution_id": "DRR_000001",
      "opportunity_id": "LO_B1_000184",
      "previous_dependency_status": "unknown",
      "resolved_dependency_status": "ready",
      "resolution_type": "no_requires_ready",
      "evidence": {
        "has_valid_pattern": true,
        "has_valid_vocabulary": true,
        "has_valid_theme": true,
        "has_explicit_requires": false,
        "requires_resolve": true,
        "content_contains_required_nodes": false,
        "higher_level_requires_count": 0
      },
      "confidence": 0.8,
      "planner_eligible_after_resolution": true,
      "warnings": []
    }
  ]
}
```

Required fields:

- `resolution_id`
- `opportunity_id`
- `previous_dependency_status`
- `resolved_dependency_status`
- `resolution_type`
- `evidence`
- `confidence`
- `planner_eligible_after_resolution`
- `warnings`

Allowed `resolved_dependency_status`:

- `ready`
- `blocked`
- `unknown`

Allowed `resolution_type`:

- `no_requires_ready`
- `content_contained_requires_ready`
- `same_or_lower_level_requires_ready`
- `higher_level_requires_unknown`
- `missing_ref_blocked`
- `manual_review_required_unknown`
- `all_refs_valid_requires_review`

## 9. Safety Rules

Hard rules:

- Do not batch-convert all `unknown` dependencies to `ready`.
- Do not promote missing node refs to `ready`.
- Do not use theme continuity as dependency readiness evidence.
- Do not convert `blocked` to `ready` without explicit remediation evidence.
- Do not let planner pressure change dependency readiness.
- Do not treat CEFR alone as prerequisite evidence.
- Do not treat reinforcement signal score as proof of dependency readiness.
- Do not let `reading_available` alone satisfy hard grammar dependencies.
- Do not mutate `learning_opportunities.json` directly in S8Y; emit a derived resolution artifact first.
- Do not change S10E until S10H re-audit proves safe consumption behavior.

## 10. Impact on Reinforcement Signal

Current S10G:

- 7 positive reinforcement signals
- 0 eligible positive reinforcement signals
- all 7 positive signals have `ineligible_reason = dependency_unknown`

If S8Y resolves any of the 7 from `unknown` to `ready`, then a rebuilt S10G could make those signals planner eligible.

Expected impact if all 7 were safely resolved:

```text
signals_with_score_gt_zero = 7
eligible_with_score_gt_zero = up to 7
planner_eligible_count = up to 7
```

However, S8X does not recommend auto-resolving all 7. Several require A2 grammar from A1 opportunities, so `higher_level_requires_unknown` or manual review is safer for V1.

## 11. Impact on Antigravity Planner

S10E does not need an immediate integration fix.

Current S10H result:

```text
planner_failure = false
signal_failure = false
primary_cause = UPSTREAM_DEPENDENCY_READINESS_GAP
```

Recommended flow after S8Y:

```text
build dependency_readiness_resolution.json
rebuild learning opportunities or overlay dependency resolution
rebuild S10G reinforcement_signal.json
rerun S10H planner reinforcement audit
only then consider S10E integration changes
```

Planner behavior should remain fail-closed until S8Y proves eligible reinforcement candidates exist.

## 12. QA / Audit Plan

S8Y should include a focused QA report with:

- `unknown_before`
- `unknown_after`
- `resolved_ready_count`
- `resolved_blocked_count`
- `still_unknown_count`
- `false_ready_guard_count`
- `missing_ref_blocked_count`
- `higher_level_requires_unknown_count`
- `reinforcement_eligible_before`
- `reinforcement_eligible_after`
- `planner_reaudit_status`

Required QA checks:

- every resolution target exists in `learning_opportunities.json`
- every required node ref resolves or is blocked
- no `blocked` opportunity becomes ready
- no theme-only readiness promotion
- no CEFR-only readiness promotion
- no opportunity with higher-level hard requires is auto-ready without review evidence
- summary counts match resolution records
- S10G rebuild after resolution is deterministic
- S10H re-audit reports no selected ineligible reinforcement

## 13. Risks and Mitigations

### False ready

Risk:

- dependency `unknown` is converted to `ready` just to unblock reinforcement.

Mitigation:

- require explicit resolution types and evidence fields.
- keep higher-level requires as unknown unless reviewed.

### Hidden missing refs

Risk:

- dangling node refs become ready by default.

Mitigation:

- `missing_ref_blocked` rule.
- validator must resolve every required node.

### CEFR misuse

Risk:

- A1/A2 order is treated as dependency proof.

Mitigation:

- CEFR may only cap or warn; it cannot create readiness alone.

### Theme overreach

Risk:

- theme continuity is used to satisfy dependency readiness.

Mitigation:

- theme refs are context evidence only.

### Planner pressure

Risk:

- S10E/S10G needs a reinforcement block, so upstream dependency gets weakened.

Mitigation:

- S8Y emits independent resolution artifact and S10H audits planner consumption afterward.

### Higher-level requires in current inventory

Risk:

- several A1 opportunities require A2 grammar nodes.

Mitigation:

- default to `higher_level_requires_unknown` or manual review.

## 14. Recommended Repair Path

Recommended next task:

```text
ULGA-S8Y_DependencyReadinessResolution_Implementation
```

S8Y should:

1. Build `dependency_readiness_resolution.json`.
2. Classify all opportunity dependency statuses.
3. Preserve current `unknown` where evidence is insufficient.
4. Block dangling refs.
5. Only resolve ready with explicit evidence.
6. Emit a summary report.
7. Add validator and tests.
8. Rebuild S10G.
9. Rerun S10H.

Alternative intermediate task:

```text
ULGA-S8X1_DependencyUnknownEvidenceAudit
```

Use this if manual review wants a deeper per-edge evidence table before implementation.

## 15. Final Verdict

S8X is design-ready.

The current readiness gap is not caused by S10E planner behavior or S10G signal materialization.

It is caused by a conservative S10B dependency status rule:

```text
explicit requires exist -> dependency.status = unknown
```

That rule is safe, but incomplete. A new Dependency Readiness Resolution Authority is needed to distinguish:

- no-requires ready
- content-contained ready
- same/lower-level ready with evidence
- higher-level unknown
- missing-ref blocked
- manual-review unknown

```text
S8X_STATUS: DESIGN_READY
```

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S8X_DEPENDENCY_READINESS_RESOLUTION_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- `dependency_graph.json`
- `learning_opportunities.json`
- `ranked_learning_opportunities.json`
- `reinforcement_signal.json`
- `antigravity_plan.json`
- S10G/S10H reports
- S8A/S8D/S10F/S10G/S10H docs
- S10B learning opportunity builder

Unknown Inventory Count:

- 7 unknown-positive reinforcement opportunities

Root Cause Summary:

```text
CONSERVATIVE_UNKNOWN_POLICY
```

Impact on S10G/S10H:

- S10G positive reinforcement signals remain ineligible.
- S10H correctly reports upstream dependency readiness gap.
- S10E is not currently a planner failure.

Final Verdict:

```text
S8X_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
ULGA-S8Y_DependencyReadinessResolution_Implementation
```
