# ULGA-S9Z Exposure Coverage Expansion Design Scan

## 1. Scope

This design scan investigates why Learner Exposure Evidence coverage remains too narrow after S9Y and why S10J1 still produces no planner-eligible reinforcement candidates.

Scope is design only.

S9Z does not modify:

- `ulga/graph/*`
- `ulga/builders/*`
- `ulga/validators/*`
- `ulga/reports/*`
- `ulga/schema/*`
- `ulga/learner_state/*`
- `tests/*`

Current status:

```text
S9Y_STATUS: PASS
S10J1_STATUS: PASS_WITH_WARNINGS
```

Core question:

```text
Why is Learner Exposure Evidence coverage only 0.001488, and what bridge layer is needed to expand coverage without creating false planner eligibility?
```

## 2. Inputs Reviewed

Read-only inputs reviewed:

- `ulga/learner_state/learner_state.json`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/reports/dependency_readiness_resolution_summary.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/reading_stub_authority.json`
- `docs/ulga/ULGA_S9X_LEARNER_EXPOSURE_EVIDENCE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10J1_CANDIDATE_EXPANSION_REBUILD_WITH_EXPOSURE_EVIDENCE.md`

Missing optional inputs:

```text
None required for design scan.
```

## 3. Current Coverage Gap

Current counts:

```text
learner_state record count = 9
learning_opportunity count = 1344
exposure evidence count = 2
opportunity mapping count = 2
coverage rate = 0.001488
S10J1 candidate_count = 2
S10J1 planner_eligible_count = 0
```

Learner-state node type distribution:

| Node type | Count |
|---|---:|
| `assessment` | 1 |
| `chunk` | 1 |
| `dialogue` | 1 |
| `grammar` | 1 |
| `morphology` | 1 |
| `sentence_pattern` | 1 |
| `skill` | 1 |
| `theme` | 1 |
| `vocabulary` | 1 |

Current direct mapping inventory:

| Learner state record | Direct focus mapping | Theme mapping | Current result |
|---|---:|---:|---|
| `chunk:SAFE_CHUNK_000321` | 0 | 0 | unmapped |
| `dialogue:DIALOGUE_ORDERING_FOOD_A1_001` | 0 | 0 | unmapped |
| `vocabulary:VOCAB_NODE_004210` | 0 | 0 | unmapped |
| `assessment:SHORT_WRITING_CHECK_A2_001` | 0 | 0 | unmapped |
| `grammar:GRAMMAR_NODE_000123` | 0 | 0 | unmapped |
| `morphology:word_family_read` | 0 | 0 | unmapped |
| `sentence_pattern:PATTERN_NODE_000014` | 0 | 0 | unmapped under raw id |
| `skill:writing_revision` | 0 | 0 | unmapped |
| `theme:a1_daily_life_and_routines` | 0 | 2 | mapped |

Current mapped opportunities:

```text
LEE_000001 -> LO_A1_000011
LEE_000002 -> LO_A1_000012
```

Both mapped opportunities are:

```text
reading_ready = true
dependency_status = blocked
level_ceiling_passed = false
planner_eligible = false
```

Important bridge hint:

```text
sentence_pattern:PATTERN_NODE_000014 has no raw direct match,
but pattern:PATTERN_NODE_000014 maps to 1 opportunity.
```

This indicates a namespace bridge gap, not necessarily missing learning data.

## 4. Root Cause Classification

Classification:

| Root cause | Applies | Evidence |
|---|---|---|
| `LEARNER_STATE_TOO_SMALL` | Yes | Only 9 learner-state records for 1344 opportunities. |
| `NODE_TO_OPPORTUNITY_MAPPING_MISSING` | Yes | 8 of 9 learner-state records do not map to opportunities. |
| `THEME_ONLY_MAPPING_TOO_WEAK` | Yes | Current 2 evidence records are weak theme-only mappings. |
| `FOCUS_NODE_MISMATCH` | Yes | Learner `sentence_pattern:` id does not match opportunity `pattern:` id. |
| `MISSING_PATTERN_BRIDGE` | Yes | Pattern namespace normalization would unlock at least 1 direct opportunity mapping. |
| `MISSING_GRAMMAR_BRIDGE` | Yes | Grammar state exists but no current direct opportunity focus match. |
| `MISSING_VOCABULARY_BRIDGE` | Yes | Vocabulary state uses `VOCAB_NODE_*`, while opportunities use lexical ids such as `vocabulary:be:v_1427`. |
| `DEPENDENCY_BLOCKED_MAPPING` | Yes | Existing 2 mapped opportunities are blocked by S8Y dependency resolution. |
| `OTHER` | Yes | Dialogue, assessment, morphology, and skill records need event-derived bridge rules or future authority nodes. |

Primary root cause:

```text
The exposure authority currently has only direct focus and theme lookup. It lacks bridge logic across node namespaces, pattern aliases, vocabulary identity systems, grammar adjacency, chunk links, and event-derived opportunity exposure.
```

## 5. Mapping Bridge Design

Recommended bridge architecture:

```text
Learner State Node
-> Vocabulary / Grammar / Pattern / Theme / Chunk Bridge
-> Candidate Opportunity Set
-> Dependency and Reading Safety Overlay
-> Exposure Evidence V2
```

The bridge layer should be owned by Exposure Evidence Authority, not Candidate Expansion.

Reason:

```text
Candidate Expansion should consume canonical exposure decisions.
It should not infer exposure from learner-state internals or graph heuristics.
```

Recommended bridge record shape:

```json
{
  "bridge_id": "LEB_000001",
  "learner_id": "learner:james",
  "source_node_id": "sentence_pattern:PATTERN_NODE_000014",
  "source_node_type": "sentence_pattern",
  "bridge_type": "pattern_bridge",
  "target_opportunity_id": "LO_A1_000014",
  "bridge_confidence": 0.8,
  "guard_flags": []
}
```

## 6. Bridge Types

Recommended bridge types:

| Bridge type | Input | Output | Confidence | Notes |
|---|---|---|---|---|
| `direct_focus_node_bridge` | exact focus node match | opportunity | high | Current S9Y behavior for grammar/vocabulary when ids match. |
| `theme_bridge` | learner theme state | theme opportunities | low | Diagnostic only unless paired with a stronger bridge. |
| `pattern_bridge` | `sentence_pattern:*` or `pattern:*` | pattern-focused opportunities | medium/high | Must normalize namespace. |
| `grammar_bridge` | grammar node | opportunities sharing grammar focus or accepted dependency parent | medium | Must not infer mastery of child opportunity. |
| `vocabulary_bridge` | vocabulary node | lexical opportunity focus ids | medium | Requires vocabulary identity mapping from authority graph. |
| `chunk_bridge` | chunk node | chunk-focused opportunities or chunk-linked patterns | medium | Needs chunk id namespace normalization. |
| `dependency_parent_bridge` | exposed prerequisite | blocked or child opportunity candidates | high if exact prior exposure | Candidate may remain ineligible if child is blocked. |

First implementation should prioritize:

```text
pattern_bridge
vocabulary_bridge
grammar_bridge
```

Reason:

```text
They are most likely to convert existing learner-state evidence into opportunity-level exposure without relying on broad same-theme inference.
```

## 7. Expansion Policy

Exposure may be expanded when at least one of these is true:

- exact focus node match
- normalized pattern id match
- shared grammar focus or accepted grammar dependency parent
- shared vocabulary identity through an authority mapping
- chunk focus match or chunk-to-pattern bridge
- theme plus prior exposure to a concrete focus node
- dependency parent with explicit prior exposure

Exposure must not be expanded from:

- same theme only
- unseen related vocabulary
- future dependency child
- level-unsafe opportunity
- dependency-blocked opportunity as planner-eligible exposure
- planner structural fallback
- remediation recommendation alone

Recommended minimal policy:

```text
Generate exposure evidence for blocked opportunities when the bridge is real,
but set planner_eligible_for_reinforcement = false.
```

This preserves diagnostics without weakening planner safety.

## 8. Confidence Model

Recommended bridge confidence:

| Bridge type | Confidence band | Suggested score |
|---|---|---:|
| `direct_focus_node_bridge` | high | `0.85-1.00` |
| `pattern_bridge` | medium/high | `0.70-0.90` |
| `grammar_bridge` | medium | `0.55-0.75` |
| `vocabulary_bridge` | medium | `0.55-0.75` |
| `chunk_bridge` | medium | `0.55-0.75` |
| `theme_bridge` | low | `0.20-0.40` |
| `dependency_parent_bridge` | high if exact prior exposure | `0.75-0.95` |

Confidence should be capped by learner-state quality:

```text
single exposure_count = 1 caps confidence at medium unless the bridge is exact and source confidence is high.
theme-only bridge caps confidence at low.
manual evidence without strong provenance caps confidence at medium.
```

Current S9Y evidence is:

```text
weak theme-only evidence
score = 0.335
```

This is suitable for diagnostics, not planner eligibility.

## 9. Dependency Safety

Exposure expansion must never override `dependency_readiness_resolution.json`.

Current dependency summary:

```text
total_unknown_inputs = 7
resolved_ready_count = 0
resolved_blocked_count = 7
resolution_type_distribution = explicit_requires_level_blocked
reinforcement_positive_eligible_after = 0
```

Required rule:

```text
If resolved_dependency_status != ready, expanded exposure may be recorded,
but planner_eligible_for_reinforcement must be false.
```

Current blocked mappings:

```text
LO_A1_000011
LO_A1_000012
```

Both have:

```text
level_ceiling_passed = false
```

Therefore S9Z must recommend coverage expansion, not dependency bypass.

## 10. Reading Safety

Exposure expansion must check `reading_stub_authority`.

Current reading safety:

```text
delivery_ready linked opportunities = 1344
current mapped opportunities reading_ready = 2
```

Required rule:

```text
An expanded opportunity can only become planner eligible for reinforcement if a delivery-ready reading stub or equivalent deliverable exists.
```

Reading missing should produce:

```text
planner_eligible_for_reinforcement = false
warning = reading_missing
```

Reading readiness is necessary but not sufficient:

```text
LO_A1_000011 and LO_A1_000012 are reading-ready but still dependency-blocked.
```

## 11. Learner State Data Gap

The learner-state corpus is small:

```text
learner_state records = 9
learners = learner:cyndi, learner:james
```

This is not enough to create a broad reinforcement pool without bridge expansion or richer event ingestion.

Current state gaps:

- only one theme record maps directly
- pattern evidence has namespace mismatch
- vocabulary evidence uses a node id that does not match opportunity lexical refs
- grammar evidence does not currently overlap opportunity focus grammar
- chunk, dialogue, assessment, morphology, and skill records lack bridge rules

Recommended data-source direction:

- session-derived exposure logs for actual opportunity encounters
- assessment-derived events for targeted grammar, pattern, vocabulary, and writing evidence
- dialogue-derived exposure logs that include opportunity id or target refs
- reading-derived exposure logs that record which linked opportunity was delivered
- synthetic seed learner events only for tests and fixtures, not production truth

## 12. Future Learner Event Model

Recommended future artifact:

```text
ulga/learner_state/learner_event_log.json
```

Schema draft:

```json
{
  "event_id": "LE_000001",
  "learner_id": "learner:james",
  "event_type": "reading_seen",
  "opportunity_id": "LO_A1_HOME_000001",
  "target_refs": {
    "vocabulary": [],
    "grammar": [],
    "pattern": [],
    "theme": [],
    "chunk": []
  },
  "success": null,
  "timestamp": "2026-06-18T00:00:00Z",
  "source": {
    "authority_name": "LearnerEventLog",
    "producer": "reading_runtime"
  }
}
```

Event ingestion rules:

- `reading_seen` proves exposure to delivered reading-linked opportunity.
- `dialogue_seen` proves contextual exposure only when target refs are present.
- `quiz_attempt` can support success and exposure.
- `writing_attempt` can support pattern, grammar, vocabulary, and skill evidence.
- duplicate `event_id` must be idempotent.
- missing `opportunity_id` must fall back to target refs, not broad theme inference.

## 13. Expanded Exposure Authority Schema

Recommended future artifact:

```text
ulga/graph/learner_exposure_evidence_v2.json
```

Schema draft:

```json
{
  "metadata": {
    "source": "ULGA_S9Z1_EXPOSURE_MAPPING_BRIDGE",
    "contract_version": "ULGA-S9Z1",
    "generated_at": "2026-06-18T00:00:00Z"
  },
  "evidence": [
    {
      "evidence_id": "LEE2_000001",
      "learner_id": "learner:james",
      "target_type": "opportunity",
      "target_id": "LO_A1_HOME_000001",
      "bridge_type": "pattern_bridge",
      "exposure_score": 0.75,
      "confidence_band": "medium",
      "prior_exposure": true,
      "dependency_status": "ready",
      "reading_ready": true,
      "planner_eligible_for_reinforcement": true,
      "source_refs": [
        "sentence_pattern:PATTERN_NODE_000014"
      ],
      "warnings": []
    }
  ]
}
```

Compatibility note:

```text
S10J should continue consuming canonical exposure evidence,
not bridge internals. S9Z1 may either extend S9Y schema in place or emit v2 with a compatibility adapter.
```

## 14. QA / Audit Plan

Required metrics:

```text
coverage_before
coverage_after
mapping_count_by_bridge_type
high_confidence_count
medium_confidence_count
low_confidence_count
dependency_blocked_count
reading_missing_count
planner_eligible_exposure_count
false_expansion_guard_count
```

Required tests:

- deterministic bridge output
- no same-theme-only planner-eligible exposure
- pattern namespace bridge maps `sentence_pattern:*` to `pattern:*`
- vocabulary bridge requires authority-backed identity mapping
- grammar bridge does not bypass dependency readiness
- dependency-blocked mapped opportunities remain ineligible
- reading-missing mapped opportunities remain ineligible
- duplicate event or source refs do not inflate evidence
- empty learner-state input emits safe empty evidence

Recommended audit report:

```text
ulga/reports/exposure_mapping_bridge_summary.json
```

## 15. Safety Rules

Required safety rules:

```text
same-theme-only must not create planner-eligible exposure
dependency-blocked opportunity must not become eligible
level-unsafe opportunity must not become eligible
unseen related vocabulary must not become exposure
planner fallback must not create exposure
remediation recommendation must not create exposure
reading-missing opportunity must not become eligible
weak exposure must not override dependency, reading, or level gates
```

Real environment risks:

- API failure can create partial learner events without target refs.
- Timeout during bridge build must not leave partial evidence artifacts.
- Empty learner state must produce a valid empty report.
- Repeated execution must be idempotent.
- Process restart must produce stable evidence ids.
- Abnormal upstream response must not create broad false exposure.

## 16. Recommended Implementation Path

Recommended next task:

```text
ULGA-S9Z1_ExposureMappingBridge_Implementation
```

Scope:

```text
Implement bridge expansion inside Exposure Evidence Authority, beginning with pattern namespace bridging and safe summary metrics.
```

Minimal sequence:

1. Add bridge summary/audit fields without changing S10J first.
2. Implement `pattern_bridge` for `sentence_pattern:*` to `pattern:*`.
3. Add guarded `vocabulary_bridge` only when a trusted vocabulary identity mapping exists.
4. Add `grammar_bridge` only for exact focus or accepted dependency-parent exposure.
5. Keep same-theme-only evidence diagnostic.
6. Rebuild S10J only after S9Z1 validator passes.

Deferred task:

```text
ULGA-S9Z1_LearnerEventLog_DesignScan
```

Use this if bridge expansion remains too narrow because learner state lacks opportunity-level event provenance.

## 17. Final Verdict

S9Z conclusion:

```text
S9Z_STATUS: DESIGN_READY
```

Rationale:

```text
The pipeline is wired correctly through S9Y and S10J1, but exposure coverage is too narrow because the current authority lacks bridge logic across node namespaces and event-derived opportunity exposure.
```

S9Z is not blocked. The next repair should expand exposure mapping coverage while preserving dependency and reading safety.

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S9Z_EXPOSURE_COVERAGE_EXPANSION_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- `ulga/learner_state/learner_state.json`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/reports/dependency_readiness_resolution_summary.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/reading_stub_authority.json`
- related S9 and S10 documents

Coverage Gap Summary:

```text
learner_state_records = 9
learning_opportunities = 1344
exposure_evidence_count = 2
opportunity_mapping_count = 2
coverage_rate = 0.001488
planner_eligible_count = 0
```

Root Cause Classification:

```text
LEARNER_STATE_TOO_SMALL
NODE_TO_OPPORTUNITY_MAPPING_MISSING
THEME_ONLY_MAPPING_TOO_WEAK
FOCUS_NODE_MISMATCH
MISSING_PATTERN_BRIDGE
MISSING_GRAMMAR_BRIDGE
MISSING_VOCABULARY_BRIDGE
DEPENDENCY_BLOCKED_MAPPING
OTHER
```

Recommended Implementation Path:

```text
ULGA-S9Z1_ExposureMappingBridge_Implementation
```

Final Verdict:

```text
S9Z_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
ULGA-S9Z1_ExposureMappingBridge_Implementation
```
