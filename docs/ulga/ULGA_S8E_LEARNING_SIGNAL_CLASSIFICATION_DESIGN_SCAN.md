# ULGA-S8E Learning Signal Classification Design Scan

## Executive Summary

S8E defines a **Learning Signal Classification Framework** for ULGA. The core problem is that a knowledge edge is not automatically a learning decision. The same edge can support gating, recommendation, mastery evidence, review planning, coverage planning, context filtering, or diagnostics depending on relation type, confidence, authority source, and runtime consumer.

Current ULGA has enough evidence to define the framework:

- Dependency relations from S8A: `REQUIRES`, `EXPANDS`, `REINFORCES`, `PRECEDES`.
- Theme Spiral relations from S8B: `SPIRAL_TO`, `INTRODUCES`, `REINFORCES`, `BROADENS_TO`, `CONTRASTS_WITH`.
- Existing physical graph edges: `prerequisite`, `supports`, `reviews`, `contrasts_with`, `uses`, `belongs_to`.
- Pattern constraints already distinguish gate and ranking behavior: CEFR gates, theme filters, and frequency ranking signals.

Main conclusion:

```text
Only accepted REQUIRES / hard prerequisite evidence should produce GATE_SIGNAL by default.
Theme Spiral, belongs_to, supports, reviews, and most uses edges should not gate.
They become recommendation, mastery, review, coverage, context, or diagnostic signals.
```

Recommendation: **GO for a Learning Signal contract before S8C/S8F builders produce more graph artifacts.**

## Current ULGA Signal Inventory

### Evidence Inspected

- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8B_THEME_SPIRAL_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7E_PATTERN_THEME_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5D_VOCABULARY_THEME_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ulga_roadmap.md`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`
- `ulga/schema/ulga_graph_schema.json`
- `ulga/graph/grammar_dependency_all_edges.json`
- `ulga/graph/grammar_dependency_core_edges.json`
- `ulga/graph/grammar_dependency_extended_edges.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `ulga/graph/vocabulary_morphology_edges.json`
- `ulga/graph/chunk_vocabulary_edges.json`
- `ulga/graph/ulga_sentence_pattern_edges.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/chunk_grammar_metadata.json`
- `ulga/reports/grammar_dependency_extended_qa_audit.json`
- `ulga/reports/vocabulary_theme_refinement_summary.json`
- `ulga/reports/vocabulary_morphology_summary.json`
- `ulga/reports/chunk_vocabulary_linkage_summary.json`
- `ulga/reports/chunk_grammar_metadata_qa_audit.json`
- `ulga/reports/sentence_pattern_mount_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`

### Missing Evidence

No mounted Learning Signal Authority files exist yet. Specifically, no existing `learning_signal_contract.json`, signal graph, signal validator, Learner State Authority, Reading Authority, Dialogue Authority, Assessment Authority, or Antigravity Planner implementation was found in the inspected scope. These are treated as future consumers, not existing authorities.

### Existing Signal-Like Inventory

| Source | Count | Current relation or behavior | Signal implication |
|---|---:|---|---|
| Grammar dependency all | 493 | `84 prerequisite`, `362 supports`, `30 contrasts_with`, `17 reviews` | Gate, recommendation, review, diagnostic candidates |
| Vocabulary theme refined | 19,557 | `belongs_to` | Context and coverage signals |
| Vocabulary morphology | 9,122 | `supports` with morphology metadata | Recommendation and mastery expansion signals |
| Chunk vocabulary | 7,804 | `uses`; `6,032` low confidence fallback | Context/recommendation; limited gate only after review |
| Sentence pattern edges | 1,529 | `uses`, `belongs_to`, `prerequisite` | Composition, context, limited sequencing |
| Pattern vocabulary constraints | 1,344 records | CEFR gate, theme filter, frequency ranking | Query-time gate and recommendation signals |
| Chunk grammar metadata | 3,522 records | grammar signals, sparse prerequisites, review queue | Diagnostic/review candidates |

Known QA constraints:

- Grammar extended QA reports hard dependency DAG as acyclic and CEFR-not-order checks as true.
- Vocabulary theme refinement reduced `88,423` theme edges to `19,557`, with max theme edges per mapped vocabulary reduced to `3`.
- Chunk vocabulary linkage contains `6,032` low-confidence edges, so it must not become hard gating by default.
- Pattern vocabulary constraints intentionally avoid dense pattern-vocabulary edge materialization.

## Learning Signal Definition

A **Knowledge Edge** is an authority fact about two nodes or records. It says something like:

- this pattern uses this grammar;
- this vocabulary belongs to this theme;
- this grammar supports that grammar;
- this theme spirals to that theme;
- this node requires that node.

A **Learning Signal** is a consumer-facing interpretation of that knowledge edge for a learning decision. It answers:

- should access be blocked?
- should this be recommended next?
- does this count as mastery evidence?
- should this be reviewed?
- does this satisfy coverage?
- does this provide context?
- does this help diagnose confusion?

Therefore:

```text
Knowledge Edge != Learning Signal
```

One edge can become multiple signals:

- `REQUIRES`: `GATE_SIGNAL`, `MASTERY_SIGNAL`, `DIAGNOSTIC_SIGNAL`.
- `SPIRAL_TO`: `RECOMMENDATION_SIGNAL`, `COVERAGE_SIGNAL`, `REVIEW_SIGNAL`.
- `BELONGS_TO`: `CONTEXT_SIGNAL`, `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL`.
- `CONTRASTS_WITH`: `DIAGNOSTIC_SIGNAL`, `REVIEW_SIGNAL`, `RECOMMENDATION_SIGNAL`.

The conversion must consider:

- edge relation;
- source authority;
- confidence method and value;
- review status;
- node types;
- whether the consuming engine is a gate, planner, learner state model, assessment engine, or content generator.

## Signal Taxonomy

| Signal type | Semantic meaning | Planner usage | Learner state usage | Assessment usage | Recommendation usage |
|---|---|---|---|---|---|
| `GATE_SIGNAL` | Candidate should be blocked until a required condition is satisfied. | Exclude or defer candidate before ranking. | Compute readiness and prerequisite gaps. | Explain why assessment target is not yet valid. | Do not recommend blocked target except as prerequisite remediation. |
| `MASTERY_SIGNAL` | Evidence that practicing or succeeding on one node informs mastery of another. | Prefer tasks that improve weak mastery clusters. | Update mastery evidence, confidence, and decay/review needs. | Map assessment results to node-level mastery. | Recommend practice that strengthens weak concepts. |
| `RECOMMENDATION_SIGNAL` | Candidate is pedagogically useful, next, adjacent, or likely relevant. | Ranking boost. | Optional preference evidence, not readiness. | Suggest follow-up assessments. | Core recommendation input. |
| `REVIEW_SIGNAL` | Candidate should revisit, retrieve, contrast, or refresh prior material. | Insert spaced review and spiral review. | Trigger review due or decay handling. | Use as retention check. | Recommend review activities. |
| `COVERAGE_SIGNAL` | Candidate helps cover a theme, level, skill, pattern family, or curriculum scope. | Balance lesson plans and avoid overconcentration. | Track exposure breadth, not mastery by itself. | Ensure assessment blueprint coverage. | Recommend undercovered areas. |
| `CONTEXT_SIGNAL` | Candidate belongs to or fits a theme, scenario, slot, topic, or content context. | Filter or rank by target context. | Track exposure context, not prerequisite. | Build context-specific tasks. | Recommend content aligned to learner goal/theme. |
| `DIAGNOSTIC_SIGNAL` | Candidate helps identify confusion, contrast, error source, or prerequisite gap. | Select diagnostic tasks when confidence is low. | Explain weakness and likely confusion pairs. | Build contrastive or targeted assessment items. | Recommend remedial contrast/review. |

## Edge Mapping Matrix

| Edge / relation | Primary signals | Secondary signals | Gate eligible by default | Notes |
|---|---|---|---|---|
| `REQUIRES` | `GATE_SIGNAL`, `MASTERY_SIGNAL` | `DIAGNOSTIC_SIGNAL`, `RECOMMENDATION_SIGNAL` | Yes, if accepted and high confidence | Only true hard prerequisite relation. |
| `EXPANDS` | `RECOMMENDATION_SIGNAL`, `COVERAGE_SIGNAL` | `MASTERY_SIGNAL` | No | Useful for vocabulary morphology, grammar bridge, broader pattern scope. |
| `REINFORCES` | `REVIEW_SIGNAL`, `MASTERY_SIGNAL` | `RECOMMENDATION_SIGNAL`, `DIAGNOSTIC_SIGNAL` | No | Must not be treated as proof of mastery by itself. |
| `PRECEDES` | `RECOMMENDATION_SIGNAL` | `COVERAGE_SIGNAL`, `REVIEW_SIGNAL` | No | Sequencing hint, not prerequisite. |
| `SPIRAL_TO` | `COVERAGE_SIGNAL`, `REVIEW_SIGNAL`, `RECOMMENDATION_SIGNAL` | `CONTEXT_SIGNAL` | No | S8B: never blocks learner. |
| `INTRODUCES` | `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL` | `MASTERY_SIGNAL` as first exposure marker | No | Represents first exposure or new load. |
| `BROADENS_TO` | `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL` | `CONTEXT_SIGNAL`, `MASTERY_SIGNAL` | No | Breadth expansion, not readiness. |
| `CONTRASTS_WITH` | `DIAGNOSTIC_SIGNAL`, `REVIEW_SIGNAL` | `RECOMMENDATION_SIGNAL` | No | Helps confusion checks and contrastive practice. |
| `USES` | `CONTEXT_SIGNAL` | `MASTERY_SIGNAL`, `RECOMMENDATION_SIGNAL`; possible `GATE_SIGNAL` only after review | No | Composition edge. Do not convert all `uses` to requirements. |
| `BELONGS_TO` | `CONTEXT_SIGNAL`, `COVERAGE_SIGNAL` | `RECOMMENDATION_SIGNAL` | No | Theme membership/classification. |
| `supports` | `RECOMMENDATION_SIGNAL`, `MASTERY_SIGNAL` | `COVERAGE_SIGNAL` | No | Existing grammar/morphology physical edge. |
| `reviews` | `REVIEW_SIGNAL`, `MASTERY_SIGNAL` | `RECOMMENDATION_SIGNAL` | No | Review evidence, not blocker. |
| `prerequisite` | `GATE_SIGNAL`, `MASTERY_SIGNAL` if hard; otherwise `RECOMMENDATION_SIGNAL` | `DIAGNOSTIC_SIGNAL` | Conditional | Must inspect metadata such as `dependency_class = hard_prerequisite`. |

One-to-many examples:

- `prerequisite` + `hard_prerequisite` -> gate, mastery, diagnostic.
- `belongs_to` -> context, coverage, recommendation.
- `contrasts_with` -> diagnostic, review, recommendation.

Many-to-one examples:

- `REINFORCES`, `reviews`, `SPIRAL_TO`, `CONTRASTS_WITH` can all produce `REVIEW_SIGNAL`.
- `BELONGS_TO`, `SPIRAL_TO`, `INTRODUCES`, `BROADENS_TO` can all produce `COVERAGE_SIGNAL`.

## Signal Priority Model

Recommended priority order:

| Priority | Signal | Conflict behavior |
|---:|---|---|
| 1 | `GATE_SIGNAL` | Hard block or defer before ranking. Cannot be overridden by recommendation or coverage. |
| 2 | `DIAGNOSTIC_SIGNAL` | If a blocker or low confidence exists, diagnostic tasks outrank ordinary recommendations. |
| 3 | `MASTERY_SIGNAL` | Prefer tasks that repair weak mastery or confirm readiness. |
| 4 | `REVIEW_SIGNAL` | Insert review when mastery is stale, weak, or due. |
| 5 | `COVERAGE_SIGNAL` | Balance curriculum breadth after gate/mastery needs are satisfied. |
| 6 | `CONTEXT_SIGNAL` | Filter/rank by theme, scenario, dialogue context, or reading topic. |
| 7 | `RECOMMENDATION_SIGNAL` | General ranking boost after stronger constraints are applied. |

Planner conflict rules:

- A candidate with a blocking `GATE_SIGNAL` is not eligible for normal recommendation.
- A diagnostic recommendation can target the blocked prerequisite, not the blocked target.
- Coverage cannot override gate or mastery safety.
- Context should filter only inside allowed candidate pools.
- Recommendation weights must be capped so a large number of weak signals cannot override one valid gate.

## Learner State Integration

Future S9A Learner State Authority should consume signals as follows:

| Edge / relation | Learner state interpretation |
|---|---|
| `REQUIRES` | Readiness dependency; unmet source creates prerequisite gap for target. |
| `prerequisite` hard grammar edge | Same as `REQUIRES` if metadata confirms `hard_prerequisite`. |
| `EXPANDS` | Breadth or extension evidence; helps show progression within a concept family. |
| `supports` | Mastery support or related evidence; not readiness unless promoted by dependency contract. |
| `REINFORCES` | Mastery evidence and review history; should update confidence carefully. |
| `reviews` | Review event candidate and retention evidence. |
| `PRECEDES` | Sequencing preference only; may affect readiness confidence but not block. |
| `SPIRAL_TO` | Coverage and review evidence across theme stages. |
| `INTRODUCES` | First exposure marker; initializes learning state for a scope. |
| `BROADENS_TO` | Coverage breadth and complexity expansion. |
| `CONTRASTS_WITH` | Diagnostic confusion pair; assessment errors can update both nodes. |
| `USES` | Composition evidence; success on a pattern/chunk may partially inform grammar/vocabulary mastery. |
| `BELONGS_TO` | Context exposure tracking by theme or domain. |

S9A should not infer mastery from exposure alone. `COVERAGE_SIGNAL` and `CONTEXT_SIGNAL` can say the learner has seen material, but not that they have mastered it.

## Antigravity Planner Integration

Planner participation by signal:

| Planner output | Signals used |
|---|---|
| Candidate ranking | `RECOMMENDATION_SIGNAL`, `MASTERY_SIGNAL`, `REVIEW_SIGNAL`, `COVERAGE_SIGNAL`, `CONTEXT_SIGNAL`, `DIAGNOSTIC_SIGNAL` |
| Next lesson | `GATE_SIGNAL` first, then `MASTERY_SIGNAL`, `COVERAGE_SIGNAL`, `RECOMMENDATION_SIGNAL` |
| Next reading | `CONTEXT_SIGNAL`, `COVERAGE_SIGNAL`, `REVIEW_SIGNAL`, CEFR gate signals from constraints |
| Next dialogue | `CONTEXT_SIGNAL`, `RECOMMENDATION_SIGNAL`, `SPIRAL_TO`-derived review/coverage, pattern constraints |
| Next worksheet | `DIAGNOSTIC_SIGNAL`, `MASTERY_SIGNAL`, `REVIEW_SIGNAL`, `GATE_SIGNAL` remediation |

Recommended Planner Signal Weight bands:

| Weight band | Signal class | Suggested range |
|---|---|---|
| Blocking | `GATE_SIGNAL` | hard exclude; not numeric ranking |
| Critical | `DIAGNOSTIC_SIGNAL`, unmet prerequisite remediation | `0.80-1.00` |
| Strong | high-confidence `MASTERY_SIGNAL`, due `REVIEW_SIGNAL` | `0.60-0.85` |
| Medium | `COVERAGE_SIGNAL`, strong `CONTEXT_SIGNAL` | `0.35-0.65` |
| Light | weak recommendation or heuristic context | `0.10-0.35` |
| Ignored | low-confidence or manual-review-required signal | `0.00` until accepted |

## Content Authority Integration

### Reading Authority

Should consume:

- `GATE_SIGNAL`: avoid readings whose required grammar/pattern load is blocked.
- `CONTEXT_SIGNAL`: match reading topic/theme.
- `COVERAGE_SIGNAL`: ensure theme and vocabulary breadth.
- `REVIEW_SIGNAL`: include previously learned vocabulary/grammar in new passages.
- `MASTERY_SIGNAL`: choose texts that exercise weak but reachable nodes.

Should not consume:

- Theme spiral as hard prerequisite.
- Coverage as proof of readiness.

### Dialogue Authority

Should consume:

- `CONTEXT_SIGNAL`: scenario, role, theme, slot context.
- `RECOMMENDATION_SIGNAL`: choose next useful dialogue patterns.
- `REVIEW_SIGNAL`: reintroduce earlier chunks/patterns.
- `DIAGNOSTIC_SIGNAL`: contrast confusing forms in controlled dialogues.
- `GATE_SIGNAL`: avoid unreachable target structures unless the dialogue is remedial.

### Assessment Authority

Should consume:

- `GATE_SIGNAL`: define prerequisite gap checks.
- `MASTERY_SIGNAL`: map item success/failure to node mastery.
- `DIAGNOSTIC_SIGNAL`: build contrastive items and error explanations.
- `COVERAGE_SIGNAL`: blueprint assessment coverage.
- `CONTEXT_SIGNAL`: build theme-specific assessment forms.

Assessment should not treat `REINFORCES` or `SPIRAL_TO` as mastery proof without learner performance evidence.

## Confidence Model

| Confidence method | Gate eligibility | Planner weight | Mastery calculation |
|---|---|---|---|
| `authoritative` | Eligible if relation supports gating and review status is accepted. | Can receive full band weight. | Can contribute strongly, subject to learner evidence. |
| `derived` | Gate only if explicitly allowed by contract and audited. | Medium to strong depending on value and source. | Can contribute as supporting evidence. |
| `heuristic` | Not gate eligible. | Low to medium; cap recommended at `0.35`. | Weak evidence only; should not raise mastery alone. |
| `manual_review_required` | Not gate eligible. | `0.0` unless planner explicitly includes review queue tasks. | No mastery effect until reviewed. |

Recommended numeric policy:

- `gate_eligible = true` requires accepted review, relation allows gate, and confidence method is `authoritative` or audited `derived`.
- Planner weight must be capped by confidence method.
- Mastery weight must be lower than planner weight for exposure-only signals.
- Diagnostic weight may be high even when mastery weight is low, because weak/contrasting evidence can still guide assessment.

## Signal Contract Proposal

Proposed future file: `learning_signal_contract.json`. S8E does not create it.

```json
{
  "signal_id": "signal:grammar:requires:000001",
  "signal_type": "GATE_SIGNAL",
  "source_edge_id": "edge:grammar:example",
  "source_node_id": "grammar:GRAMMAR_NODE_000001",
  "target_node_id": "grammar:GRAMMAR_NODE_000002",
  "source_relation": "REQUIRES",
  "source_authority": {
    "authority_name": "DependencyAuthority",
    "source_file": "ulga/graph/grammar_dependency_all_edges.json",
    "derivation": "rule_based"
  },
  "confidence": {
    "value": 0.85,
    "method": "authoritative",
    "notes": []
  },
  "review_status": "accepted",
  "gate_eligible": true,
  "planner_weight": 0.0,
  "mastery_weight": 0.75,
  "review_weight": 0.0,
  "coverage_weight": 0.0,
  "context_weight": 0.0,
  "diagnostic_weight": 0.5,
  "consumer_policy": {
    "dependency_engine": "block_if_unmet",
    "learner_state": "readiness_dependency",
    "planner": "exclude_target_until_met",
    "assessment": "prerequisite_gap_check"
  },
  "notes": [
    "Gating only applies when source mastery is below threshold."
  ]
}
```

Minimal required fields:

```json
{
  "signal_id": "",
  "signal_type": "",
  "source_edge_id": "",
  "source_node_id": "",
  "target_node_id": "",
  "confidence": {},
  "gate_eligible": false,
  "planner_weight": 0.0,
  "mastery_weight": 0.0,
  "review_weight": 0.0,
  "coverage_weight": 0.0,
  "diagnostic_weight": 0.0
}
```

Recommended signal type enum:

```json
[
  "GATE_SIGNAL",
  "RECOMMENDATION_SIGNAL",
  "MASTERY_SIGNAL",
  "REVIEW_SIGNAL",
  "COVERAGE_SIGNAL",
  "CONTEXT_SIGNAL",
  "DIAGNOSTIC_SIGNAL"
]
```

## Validation Plan

Signal Validator rules:

- Schema validation: required fields, enum values, weight ranges, confidence structure.
- Invalid signal mapping: block `SPIRAL_TO -> GATE_SIGNAL`, `BELONGS_TO -> GATE_SIGNAL`, and unreviewed `USES -> GATE_SIGNAL`.
- Gate misuse: `gate_eligible = true` only allowed for accepted `GATE_SIGNAL` from valid hard dependency sources.
- Theme misuse: theme-derived signals cannot block learners; theme membership cannot become prerequisite.
- CEFR misuse: CEFR may constrain candidate level but cannot create `GATE_SIGNAL` by itself.
- Planner overweight: cap weights by signal type and confidence method; reject aggregate weak signals overriding gates.
- Signal duplication: detect duplicate `(signal_type, source_edge_id, source_node_id, target_node_id)` tuples.
- Conflicting signals: report candidates with both strong recommendation and hard gate, requiring planner to exclude or remediate.
- Circular gate chains: run cycle detection over gate-eligible `GATE_SIGNAL` edges only.
- Manual review queue: all heuristic gate attempts, low-confidence mastery claims, theme-to-gate mappings, and chunk fallback gate attempts.

## Risk Register

| Risk | Severity | Analysis | Mitigation |
|---|---|---|---|
| `REQUIRES` overused | High | If composition, theme, or sequencing edges become `REQUIRES`, planner will overblock. | Only accepted hard dependency sources produce gate signals. |
| Theme Spiral treated as prerequisite | High | S8B explicitly says `SPIRAL_TO` must not block learners. | Validator rejects theme spiral gate signals. |
| `REINFORCES` treated as mastery proof | High | Reinforcement indicates practice opportunity, not successful learner performance. | Use as mastery evidence only when paired with learner outcome data. |
| Coverage treated as readiness | High | Seeing a theme or covering a stage is not mastery. | Separate `COVERAGE_SIGNAL` from `MASTERY_SIGNAL` and `GATE_SIGNAL`. |
| Planner overdepends on one signal | Medium | Recommender may repeatedly chase theme, frequency, or review signals. | Use priority model, caps, diversity, and coverage balancing. |
| Low-confidence chunk anchors gate content | Medium | Chunk linkage has many low-confidence fallback edges. | Cap as context/recommendation only until reviewed. |
| Dense signal explosion | Medium | One edge can create many signals. | Generate only consumer-needed signals or derive at query time where possible. |
| Existing physical edge ambiguity | Medium | `supports` and `prerequisite` need metadata inspection. | Require relation-specific mapping rules and metadata checks. |

## Recommended Roadmap

Recommended reordered roadmap:

1. `ULGA-S8F LearningSignalContract`
2. `ULGA-S8G LearningSignal_QA_Audit`
3. `ULGA-S8C DependencyEdgeBuilder`
4. `ULGA-S8D DependencyAuthority_QA_Audit`
5. `ULGA-S8H ThemeSpiralEdgeBuilder` or keep prior `ULGA-S8F ThemeSpiralEdgeBuilder` only if task numbering is not fixed
6. `ULGA-S8I ThemeSpiralAuthority_QA_Audit` or keep prior `ULGA-S8G ThemeSpiralAuthority_QA_Audit`
7. `ULGA-S9A LearnerStateAuthority_DesignScan`

Rationale:

- Signal contract should precede builders so generated edges carry safe consumer semantics.
- QA should verify signal misuse before dependency and theme spiral edges are consumed by planner or learner state.
- Learner State should come after signal taxonomy because it needs stable definitions for readiness, mastery, review, coverage, context, and diagnostics.

## Go / No-Go Recommendation

Recommendation: **GO for S8F LearningSignalContract before additional builder work.**

No-go conditions for implementation:

- generating `GATE_SIGNAL` from `SPIRAL_TO`, `BELONGS_TO`, `reviews`, or unreviewed `uses`;
- using CEFR alone to create readiness or gate signals;
- treating coverage or context as mastery;
- allowing heuristic or manual-review-required signals to gate;
- allowing planner weights to override hard gates;
- building Learner State before signal semantics are stable.

Minimal safe next step:

- define `learning_signal_contract.json` as a contract proposal;
- map existing physical edges to signal candidates without mutating graph files;
- validate signal type, confidence, weight, and gate eligibility rules;
- keep builder output separate from existing graph/source files until QA passes.
