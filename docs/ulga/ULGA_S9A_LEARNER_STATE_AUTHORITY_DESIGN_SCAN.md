# ULGA-S9A Learner State Authority Design Scan

## Executive Summary

Learner State Authority is the ULGA authority layer that records and computes what a specific learner has actually encountered and demonstrated over time at node level. It should answer questions such as:

- has the learner seen this node before;
- has the learner practiced it successfully;
- is mastery partial, functional, or automatic;
- has mastery decayed enough that review is due;
- what evidence supports the current state.

Learner State Authority is not the same as planner logic.

- Authority stores stable learner truth and derived learner-state metrics.
- Planner logic consumes authority outputs plus dependency, theme spiral, candidate query, and policy rules to decide what to do next.
- A planner may change ranking policy without changing learner-state truth.
- A learner-state record must remain valid across scheduler retries, process restarts, planner revisions, and future reading/dialogue/assessment consumers.

Learner State Authority must exist before S9B Candidate Ranking because S9B needs a canonical state source for:

- `learner_mastery_gap` ranking;
- review due ranking;
- prerequisite readiness checks;
- theme spiral revisit readiness;
- confidence-aware handling of weak or stale evidence.

Without S9A, S9B would either duplicate state logic inside ranking code or overfit to static authority edges, which would blur the S9A/S9B/S9C boundary and create maintenance risk.

## Current Architecture Scan

### Evidence Inspected

- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_graph_schema.json`
- `ulga/schema/learning_signal_contract.schema.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/graph/grammar_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/chunk_nodes.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/chunk_grammar_metadata.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/reports/dependency_graph_summary.json`
- `ulga/reports/dependency_graph_qa_audit.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/theme_spiral_graph_qa_audit.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `ulga/reports/ulga_sentence_pattern_qa_audit.json`
- `docs/ulga/ULGA_S7A_SENTENCE_PATTERN_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7E_PATTERN_THEME_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8B_THEME_SPIRAL_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8E_LEARNING_SIGNAL_CLASSIFICATION_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8F_LEARNING_SIGNAL_CONTRACT_CLOSEOUT.md`
- `docs/ulga/ULGA_S8G_LEARNING_SIGNAL_QA_AUDIT.md`
- `tests/ulga/test_dependency_graph.py`
- `tests/ulga/test_theme_spiral_graph.py`
- `tests/ulga/test_pattern_vocabulary_constraints.py`

### Existing ULGA Node Types

Current mounted node types:

| Node type | Current count | Notes |
|---|---:|---|
| `grammar` | 1,222 | Structural rule authority; already linked into dependency graph. |
| `vocabulary` | 15,696 | Largest authority surface; strong candidate for learner-state tracking. |
| `chunk` | 3,522 | Exposure-heavy and likely important for fluency evidence. |
| `theme` | 25 | Mounted stage-bearing theme nodes. |
| `sentence_pattern` | 1,482 | Production-oriented authority; key bridge to speaking/writing readiness. |

Schema-allowed but not yet mounted for S9A scope:

| Node type | Mounted now | S9A relevance |
|---|---:|---|
| `learner_state` | no | Schema already anticipates this runtime authority. |
| `assessment` | no | Future evidence producer and consumer. |
| `skill` | no | May later aggregate cross-node ability. |
| `exercise_type` | no | Could tag evidence source but is not a mastery target. |

### Node Types Requiring Learner-State Tracking

Required in first-pass S9A:

- `grammar`
- `vocabulary`
- `chunk`
- `sentence_pattern`
- `theme`
- `morphology` as derived node-family state over vocabulary-linked evidence, even though morphology is currently represented through edges rather than a separate mounted node type

Required in future expansion:

- reading nodes
- dialogue nodes
- assessment nodes
- speaking-task nodes
- writing-task nodes
- listening-task nodes

Rationale:

- Vocabulary and grammar are the most obvious per-node mastery targets.
- Chunks and sentence patterns are necessary because learner performance often appears first as formulaic use, not isolated rule recall.
- Theme needs learner-state tracking for spiral readiness and coverage history, but theme exposure must not be treated as direct mastery proof.
- Morphology is needed because successful handling of `derived_from`, `has_suffix`, `has_prefix`, `compound_of`, and `shares_root` relations can support family-level readiness and error diagnosis.

### Existing Graph and Query Outputs S9A Can Consume

Directly consumable today:

| Artifact | Current count | S9A use |
|---|---:|---|
| `ulga/graph/dependency_graph.json` | 84 `REQUIRES` edges | readiness gaps, blocked targets, prerequisite evidence routing |
| `ulga/graph/theme_spiral_graph.json` | 21 theme stage nodes, 12 `SPIRAL_TO` edges | spiral review and stage-readiness sequencing |
| `ulga/graph/pattern_vocabulary_constraints.json` | 1,344 active constraint records | pattern practice evidence attribution and vocabulary-slot success mapping |
| `ulga/graph/pattern_vocabulary_candidate_query_contract.json` | 1 contract | defines ranking inputs including `learner_mastery_gap` |
| `ulga/graph/chunk_grammar_metadata.json` | 3,522 records | chunk-to-grammar attribution, pattern seeds, diagnostic evidence |
| `ulga/graph/sentence_patterns.json` | 1,482 nodes | pattern family, grammar refs, theme refs, slot constraints |
| `ulga/schema/learning_signal_policy.json` | 1 policy | tells S9A which relations behave as mastery, review, coverage, context, or diagnostic signals |

Indirect but important supporting sources:

- sentence pattern `grammar_refs`, `chunk_refs`, `theme_refs`, and `vocabulary_slot_constraints`
- dependency `gate_eligible`, `review_status`, `confidence`, and `dependency_class`
- theme spiral `review_status`, `source_cefr`, `target_cefr`, and stage-gap review queue behavior
- candidate query ranking signals: `theme_match`, `frequency_band`, `learner_mastery_gap`, `recency`, `diversity`

### Current Architecture Implications

1. S8 already established that `Knowledge Edge != Learning Signal`. S9A should consume learning-signal semantics, not reinterpret raw edge names ad hoc.
2. Candidate ranking already expects `learner_mastery_gap`, but no canonical learner-state artifact exists yet. This is a real architecture gap.
3. Current graph contracts are mostly authority-truth artifacts, not per-learner runtime truth. S9A should remain a separate data product, not a mutation of static graph files.

## Proposed Learner State Schema

Recommended canonical file shape:

```json
{
  "contract_metadata": {
    "contract_id": "ulga.learner_state",
    "contract_version": "ULGA-S9A",
    "schema_version": "1.0.0",
    "purpose": "Canonical per-learner node mastery and review state.",
    "state_is_authority_not_planner_output": true
  },
  "learner_state_records": [
    {
      "learner_id": "learner:james",
      "node_id": "grammar:GRAMMAR_NODE_000123",
      "node_type": "grammar",
      "mastery_score": 0.58,
      "mastery_band": "practicing",
      "exposure_count": 7,
      "correct_count": 4,
      "incorrect_count": 3,
      "last_seen_at": "2026-06-17T10:45:00Z",
      "last_success_at": "2026-06-16T09:10:00Z",
      "evidence_refs": [
        "event:worksheet_20260616_001",
        "event:quiz_20260617_002"
      ],
      "decay_adjusted_score": 0.52,
      "review_due_at": "2026-06-20T00:00:00Z",
      "confidence": {
        "value": 0.71,
        "method": "derived",
        "notes": [
          "Mixed worksheet and quiz evidence",
          "Recent incorrect evidence lowered confidence"
        ]
      },
      "source": {
        "authority_name": "LearnerStateAuthority",
        "derivation": "learner_runtime",
        "aggregation_version": "ULGA-S9A.v1"
      }
    }
  ]
}
```

Recommended record fields:

| Field | Meaning |
|---|---|
| `learner_id` | Stable learner key. Must support multiple learners. |
| `node_id` | ULGA authority node identifier. |
| `node_type` | Canonical node type for routing and validation. |
| `mastery_score` | Raw mastery estimate before decay adjustment. |
| `mastery_band` | Planner-friendly band label. |
| `exposure_count` | Total learner exposures mapped to this node. |
| `correct_count` | Evidence-weighted successful outcomes. |
| `incorrect_count` | Evidence-weighted failed outcomes. |
| `last_seen_at` | Most recent mapped exposure timestamp. |
| `last_success_at` | Most recent successful evidence timestamp. |
| `evidence_refs` | References to source evidence events. |
| `decay_adjusted_score` | Computed current score after retention decay. |
| `review_due_at` | Computed review timestamp, not user-authored planner output. |
| `confidence` | Confidence in the learner-state estimate, not confidence of the original static node. |
| `source` | Authority provenance and aggregation version. |

Recommended additional minimal fields for robustness:

- `first_seen_at`
- `last_attempt_at`
- `success_rate`
- `streak_current`
- `streak_best`
- `manual_override`
- `state_updated_at`
- `processing_idempotency_key`

Why these extras matter:

- repeated execution and process restart safety improve with `processing_idempotency_key`
- manual parent/teacher corrections need explicit override tracking
- empty-data and cold-start handling is clearer with `first_seen_at` and `state_updated_at`

## Mastery Bands

Recommended first-pass bands:

| Band | Score range | Planner interpretation |
|---|---:|---|
| `unknown` | `0.00-0.09` | No usable evidence. Eligible for introduction if not blocked by dependencies. |
| `seen` | `0.10-0.24` | Learner has encountered the node but cannot be assumed to use it reliably. Good for light review or contextual revisit. |
| `practicing` | `0.25-0.49` | Evidence exists but correctness or stability is weak. Prefer targeted practice and diagnostic follow-up. |
| `functional` | `0.50-0.69` | Learner can often use or recognize the node in constrained contexts. Candidate ranking may allow adjacent expansion. |
| `mastered` | `0.70-0.89` | Strong evidence across time and task types. Slower review cadence. Can support downstream readiness. |
| `automatic` | `0.90-1.00` | Highly stable retrieval or production. Mostly maintenance review unless decay or transfer failure appears. |

Interpretation rules:

- `mastery_band` is a planner-facing summary, not the only source of truth.
- Planner should prefer `decay_adjusted_score` over raw `mastery_score`.
- `coverage` or `context` evidence alone cannot move a learner above `seen`.
- `automatic` should require repeated success over time, not one high quiz score.

## Evidence Event Model

Recommended canonical event schema:

```json
{
  "event_id": "event:quiz_20260617_002",
  "learner_id": "learner:james",
  "node_refs": [
    {
      "node_id": "grammar:GRAMMAR_NODE_000123",
      "node_type": "grammar",
      "role": "primary_target",
      "weight": 1.0
    },
    {
      "node_id": "sentence_pattern:PATTERN_NODE_000014",
      "node_type": "sentence_pattern",
      "role": "supporting_context",
      "weight": 0.4
    }
  ],
  "event_type": "quiz",
  "score": 0.8,
  "attempt_count": 1,
  "response_time": 12.4,
  "error_type": "tense_confusion",
  "timestamp": "2026-06-17T10:45:00Z",
  "confidence": {
    "value": 0.9,
    "method": "authoritative"
  }
}
```

Event producers in scope:

- worksheet
- quiz
- reading
- dialogue
- speaking
- writing
- listening
- manual parent input
- manual teacher input

Recommended update behavior by event type:

| Event type | Typical update strength | Notes |
|---|---|---|
| `worksheet` | medium | Good for repeated structured practice; may overstate recognition-based mastery. |
| `quiz` | medium to high | Useful but must not dominate everything. |
| `reading` | low to medium | Strong for exposure and recognition; weak for production mastery. |
| `dialogue` | medium to high | Better evidence for contextual retrieval and fluency. |
| `speaking` | high if confidence is strong | Reliability depends on scoring quality and transcription quality. |
| `writing` | high if reviewed or auto-scored reliably | Useful for pattern and grammar production. |
| `listening` | low to medium | Stronger for comprehension than production. |
| `manual parent input` | low by default | Should update confidence conservatively and require provenance. |
| `manual teacher input` | medium to high | Can override or annotate state when evidence is sparse or ambiguous. |

Recommended event model rules:

1. One event may update multiple nodes with different weights.
2. `node_refs` must distinguish `primary_target` from `supporting_context`.
3. `response_time` should influence automaticity more than basic correctness.
4. `error_type` should support diagnostic routing, not just score reduction.
5. Duplicate event ingestion must be prevented with stable `event_id`.

## Aggregation Model

S9A needs explicit upward aggregation rules so planner consumers do not reinvent them.

### Vocabulary -> Theme Mastery

Recommended rule:

- theme state should aggregate from vocabulary, chunk, and pattern evidence linked to that theme
- vocabulary should be the strongest base signal because theme membership authority is already strongest there
- theme success should measure coverage breadth plus recent active evidence, not just average score

Initial model:

```text
theme_mastery =
0.60 * weighted_vocab_theme_mastery +
0.20 * theme_pattern_exposure +
0.20 * theme_chunk_fluency
```

### Grammar -> Pattern Readiness

Recommended rule:

- pattern readiness should depend on prerequisite grammar nodes from `grammar_refs` and dependency edges
- grammar gaps should reduce pattern confidence even when surface pattern recognition is high

Initial model:

```text
pattern_readiness =
0.70 * prerequisite_grammar_decay_adjusted_score +
0.30 * direct_pattern_evidence
```

### Pattern -> Speaking/Writing Readiness

Recommended rule:

- direct pattern mastery should contribute strongly to productive readiness
- speaking and writing should use different evidence weighting because output conditions differ

Initial model:

```text
speaking_readiness =
0.60 * pattern_mastery +
0.20 * chunk_fluency +
0.20 * response_speed_or_fluency

writing_readiness =
0.65 * pattern_mastery +
0.25 * grammar_accuracy +
0.10 * vocabulary_fit
```

### Chunk -> Expression Fluency

Recommended rule:

- chunks should aggregate toward expression fluency because they capture formulaic ease
- success on a chunk should not automatically imply full grammar or vocabulary mastery

Initial model:

```text
expression_fluency =
0.70 * direct_chunk_success +
0.30 * supporting_vocabulary_stability
```

### Theme Stage -> Spiral Readiness

Recommended rule:

- spiral readiness should combine current theme stage mastery, review freshness, and prerequisite readiness for higher-stage vocabulary/pattern load
- `SPIRAL_TO` remains non-gating, but ranking can downweight a spiral jump when current stage evidence is weak

Initial model:

```text
spiral_readiness =
0.50 * current_theme_stage_decay_adjusted_score +
0.30 * review_freshness +
0.20 * next_stage_prerequisite_readiness
```

## Decay / Retention Model

Mastery must decay over time because static best-ever score is not the same as current recall or production reliability.

If S9A does not decay:

- the planner will overestimate retained knowledge after long inactive periods
- review scheduling will drift or stop entirely
- one-time quiz success can permanently inflate ranking
- speaking and writing weakness may be masked by old worksheet data

Recommended initial rules:

1. High mastery decays slower.
2. Low mastery decays faster.
3. Recent successful evidence reduces decay pressure.
4. `review_due_at` should be computed from decay and evidence history, not manually assigned.

Simple first-pass model:

```text
decay_rate_per_day =
base_rate
* mastery_band_multiplier
* evidence_reliability_multiplier
* inactivity_multiplier

decay_adjusted_score =
max(0, mastery_score - decay_since_last_success)
```

Suggested first-pass multipliers:

| State | Decay guidance |
|---|---|
| `automatic` | very slow decay |
| `mastered` | slow decay |
| `functional` | moderate decay |
| `practicing` | faster decay |
| `seen` | fast decay toward `unknown` |
| `unknown` | no decay needed |

Suggested review due logic:

```text
review_due_at = earliest timestamp where
projected_decay_adjusted_score crosses the band threshold boundary
or where policy minimum review interval expires for weak/stale nodes
```

This keeps `review_due_at` deterministic and rebuildable after process restart.

## S9A / S9B Boundary

Required hard boundary:

- S9A stores and computes learner state.
- S9B ranks candidate next nodes.
- S9C produces planner decisions.
- S9A must not recommend lessons directly.

More explicit contract split:

| Layer | Owns | Must not own |
|---|---|---|
| `S9A` | learner mastery records, evidence aggregation, decay, review due computation, readiness support metrics | candidate ranking, lesson recommendation, scheduler policy |
| `S9B` | candidate ranking, feature weighting, score composition over S9A + S8 outputs | persistence of learner truth |
| `S9C` | planner decisions, pacing, bundle selection, remediation flow | canonical learner-state computation |

Why this matters:

- ranking heuristics will change more often than authority truth
- storing planner outputs as learner truth would create replay inconsistency after retries or restarts
- future APIs, dashboards, and orchestrators need stable learner-state facts independent of one planner version

## Data Products

Recommended future files:

- `ulga/learner_state/learner_state_schema.json`
- `ulga/learner_state/sample_learner_state.json`
- `ulga/learner_state/evidence_event_schema.json`
- `ulga/reports/learner_state_design_scan.json`

Recommended artifact roles:

| File | Purpose |
|---|---|
| `learner_state_schema.json` | canonical validation contract for learner-state records |
| `sample_learner_state.json` | fixture and dashboard/API alignment sample |
| `evidence_event_schema.json` | canonical event input contract |
| `learner_state_design_scan.json` | structured design-scan output for downstream tooling and status reporting |

## PASS / WARN / BLOCKER Findings

### PASS

- `ulga/schema/ulga_node_schema.json` already permits `learner_state` IDs and `node_type`, so S9A fits the existing node contract direction.
- S8F already defines learner-state-relevant signal semantics such as `MASTERY_SIGNAL`, `REVIEW_SIGNAL`, `COVERAGE_SIGNAL`, `CONTEXT_SIGNAL`, and `DIAGNOSTIC_SIGNAL`.
- `pattern_vocabulary_candidate_query_contract.json` already declares `learner_mastery_gap` as a ranking signal, which validates the need for S9A before S9B.
- Dependency QA is currently `PASS`, which gives S9A a stable source for prerequisite readiness consumption.

### WARN

- Theme spiral QA is `PASS_WITH_WARNINGS`; 8 spiral edges skip intermediate CEFR stages and are tracked in a review queue. S9A should not overtrust spiral progression as smooth readiness evidence.
- Pattern vocabulary constraint QA is `WARNING_ACCEPTED`; active constraints are usable, but S9A should expect incomplete slot-type precision and avoid overstating pattern-derived vocabulary mastery.
- Morphology is currently edge-based, not a mounted node type. S9A needs a clear decision on whether morphology state is stored as vocabulary-family derived state or delayed until a distinct authority exists.
- Coverage and context signals are available, but S8 explicitly warns that they do not prove mastery. S9A must preserve that separation.

### BLOCKER

- No canonical learner-state schema, evidence-event schema, or runtime state artifact exists yet. Candidate ranking should not implement persistent learner mastery logic before this authority exists.
- No current mounted reading/dialogue/assessment node authority exists. S9A can design for them now, but direct node-level evidence mapping for those domains remains future work.
- Without explicit idempotency and duplicate-event rules, repeated execution and process restart can inflate exposure counts and corrupt mastery state.

## Risks and Open Questions

### Privacy of Learner Data

Learner-state records are dynamic personal data, unlike static authority graphs. Storage, export, dashboard display, and report generation must account for privacy and retention policy. This becomes more important for child learners and multi-user environments.

### Overfitting to Quiz Scores

Quiz results are easy to collect and therefore easy to overweight. If S9A relies too heavily on quiz success:

- recognition may be mistaken for production mastery
- timed guessing may distort automaticity
- speaking/writing weakness may stay hidden

### Speaking/Writing Evidence Reliability

Speaking and writing can be high-value evidence, but only if scoring quality is trustworthy. Auto-scoring, transcription errors, rubric drift, and partial human review can distort mastery updates. S9A should treat confidence and evidence source separately from raw score.

### Parent Manual Override

Parent-reported evidence is valuable but noisy. S9A needs:

- explicit provenance
- conservative default weight
- override reason logging
- ability to distinguish annotation from authority override

### Multi-Learner Support for James and Cyndi

S9A must support more than one learner from the start. `learner_id` cannot be optional or implied by file location. Aggregation, exports, dashboards, and APIs must avoid global-state pollution across James and Cyndi.

### Migration From Static Authority to Dynamic Learner State

Static authority layers describe what exists in the learning graph. S9A introduces dynamic per-learner truth. Open questions:

- should learner state be modeled as ULGA-style nodes, separate records, or both
- how will dashboard and API read dynamic state without confusing it with static graph authority
- how should old learner-state versions be migrated when scoring rules change

### Real Environment Risks

- API failure: event ingestion may partially succeed and create mismatched state unless updates are transactional or replay-safe.
- Timeout: batch recomputation may leave partial learner-state snapshots unless state versioning is atomic.
- Empty data: cold-start learners must remain valid and queryable as `unknown`, not error.
- Repeated execution: duplicate evidence ingestion can inflate `exposure_count`.
- Process restart: rebuild logic must derive the same `review_due_at` from persisted evidence and policy.
- Abnormal upstream response: future speaking, assessment, or dashboard services may return incomplete scores, null timestamps, or confidence gaps; S9A schema should allow rejection or quarantine, not silent corruption.

## Recommended Next Tasks

Recommended sequence:

1. `ULGA-S9B_MasterGraphSchema_DesignScan`
2. `ULGA-S9C_EvidenceEventSchema_Implementation`
3. `ULGA-S9D_LearnerStateBuilder`
4. `ULGA-S9E_CandidateRanking_DesignScan`

Why this order:

1. The master schema boundary should be fixed before builder work to avoid schema drift across state, evidence, and planner consumers.
2. Evidence event schema should be implemented before learner-state building so ingestion is idempotent and validator-ready.
3. Learner-state builder should come before candidate ranking so `learner_mastery_gap`, `review_due_at`, and decay-aware readiness are authoritative inputs rather than ranking-local heuristics.
4. Candidate ranking design should happen after S9A builder assumptions are concrete.

## Final Assessment

Final recommendation: `PASS WITH WARNINGS`.

S9A is architecturally necessary and fits the direction already established by S8 dependency, theme spiral, and learning signal work. The main risk is not conceptual ambiguity but boundary leakage: if learner-state logic is skipped or embedded directly into candidate ranking, the system will accumulate duplicated state logic, retry inconsistencies, and poor multi-learner separation.

Minimal-change recommendation:

- introduce S9A as a separate learner-state authority artifact family
- keep static ULGA graph files unchanged
- treat evidence, aggregation, decay, and review computation as S9A responsibilities only
- defer actual recommendation behavior to S9B and S9C
