# ULGA-S10A Candidate Ranking Design Scan

## 1. Scope

S10A defines the design boundary for a new **Candidate Ranking Authority** that sorts already-eligible ULGA candidates into a stable "next best thing to learn" order.

This scan is design-only. It does not modify any existing graph, builder, validator, learner-state artifact, schema, or report.

S10A scope:

- rank `candidate nodes` and `learning opportunities`
- consume existing authority outputs from Dependency, Theme Spiral, Pattern Vocabulary Candidate Query, and Learner State
- produce future ranking policy / contract / report drafts only

S10A out of scope:

- direct lesson generation
- direct learner-state mutation
- final lesson-plan assembly
- content-authority decisions for Reading / Dialogue / Exercise
- adding new mounted graph edges

Minimal-change position:

- reuse existing query-time candidate philosophy from `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- reuse existing non-gating theme policy from Theme Spiral
- reuse guarded learner-state outputs only
- keep ranking as a separate runtime/planner-side authority rather than back-writing graph truth

## 2. Current Inputs Reviewed

Reviewed design and contract inputs:

- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7DII_CANDIDATE_QUERY_CONTRACT_DEFAULT_LIMIT_FIX_CLOSEOUT.md`
- `docs/ulga/ULGA_S7E_PATTERN_THEME_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8B_THEME_SPIRAL_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8D_DEPENDENCY_AUTHORITY_QA_AUDIT.md`
- `docs/ulga/ULGA_S8I1_THEME_SPIRAL_AUTHORITY_QA_REAUDIT.md`
- `docs/ulga/ULGA_S9A_LEARNER_STATE_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9G_LEARNER_STATE_BUILDER_GUARDRAIL_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S9I_LEARNER_STATE_GUARDRAIL_QA_AUDIT.md`
- `docs/ulga/ULGA_S9J_LEARNER_STATE_STABILITY_AUDIT.md`
- `docs/ulga/ULGA_S9L_POST_TIGHTENING_READINESS_AUDIT.md`

Reviewed runtime artifacts and graph inputs:

- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/learner_state/learner_state.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/learner_state_builder_summary.json`
- `ulga/reports/learner_state_guardrail_summary.json`

Reviewed tests and validator expectations:

- `tests/ulga/test_pattern_vocabulary_constraints.py`
- `tests/ulga/test_dependency_graph.py`
- `tests/ulga/test_theme_spiral_graph.py`
- `tests/ulga/test_learner_state_builder.py`
- `tests/ulga/test_learner_state_guardrails.py`
- `tests/ulga/test_learner_state_stability_audit.py`

Key facts extracted from current inputs:

- Candidate query already uses gate-then-rank with top-level `limit_default=50`, `limit_max=200`, and ranking signals `theme_match`, `frequency_band`, `learner_mastery_gap`, `recency`, `diversity`.
- Dependency Authority is separate from path planning; only accepted `REQUIRES` edges are gate-eligible, and current dependency graph is limited to 84 hard grammar prerequisites.
- Theme Spiral is explicitly non-gating; current summary shows 12 `SPIRAL_TO` edges, 0 gate-eligible edges, and 8 reviewed stage-gap warnings.
- Learner State is required before learner-specific ranking, but ranking must consume guarded outputs rather than raw inflated mastery.
- Learner-state stability is usable for ranking with warnings, but still too risky for aggressive planner behavior.

## 3. Candidate Ranking Position in ULGA

### 3.1 Authority Boundary

Candidate Ranking Authority sits after candidate eligibility and before final planner/material choice.

Recommended pipeline:

```text
graph authorities
+ candidate query / opportunity builder
+ hard blocks / eligibility filters
+ candidate ranking authority
+ antigravity planner
+ reading/dialogue/exercise authority
```

### 3.2 Boundary With Existing Modules

`Dependency Authority`

- provides block / readiness facts
- Candidate Ranking may read `REQUIRES`, `gate_eligible`, and unmet prerequisite counts
- Candidate Ranking must not redefine dependencies or promote soft/context/theme relations into gates

`Learner State Authority`

- provides guarded `mastery_score`, `mastery_band`, `decay_adjusted_score`, `review_due_at`, `confidence`, and idempotent learner records
- Candidate Ranking may compute `mastery_gap_score` and reinforcement need from learner-state outputs
- Candidate Ranking must not write, merge, or repair learner-state records

`Candidate Query Contract`

- provides candidate-pool shape, query limits, gate order, and existing ranking signal vocabulary
- S10A should extend the idea from vocabulary-slot candidates to general ULGA candidates
- S10A must not narrow the existing contract into pattern-only assumptions

`Antigravity Planner`

- planner chooses final lesson composition, pacing, variety, and top-k assembly
- Candidate Ranking only returns scored candidates plus explanations
- planner may still apply diversity caps, cooldowns, or content-balance policy after ranking

`Reading / Dialogue / Exercise Authority`

- these authorities generate or choose concrete learning content
- Candidate Ranking may nominate a `learning_opportunity`
- it must not generate the final reading, dialogue, exercise, or answer key

### 3.3 Explicit Non-Responsibilities

Candidate Ranking:

- only sorts candidate nodes / learning opportunities
- does not directly generate teaching material
- does not directly modify learner state
- does not directly decide the final lesson plan

## 4. Candidate Definitions

S10A should support two candidate layers so ranking can stay neutral between "what concept" and "what teachable move."

### 4.1 Node Candidate

A `Node Candidate` is a single ULGA node judged eligible for introduction, reinforcement, review, or expansion.

Draft shape:

```json
{
  "candidate_id": "cand_node_vocabulary_004210",
  "candidate_type": "node",
  "node_id": "vocabulary:VOCAB_NODE_004210",
  "node_type": "vocabulary",
  "cefr_level": "A1",
  "source_authorities": [
    "DependencyAuthority",
    "LearnerStateAuthority"
  ]
}
```

Use cases:

- next vocabulary node
- next grammar node
- next sentence pattern node
- next theme stage node for review or continuity context

### 4.2 Learning Opportunity Candidate

A `Learning Opportunity Candidate` is a teachable opportunity centered on one focus node plus supporting references that make the recommendation explainable and content-ready for later authorities.

Draft shape:

```json
{
  "candidate_id": "cand_opp_vocab_004210_home_pattern_000001",
  "candidate_type": "learning_opportunity",
  "opportunity_kind": "introduce_with_pattern_support",
  "focus_node": "vocabulary:VOCAB_NODE_004210",
  "focus_node_type": "vocabulary",
  "theme_refs": [
    "theme:a1_homes_and_neighborhoods"
  ],
  "pattern_refs": [
    "pattern:PATTERN_NODE_000001"
  ],
  "grammar_refs": [
    "grammar:GRAMMAR_NODE_000718"
  ],
  "chunk_refs": [],
  "reinforces": [
    "vocabulary:VOCAB_NODE_001111",
    "vocabulary:VOCAB_NODE_001222"
  ],
  "evidence_summary": {
    "theme_continuity_source": "SPIRAL_TO_or_same_theme",
    "pattern_query_source": "pattern_vocabulary_candidate_query_contract",
    "learner_state_source": "guarded_mastery"
  }
}
```

### 4.3 Why Two Layers Are Needed

- node candidates keep ranking generic and authority-safe
- learning opportunity candidates let planner/content layers explain why a node is worth teaching now
- this avoids coupling ranking to one delivery format
- it also prevents ranking from recommending isolated nodes without enough supporting context

### 4.4 Minimal-Change Recommendation

V1 ranking should allow both types but default runtime output to:

- `node` when only a safe eligible node exists
- `learning_opportunity` when the candidate has explainable support from pattern/theme/grammar references

## 5. Ranking Signals

S10A V1 should use six signals only. This matches current ULGA evidence quality and avoids overfitting to noisy or missing fields.

### 5.1 `dependency_score`

Meaning:

- measures structural readiness after hard blocks have already filtered impossible targets

Recommended inputs:

- unmet hard prerequisite count from `dependency_graph.json`
- number of satisfied prerequisites
- whether candidate is directly reachable without missing authority refs

Recommended semantics:

- `1.00` when all required prerequisites are satisfied and no soft warning exists
- `0.60-0.85` when reachable but supported mainly by non-gating evidence or with mild readiness warnings
- `0.00` only after a hard block check fails; blocked candidates should normally be excluded before scoring

### 5.2 `mastery_gap_score`

Meaning:

- prefers candidates that are neither already mastered nor totally detached from learner readiness

Recommended inputs:

- guarded `decay_adjusted_score`
- guarded `mastery_band`
- `review_due_at`
- confidence from learner-state record

Recommended semantics:

- highest score when learner has a meaningful gap on the focus node or its direct prerequisite chain
- downweight already-mastered targets
- downweight totally cold advanced targets when dependency/context support is weak

Important safety:

- never compute this from raw pre-guardrail mastery
- if learner state is unavailable in learner-specific mode, candidate must hard block rather than silently assume unknown mastery

### 5.3 `reinforcement_score`

Meaning:

- rewards candidates that strengthen nearby weak knowledge instead of teaching isolated items

Recommended inputs:

- `REINFORCES`, `REVIEW_SIGNAL`, and non-gating contextual support from `learning_signal_policy.json`
- overlap with weak prerequisite / sibling / same-pattern / same-theme nodes
- due-for-review evidence from learner state

Recommended semantics:

- high when learning this candidate also revisits weak or due nodes
- low when candidate is a singleton with little graph or theme support

### 5.4 `theme_continuity_score`

Meaning:

- prefers candidates that continue a current or recently used theme without turning theme into a gate

Recommended inputs:

- same-theme membership from pattern/theme refs
- same-stage or adjacent-stage Theme Spiral evidence
- stage-gap review queue warnings from Theme Spiral

Recommended semantics:

- high for same theme or adjacent accepted spiral step
- medium for related but not same theme
- low for abrupt thematic jumps
- cap or discount stage-gap edges already warned in Theme Spiral QA

### 5.5 `frequency_score`

Meaning:

- prefers higher-utility common material, especially at lower levels, without letting frequency override readiness or mastery need

Recommended inputs:

- vocabulary frequency proxy from mounted vocabulary metadata
- raw/theme policy frequency band hints where available
- chunk `frequency_proxy_score` if ranking future chunk opportunities

Recommended semantics:

- normalize within candidate type
- use as preference, not gate
- apply a stronger influence at A1-A2 than at B2-C1

### 5.6 `pattern_utility_score`

Meaning:

- rewards candidates that unlock, populate, or strengthen reusable sentence-pattern opportunities

Recommended inputs:

- explicit `pattern_refs` from `sentence_patterns.json`
- active slot constraints from `pattern_vocabulary_constraints.json`
- number of safe eligible opportunities a node can serve

Recommended semantics:

- high when a node can fill common accepted patterns or support multiple reusable patterns
- lower when the node has little pattern connectivity

## 6. Score Formula

### 6.1 V1 Formula

```text
candidate_score =
0.30 * dependency_score
+ 0.20 * mastery_gap_score
+ 0.20 * reinforcement_score
+ 0.10 * theme_continuity_score
+ 0.10 * frequency_score
+ 0.10 * pattern_utility_score
```

### 6.2 Formula Rationale

- `dependency_score` is highest because ULGA already treats hard readiness as authority truth
- `mastery_gap_score` is next because ranking should target what the learner most needs, not just what exists
- `reinforcement_score` is equally important to avoid isolated recommendations
- `theme_continuity_score`, `frequency_score`, and `pattern_utility_score` are meaningful but non-gating

### 6.3 Suggested Signal Computation Rules

```text
dependency_score:
1.00 if all hard prerequisites satisfied
0.00 if any hard prerequisite missing
else not reachable in V1

mastery_gap_score:
1.00 when guarded mastery is low-to-mid and candidate is reachable
0.30 or less when guarded mastery is already high
0.50 default only in non-learner-specific mode

reinforcement_score:
1.00 when candidate strengthens multiple weak/due neighboring nodes
0.50 when reinforcement is plausible but sparse
0.10 when candidate is isolated

theme_continuity_score:
1.00 same theme or accepted adjacent spiral step
0.60 related theme
0.20 abrupt jump or stage-gap warning case

frequency_score:
normalized per candidate type and CEFR band

pattern_utility_score:
higher when candidate participates in accepted reusable pattern slots or focus-pattern support
```

### 6.4 Tie-Break Order

When `candidate_score` ties, use:

1. higher `dependency_score`
2. higher `mastery_gap_score`
3. higher `reinforcement_score`
4. lower CEFR jump from recent/current learner context
5. deterministic `candidate_id` ordering

Deterministic tie-breaks matter for repeated execution and process restart stability.

## 7. Hard Block Policy

Hard blocks must execute before scoring. Blocked candidates should be excluded from the ranked list and counted in audit output.

### 7.1 Required Hard Blocks

`missing prerequisite`

- any unmet accepted gate-eligible `REQUIRES` dependency

`candidate level above allowed ceiling`

- candidate CEFR exceeds runtime ceiling or slot/query ceiling

`blocked grammar`

- focus candidate depends on grammar explicitly blocked by policy, unresolved guardrail, or authority denial

`blocked vocabulary`

- candidate requires vocabulary barred by current candidate-query contract or safety policy

`unsafe chunk`

- any learning opportunity depending on a chunk outside the safe mounted authority or marked unusable by downstream content rules

`missing authority reference`

- required `node_id`, `theme_ref`, `pattern_ref`, `grammar_ref`, or dependency evidence cannot be resolved in mounted artifacts

`learner_state unavailable in learner-specific mode`

- learner-specific ranking must not silently degrade into anonymous ranking if learner state is missing, unreadable, or schema-invalid

### 7.2 Additional Recommended Hard Blocks

- `review_status != accepted` for focus patterns or dependency sources used as authority facts
- `generator_allowed = false` when a learning opportunity depends on pattern/query generation that is explicitly disabled
- `candidate_type unsupported_by_runtime` when planner requested only node candidates or only opportunities

### 7.3 Hard Block Notes

- Theme Spiral must never hard block by itself.
- `BELONGS_TO`, `USES`, `supports`, `reviews`, and `SPIRAL_TO` remain non-gating unless a future authority explicitly promotes them.
- Empty candidate pools are valid outputs and must return an explanatory report rather than fallback hallucinated recommendations.

## 8. Output Contract Drafts

These are schema drafts only. No JSON files are created in S10A.

### 8.1 `candidate_ranking_policy.json`

Purpose:

- static runtime policy for weights, block rules, mode flags, and tie-break behavior

Draft schema:

```json
{
  "contract_id": "ulga.candidate_ranking_policy",
  "contract_version": "ULGA-S10B.v1",
  "ranking_mode": "learner_specific_or_global",
  "candidate_types_allowed": ["node", "learning_opportunity"],
  "weights": {
    "dependency_score": 0.30,
    "mastery_gap_score": 0.20,
    "reinforcement_score": 0.20,
    "theme_continuity_score": 0.10,
    "frequency_score": 0.10,
    "pattern_utility_score": 0.10
  },
  "hard_blocks": [
    "missing_prerequisite",
    "candidate_level_above_allowed_ceiling",
    "blocked_grammar",
    "blocked_vocabulary",
    "unsafe_chunk",
    "missing_authority_reference",
    "learner_state_unavailable_in_learner_specific_mode"
  ],
  "theme_spiral_policy": {
    "non_gating": true,
    "stage_gap_edge_weight_cap": 0.20
  },
  "learner_state_policy": {
    "require_guarded_scores": true,
    "use_decay_adjusted_score": true,
    "fallback_global_mode_allowed": false
  },
  "tie_break_order": [
    "dependency_score",
    "mastery_gap_score",
    "reinforcement_score",
    "lower_context_jump",
    "candidate_id"
  ]
}
```

### 8.2 `candidate_ranking_contract.json`

Purpose:

- request/response contract for a ranking invocation

Draft schema:

```json
{
  "contract_id": "ulga.candidate_ranking_contract",
  "contract_version": "ULGA-S10B.v1",
  "request": {
    "learner_id": "optional string",
    "ranking_mode": "global|learner_specific",
    "candidate_pool_ref": "required string",
    "candidate_types_requested": ["node", "learning_opportunity"],
    "target_cefr_ceiling": "optional string",
    "theme_context": ["optional array"],
    "top_k": "required integer <= 200"
  },
  "candidate_record": {
    "candidate_id": "string",
    "candidate_type": "node|learning_opportunity",
    "focus_node": "string",
    "focus_node_type": "string",
    "theme_refs": ["array"],
    "pattern_refs": ["array"],
    "grammar_refs": ["array"],
    "reinforces": ["array"],
    "candidate_score": "number",
    "signal_scores": {
      "dependency_score": "number",
      "mastery_gap_score": "number",
      "reinforcement_score": "number",
      "theme_continuity_score": "number",
      "frequency_score": "number",
      "pattern_utility_score": "number"
    },
    "block_status": "eligible|blocked",
    "block_reasons": ["array"],
    "explanations": ["array"],
    "authority_refs": {
      "dependency": ["array"],
      "learner_state": ["array"],
      "theme_spiral": ["array"],
      "pattern_query": ["array"]
    }
  }
}
```

### 8.3 `candidate_ranking_report.json`

Purpose:

- audit-friendly artifact for ranking runs, QA, dashboards, and regression checks

Draft schema:

```json
{
  "report_id": "candidate_ranking_report:timestamp_or_run_id",
  "contract_version": "ULGA-S10C.v1",
  "generated_at": "ISO-8601 string",
  "ranking_mode": "global|learner_specific",
  "learner_id": "optional string",
  "candidate_pool_size": "integer",
  "eligible_candidate_count": "integer",
  "blocked_candidate_count": "integer",
  "dependency_block_count": "integer",
  "top_k": "integer",
  "top_candidates": [
    {
      "rank": "integer",
      "candidate_id": "string",
      "candidate_type": "string",
      "focus_node": "string",
      "candidate_score": "number",
      "signal_scores": {
        "dependency_score": "number",
        "mastery_gap_score": "number",
        "reinforcement_score": "number",
        "theme_continuity_score": "number",
        "frequency_score": "number",
        "pattern_utility_score": "number"
      },
      "explanations": ["array"]
    }
  ],
  "distribution_metrics": {
    "top_k_distribution_by_type": "object",
    "top_k_distribution_by_level": "object",
    "frequency_band_distribution": "object"
  },
  "warnings": ["array"],
  "status": "PASS|PASS_WITH_WARNINGS|BLOCKED"
}
```

## 9. QA / Audit Plan

S10B/S10C should validate the following metrics on every ranking build or sampled runtime batch.

### 9.1 Required Metrics

`dependency_block_count`

- how many candidates were removed due to unmet hard prerequisites

`eligible_candidate_count`

- confirms ranking is not silently collapsing to zero

`top_k_distribution_by_type`

- guards against all results becoming only nodes or only opportunities

`top_k_distribution_by_level`

- detects uncontrolled CEFR jumping

`theme_continuity_ratio`

- ratio of top-k candidates aligned to current/recent theme context

`reinforcement_ratio`

- ratio of top-k candidates that strengthen at least one weak/due neighbor

`mastery_gap_avg`

- average guarded gap score for top-k candidates

`frequency_band_distribution`

- detects overconcentration in only ultra-common or only rare items

`pattern_utility_coverage`

- proportion of top-k candidates with explicit reusable pattern support

`explainability_coverage`

- proportion of ranked outputs with non-empty explanation and authority refs

### 9.2 Additional Recommended Audits

- deterministic repeat-run audit with same inputs
- missing-authority-reference count
- stage-gap theme usage count
- already-mastered top-k count
- isolated-node recommendation count
- learner-state-missing hard block count

### 9.3 QA Failure Examples

- top-k dominated by high-frequency isolated vocabulary
- mastered content repeatedly reappears without review rationale
- stage-gap spiral edges dominate theme continuity
- learner-specific mode falls back to anonymous scoring without explicit warning
- score explanations do not map back to authority artifacts

## 10. Risks and Mitigations

### 10.1 `ranking overfits frequency`

Risk:

- common words/chunks may dominate top-k and suppress structurally better targets

Mitigation:

- cap `frequency_score` at 0.10 total weight
- normalize by candidate type and CEFR
- audit `frequency_band_distribution`

### 10.2 `ranking ignores mastery`

Risk:

- learner gets generic curriculum order instead of personalized next step

Mitigation:

- require guarded learner-state inputs in learner-specific mode
- make `mastery_gap_score` a first-class weight
- hard block when learner state is unavailable in learner-specific mode

### 10.3 `ranking jumps theme too aggressively`

Risk:

- planner appears erratic and loses continuity

Mitigation:

- use Theme Spiral only as non-gating context
- cap stage-gap edge contribution
- audit `theme_continuity_ratio`

### 10.4 `ranking recommends isolated vocabulary nodes`

Risk:

- next-step suggestions are hard to teach and weakly reusable

Mitigation:

- reward `reinforcement_score` and `pattern_utility_score`
- introduce isolated-node QA warning
- prefer learning-opportunity candidates when support refs exist

### 10.5 `ranking duplicates already-mastered content`

Risk:

- wastes learner time and reduces trust

Mitigation:

- downweight high guarded mastery unless review is due
- distinguish review candidates from introduction candidates
- audit already-mastered rate in top-k

### 10.6 `ranking cannot explain why candidate was selected`

Risk:

- downstream planner, dashboard, and audits cannot validate behavior

Mitigation:

- require per-signal score breakdown
- require explanation strings and authority refs
- measure `explainability_coverage`

### 10.7 `candidate query contract too narrow`

Risk:

- ranking inherits pattern-vocabulary assumptions and cannot generalize to grammar/theme/chunk opportunities

Mitigation:

- treat current candidate query as a seed contract, not the full S10 contract
- design generic candidate records with focus-node plus support refs
- keep ranking neutral to content authority

### 10.8 Real Environment Risks

`API failure / timeout`

- ranking service may fail while reading learner state or upstream candidate pools
- mitigation: fail closed in learner-specific mode, return status + warnings, never invent fallback mastery

`empty data`

- no eligible candidates may exist after hard blocks
- mitigation: return empty ranked list plus block summary

`duplicate execution`

- repeated ranking runs should not change order with identical inputs
- mitigation: deterministic tie-break and immutable scoring inputs

`process restart`

- restarted runtime must reproduce same top-k for same artifacts and timestamp assumptions
- mitigation: deterministic contract, explicit build timestamps, no hidden mutable state

`abnormal authority response`

- missing refs, null learner fields, invalid stage links, or stale reports can corrupt ranking
- mitigation: hard block missing authority refs and emit report warnings

## 11. Recommended Next Tasks

1. `S10B_CandidateRanking_Implementation`
   Minimal first pass:
   rank only eligible `node` and `learning_opportunity` candidates using existing dependency graph, theme spiral graph, candidate query contract, and guarded learner state.

2. `S10C_CandidateRanking_QA_Audit`
   Validate deterministic ordering, hard-block behavior, explainability coverage, and top-k distributions.

3. Optional follow-up after S10C:
   add planner-side diversity/cooldown policy, but keep it outside Candidate Ranking Authority.

## 12. Final Verdict

S10A is ready to proceed.

Reasons:

- existing authorities already define safe gating boundaries
- current candidate query contract provides a usable runtime ranking model seed
- guarded learner-state outputs are now good enough for conservative ranking consumption
- Theme Spiral is explicitly available as non-gating continuity input
- no new graph mutation is required for a V1 ranking authority

Controlled warnings:

- learner-state stability remains `PASS_WITH_WARNINGS`, so S10B should stay conservative
- Theme Spiral stage-gap edges must be capped or ignored for strong continuity boosts
- pattern-theme explicit coverage remains sparse, so many opportunities will rely on weak or absent theme evidence

```text
S10A_STATUS: DESIGN_READY
```
