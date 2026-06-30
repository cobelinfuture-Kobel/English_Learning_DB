# ULGA-S8F Learning Signal Contract Closeout

## Files Created

- `ulga/schema/learning_signal_contract.schema.json`
- `ulga/schema/learning_signal_policy.json`
- `docs/ulga/ULGA_S8F_LEARNING_SIGNAL_CONTRACT_CLOSEOUT.md`

## Files Modified

- None.

No existing graph, source, data JSON, builder, validator, or ULGA-S2 schema files were modified.

## Contract Summary

S8F converts the S8E Learning Signal Classification design into a concrete contract and policy artifact.

The contract preserves the core S8E rule:

```text
Knowledge Edge != Learning Signal
```

`learning_signal_contract.schema.json` defines the required policy top-level sections:

- `contract_metadata`
- `signal_types`
- `signal_mapping_rules`
- `signal_weight_policy`
- `validation_policy`
- `consumer_policy`

It also defines the canonical future signal record fields:

- `signal_id`
- `signal_type`
- `source_edge_id`
- `source_relation`
- `source_node_id`
- `target_node_id`
- `source_authority`
- `confidence`
- `review_status`
- `gate_eligible`
- `planner_weight`
- `mastery_weight`
- `review_weight`
- `coverage_weight`
- `context_weight`
- `diagnostic_weight`
- `consumer_policy`
- `notes`

## Gate Policy Summary

Only `GATE_SIGNAL` can gate.

`gate_eligible=true` is allowed only when:

- `signal_type=GATE_SIGNAL`
- `source_relation=REQUIRES`, or `source_relation=prerequisite` with hard-prerequisite metadata or policy-accepted equivalent
- `review_status=accepted`
- `confidence.method` is `authoritative` or `derived`

The following relations are explicitly non-gating:

- `EXPANDS`
- `REINFORCES`
- `PRECEDES`
- `SPIRAL_TO`
- `INTRODUCES`
- `BROADENS_TO`
- `CONTRASTS_WITH`
- `USES`
- `BELONGS_TO`
- `supports`
- `reviews`
- `contrasts_with`

`heuristic` and `manual_review_required` signals cannot gate.

## Weight Policy Summary

Weight ranges are encoded in `learning_signal_policy.json`:

| Signal | Weight policy |
|---|---|
| `GATE_SIGNAL` | Blocking, not numeric planner ranking |
| `DIAGNOSTIC_SIGNAL` | `0.80-1.00` |
| `MASTERY_SIGNAL` | `0.60-0.85` |
| `REVIEW_SIGNAL` | `0.50-0.80` |
| `COVERAGE_SIGNAL` | `0.35-0.65` |
| `CONTEXT_SIGNAL` | `0.20-0.60` |
| `RECOMMENDATION_SIGNAL` | `0.10-0.75` |

Confidence caps:

| Confidence method | Max weight |
|---|---:|
| `authoritative` | `1.00` |
| `derived` | `0.75` |
| `heuristic` | `0.35` |
| `manual_review_required` | `0.00` |

Weak signal stacks cannot override a gate.

## Mapping Policy Summary

S8F encodes the S8E edge-to-signal matrix:

| Source relation | Default signal mapping |
|---|---|
| `REQUIRES` | `GATE_SIGNAL`, `MASTERY_SIGNAL`, `DIAGNOSTIC_SIGNAL` |
| `EXPANDS` | `RECOMMENDATION_SIGNAL`, `COVERAGE_SIGNAL` |
| `REINFORCES` | `REVIEW_SIGNAL`, `MASTERY_SIGNAL`, `RECOMMENDATION_SIGNAL` |
| `PRECEDES` | `RECOMMENDATION_SIGNAL`, `COVERAGE_SIGNAL` |
| `SPIRAL_TO` | `COVERAGE_SIGNAL`, `REVIEW_SIGNAL`, `RECOMMENDATION_SIGNAL` |
| `INTRODUCES` | `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL` |
| `BROADENS_TO` | `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL`, `CONTEXT_SIGNAL` |
| `CONTRASTS_WITH` | `DIAGNOSTIC_SIGNAL`, `REVIEW_SIGNAL` |
| `USES` | `CONTEXT_SIGNAL`, `RECOMMENDATION_SIGNAL` |
| `BELONGS_TO` | `CONTEXT_SIGNAL`, `COVERAGE_SIGNAL` |
| `supports` | `RECOMMENDATION_SIGNAL`, `MASTERY_SIGNAL` |
| `reviews` | `REVIEW_SIGNAL`, `MASTERY_SIGNAL` |
| `prerequisite` | conditional; defaults to non-gating mastery/diagnostic unless hard prerequisite metadata is accepted |
| `contrasts_with` | `DIAGNOSTIC_SIGNAL`, `REVIEW_SIGNAL` |

## Consumer Policy Summary

The policy defines consumers for:

- `dependency_engine`
- `learner_state`
- `antigravity_planner`
- `reading_authority`
- `dialogue_authority`
- `assessment_authority`

Key consumer decisions:

- Dependency engine consumes hard gate and diagnostic signals only.
- Learner state consumes mastery, review, coverage, context, and diagnostic signals, but coverage/context do not prove mastery.
- Antigravity Planner applies gate exclusions before ranking.
- Reading and Dialogue authorities consume context, coverage, review, mastery, diagnostic, and gate signals according to content type.
- Assessment Authority maps learner performance to mastery; static signals alone are not performance evidence.

## Validation Policy Summary

The policy specifies future validator checks:

- `schema_required_fields`
- `enum_validation`
- `invalid_gate_mapping`
- `gate_confidence_validation`
- `theme_gate_misuse`
- `cefr_gate_misuse`
- `weight_range_validation`
- `confidence_cap_validation`
- `duplicate_signal_detection`
- `conflicting_signal_detection`
- `circular_gate_chain_detection`
- `manual_review_queue_validation`

No validator was implemented in S8F.

## Compatibility Notes

- Existing `ulga/schema/ulga_edge_schema.json` was not modified.
- Existing graph files were not modified.
- `learning_signal_contract.schema.json` is a separate contract schema for future Learning Signal policy and signal records.
- `learning_signal_policy.json` is a policy artifact, not a graph.
- No `learning_signal_graph.json` was created.
- Existing physical edge names such as `supports`, `reviews`, `prerequisite`, and `contrasts_with` remain supported as source relations.
- Logical S8A/S8B relations such as `REQUIRES`, `SPIRAL_TO`, and `BROADENS_TO` are supported without requiring ULGA-S2 schema changes.

## Risk Controls

Controls encoded in the contract:

- Theme Spiral cannot gate.
- `BELONGS_TO`, `supports`, `reviews`, `USES`, and contrast relations cannot gate by default.
- CEFR-only evidence cannot create a gate signal.
- Heuristic and manual-review-required signals cannot gate.
- Gate signals are blocking semantics, not numeric planner ranking.
- Weak signal aggregation cannot override a valid gate.
- Physical `prerequisite` requires hard-prerequisite metadata or accepted policy equivalent before gate eligibility.

## Recommended Next Task

Recommended next task:

`ULGA-S8G_LearningSignal_QA_Audit`

Rationale:

- The contract and policy now exist.
- The next safe step is to audit schema validity, policy completeness, mapping coverage, and gate misuse before any DependencyEdgeBuilder, ThemeSpiralEdgeBuilder, LearnerState, or Planner consumes these signals.
