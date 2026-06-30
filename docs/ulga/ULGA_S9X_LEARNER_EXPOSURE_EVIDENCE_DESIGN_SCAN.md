# ULGA-S9X Learner Exposure Evidence Design Scan

## 1. Scope

This design scan reviews why S10J produced reinforcement candidates but no planner-eligible reinforcement candidates, and defines the missing exposure-evidence authority needed before rebuilding candidate expansion.

Scope is design only.

No builder, validator, graph artifact, learner-state artifact, report, API, scheduler, orchestrator, dashboard, strategy, or planner behavior is modified.

Current upstream status:

```text
S10J_STATUS: PASS_WITH_WARNINGS
candidate_count = 5
planner_eligible_count = 0
```

The scan question:

```text
Why can S10J discover reinforcement candidates but still fail to produce planner-eligible reinforcement candidates?
```

Working diagnosis:

```text
Candidate Expansion is not the primary failure.
Exposure Evidence is not yet explicit, canonical, or mapped at opportunity level.
```

## 2. Inputs Reviewed

Read-only artifacts reviewed:

- `ulga/learner_state/learner_state.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/graph/reinforcement_signal.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `ulga/reports/reinforcement_signal_summary.json`
- `docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9F_BLOCKER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10G_REINFORCEMENT_SIGNAL_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10H_PLANNER_REAUDIT_WITH_REINFORCEMENT_SIGNAL.md`
- `docs/ulga/ULGA_S10J_REINFORCEMENT_CANDIDATE_EXPANSION_IMPLEMENTATION.md`

Observed learner-state coverage:

```text
learner_state_records = 9
records_with_last_seen_at = 9
records_with_last_success_at = 3
records_with_review_due_at = 8
records_mapping_to_learning_opportunity_focus_nodes = 0
records_mapping_to_learning_opportunity_theme_refs = 1
```

The only current learner-state record that maps to learning opportunities is:

```text
theme:a1_daily_life_and_routines -> LO_A1_000011, LO_A1_000012
```

Both mapped opportunities are dependency-blocked under the current dependency-readiness overlay.

## 3. Exposure Definition

Recommended definitions:

| Term | Definition | Must not mean |
|---|---|---|
| Exposure | The learner encountered a target through a traceable event or derived mapping. | Success, mastery, or readiness. |
| Success | The learner produced or recognized the target correctly in an evidence-bearing context. | Generic exposure. |
| Mastery | A scored, confidence-aware estimate based on repeated or high-quality evidence. | One-time success or theme contact. |
| Review Due | A scheduling signal that the learner should revisit a target. | Proof that the target was successfully learned. |

Minimal rule:

```text
last_seen_at can support exposure.
last_success_at can support success evidence.
mastery_band can summarize state but cannot alone create exposure.
review_due_at can trigger review but cannot alone create exposure.
```

## 4. Exposure Evidence Sources

Current learner state exposes the following source fields:

- `last_seen_at`
- `last_success_at`
- `exposure_count`
- `correct_count`
- `incorrect_count`
- `mastery_band`
- `review_due_at`
- `confidence`
- `evidence_refs`

Recommended interpretation:

| Field | Exposure use | Risk |
|---|---|---|
| `last_seen_at` | Strongest direct prior-exposure indicator when paired with a valid node target. | Can be over-applied if node-to-opportunity mapping is loose. |
| `exposure_count` | Count signal for confidence and weak/medium/strong bands. | Duplicate ingestion can inflate exposure. |
| `last_success_at` | Success evidence, not required for weak exposure. | Treating success as required would miss failed-but-seen review needs. |
| `correct_count` / `incorrect_count` | Attempt outcome context. | Counts need idempotent source events. |
| `mastery_band` | Supports confidence and review priority. | Must not create exposure without event or seen evidence. |
| `review_due_at` | Review scheduling signal. | Must not create prior exposure by itself. |
| `evidence_refs` | Audit trail and duplicate guard input. | Missing refs reduce confidence. |

## 5. Evidence Confidence Model

Recommended confidence bands:

| Band | Minimum evidence | Planner meaning |
|---|---|---|
| `weak` | One valid exposure such as `last_seen_at` or `exposure_count = 1`. | May support review discovery, but should not bypass gates. |
| `medium` | Repeated exposure or one exposure with reliable source confidence. | Can support candidate expansion when dependencies and delivery are ready. |
| `strong` | `exposure_count >= 3` and `success_ratio >= 0.6`, or equivalent repeated successful evidence. | Can support high-confidence reinforcement ranking. |

Suggested first-pass score:

```text
exposure_score =
0.45 * seen_signal
+ 0.25 * attempt_depth
+ 0.20 * success_signal
+ 0.10 * source_confidence
```

Where:

```text
seen_signal = 1.0 if last_seen_at or exposure_count > 0 else 0.0
attempt_depth = min(exposure_count / 3, 1.0)
success_signal = min(success_ratio, 1.0)
source_confidence = learner_state.confidence.value when available
```

Band thresholds:

```text
0.00-0.34 = weak
0.35-0.69 = medium
0.70-1.00 = strong
```

Safety note:

```text
weak exposure is enough to say "seen before"; it is not enough to say "ready".
```

## 6. Opportunity Mapping Problem

Current S10J can map learner-state records to opportunities only when the learner-state node id appears directly in:

- `learning_opportunities[].focus_nodes`
- `learning_opportunities[].theme_refs`

Observed result:

```text
records_mapping_to_learning_opportunity_focus_nodes = 0
records_mapping_to_learning_opportunity_theme_refs = 1
```

This is the core mapping gap. Learner state may contain valid exposure, but the current opportunity surface does not have an authority that says:

```text
Learner State Node -> Learning Opportunity exposure evidence
```

Example:

```text
vocabulary node exposure does not automatically prove that every opportunity containing related vocabulary is exposed.
```

The missing layer must distinguish:

- direct focus-node exposure
- theme-level contextual exposure
- dependency-parent exposure
- pattern/chunk/vocabulary/grammar partial overlap
- false exposure caused by broad theme membership

## 7. Opportunity Exposure Model

Recommended derived artifact:

```text
ulga/graph/learner_exposure_evidence.json
```

Recommended unit of authority:

```text
one learner + one target + one evidence decision
```

Recommended target types:

- `opportunity`
- `node`
- `theme`
- `dependency_parent`

Recommended opportunity-level fields:

```json
{
  "evidence_id": "LEE_000001",
  "learner_id": "learner:james",
  "target_type": "opportunity",
  "target_id": "LO_A1_000011",
  "exposure_score": 0.0,
  "confidence_band": "weak",
  "evidence_sources": [],
  "prior_exposure": true,
  "generated_at": "2026-06-18T00:00:00Z"
}
```

Recommended source dimensions:

- grammar overlap
- vocabulary overlap
- pattern overlap
- theme overlap
- chunk overlap
- dependency-parent overlap
- direct event refs

Opportunity exposure should be conservative:

```text
opportunity_exposure_score must be derived from explicit overlap evidence.
theme-only exposure should be weak unless supported by focus-node or event evidence.
```

## 8. Reinforcement Eligibility

Recommended eligibility gates:

```text
prior_exposure == true
dependency_status == ready
reading_ready == true
level_safe == true
target_refs not empty
```

S10J currently satisfies:

```text
candidate_count = 5
reading_ready_count = 5
prior_exposure = true for all 5 candidates
```

S10J currently fails:

```text
dependency_ready_count = 0
planner_eligible_count = 0
```

Important distinction:

```text
Exposure Evidence can improve candidate discovery and confidence.
Exposure Evidence must not weaken dependency gates.
```

Therefore S9X does not recommend making dependency-blocked opportunities eligible. It recommends making exposure evidence explicit so S10J1 can discover dependency-ready reinforcement opportunities when such evidence exists.

## 9. Exposure Evidence Authority Schema

Recommended schema contract:

```json
{
  "metadata": {
    "source": "ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE",
    "contract_version": "ULGA-S9Y",
    "generated_at": "2026-06-18T00:00:00Z"
  },
  "evidence": [
    {
      "evidence_id": "LEE_000001",
      "learner_id": "learner:james",
      "target_type": "opportunity",
      "target_id": "LO_A1_000011",
      "exposure_score": 0.42,
      "confidence_band": "medium",
      "evidence_sources": [
        {
          "source_type": "learner_state",
          "source_ref": "theme:a1_daily_life_and_routines",
          "mapping_type": "theme_overlap",
          "weight": 0.35
        }
      ],
      "prior_exposure": true,
      "false_exposure_guard": false,
      "warnings": [],
      "generated_at": "2026-06-18T00:00:00Z"
    }
  ]
}
```

Required validation:

- `evidence_id` unique
- `learner_id` required
- `target_type` enum validation
- `target_id` exists for known targets
- `exposure_score` between `0.0` and `1.0`
- `confidence_band` in `weak|medium|strong`
- `prior_exposure` equals `exposure_score > 0`
- empty or missing learner state emits valid empty evidence, not failure
- duplicate event/evidence refs do not inflate score

## 10. Integration Path

Recommended minimal integration path:

```text
Learner State
-> Exposure Evidence Authority
-> Candidate Expansion
-> Reinforcement Signal
-> Planner
```

Ownership boundary:

| Layer | Owns | Must not own |
|---|---|---|
| Learner State | Per-node learner facts. | Opportunity-level exposure mapping. |
| Exposure Evidence Authority | Learner/node/opportunity exposure decisions. | Planner eligibility or lesson selection. |
| Candidate Expansion | Candidate pool materialization. | Exposure inference rules. |
| Reinforcement Signal | Score and reason-code materialization. | Dependency override. |
| Planner | Selection and session structure. | Canonical exposure truth. |

This avoids duplicating exposure rules inside S10J and S10G.

## 11. QA / Audit Plan

Recommended summary metrics:

```text
evidence_count
weak_count
medium_count
strong_count
opportunity_mapping_rate
candidate_generation_rate
planner_eligible_rate
false_exposure_guard_count
duplicate_source_ref_count
empty_learner_state_status
dependency_blocked_exposure_count
```

Recommended audit checks:

- evidence is deterministic across repeated runs
- missing learner state emits `PASS_WITH_WARNINGS`, not crash
- malformed timestamps are quarantined or warned
- theme-only mapping stays weak unless supported by focus evidence
- dependency-blocked exposure remains ineligible
- exposure records do not mutate learner state
- candidate expansion consumes exposure authority instead of recomputing exposure ad hoc

Real environment risks:

- API failure: partial ingestion could create learner-state records without evidence refs.
- Timeout: exposure rebuild must write atomically or be fully rebuildable.
- Empty data: cold-start learners should produce zero evidence with a warning.
- Repeated execution: duplicate evidence refs must not increase exposure score.
- Process restart: deterministic generated ids and stable sorting are required.
- Abnormal upstream response: null timestamps, missing confidence, or unknown node types must not create false exposure.

## 12. Safety Rules

Required safety rules:

```text
last_success_at alone does not create opportunity exposure.
mastery_band alone does not create opportunity exposure.
review_due_at alone does not create opportunity exposure.
theme exposure alone cannot strongly expose every opportunity in that theme.
dependency-blocked opportunities cannot become planner eligible because of exposure.
weak exposure cannot override reading readiness or level safety.
empty evidence must fail closed.
```

Additional guardrails:

- `target_refs_empty` must block planner eligibility.
- unsupported node types must be retained for diagnostics but excluded from strong exposure.
- source confidence must cap exposure confidence.
- manual evidence should default to conservative confidence unless provenance is strong.

## 13. Recommended Repair Path

Recommended next task:

```text
ULGA-S9Y_LearnerExposureEvidence_Implementation
```

Purpose:

```text
Create learner_exposure_evidence.json and a validator/report that materialize exposure evidence without modifying S10J.
```

Recommended following task:

```text
S10J1_CandidateExpansion_Rebuild_WithExposureEvidence
```

Purpose:

```text
Refactor candidate expansion to consume learner exposure evidence instead of locally inferring prior_exposure from learner_state fields.
```

Minimal-change sequence:

1. Add S9Y builder, validator, report, tests, and closeout.
2. Keep all current S10J output unchanged until S9Y passes.
3. Add S10J1 to consume S9Y exposure evidence.
4. Preserve dependency/readiness fail-closed behavior.

## 14. Final Verdict

S9X conclusion:

```text
S9X_STATUS: DESIGN_READY
```

Root cause:

```text
The current system has learner-state exposure fields, but no canonical Exposure Evidence Authority that maps learner state to opportunity-level prior exposure with confidence and false-exposure guards.
```

S10J is not blocked by implementation failure. It is correctly fail-closing because current candidates are dependency-blocked and the available learner exposure maps only to theme-level opportunities.

S9X should proceed to implementation as S9Y.

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S9X_LEARNER_EXPOSURE_EVIDENCE_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- `ulga/learner_state/learner_state.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/graph/reinforcement_signal.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `ulga/reports/reinforcement_signal_summary.json`
- related S9 and S10 ULGA documents

Exposure Definition Chosen:

```text
Exposure means traceable learner encounter evidence. It is separate from success, mastery, review due, dependency readiness, and planner eligibility.
```

Root Cause Analysis:

```text
Current learner-state records do not map directly to opportunity focus nodes, and only one theme record maps to opportunities. Those opportunities are dependency-blocked. Candidate Expansion therefore finds diagnostic candidates but no planner-eligible reinforcement candidates.
```

Exposure Authority Proposal:

```text
Add learner_exposure_evidence.json as the canonical bridge from Learner State to opportunity-level exposure decisions.
```

Final Verdict:

```text
S9X_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
ULGA-S9Y_LearnerExposureEvidence_Implementation
```
