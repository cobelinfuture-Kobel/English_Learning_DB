# ULGA Roadmap

## Roadmap Principle

ULGA must be built before Learning Path automation. The graph is the authority; the path is a query result.

Each stage should produce either a design artifact, a schema artifact, or an authority mounting layer. Generator and validator runtime changes must wait until graph contracts and gates are validated.

## Stage Order

### ULGA-S1 Universal Learning Graph Authority DesignScan

Status: complete as design scan.

Purpose:

- Define ULGA boundary.
- Explain why LPA should upgrade to ULGA.
- Define first node types and edge types.
- Define Authority Hierarchy.
- Define Planner and Gate boundaries.
- Produce schema contract and roadmap docs.

Outputs:

- `docs/ulga/ULGA_S1_DESIGN_SCAN.md`
- `docs/ulga/ulga_schema_contract.md`
- `docs/ulga/ulga_roadmap.md`

No JSON graph output.

### ULGA-S2 GraphSchemaImplementation

Purpose:

- Implement formal graph schema files and validators.
- Define graph manifest structure.
- Validate node/edge enum, authority source, confidence, and endpoint integrity.

Allowed outputs:

- Graph schema JSON or Python validation schema.
- Tests for schema validation.
- Empty or fixture-only sample graph for tests.

Not allowed:

- Full graph generation from production data.
- Planner ranking.
- Generator runtime integration.

Exit criteria:

- Schema validates example nodes and edges.
- Invalid edge endpoints fail.
- Missing authority source fails.
- Hard gate confidence rules are enforced.

### ULGA-S3 GrammarDependencyAuthority

Purpose:

- Mount EGP grammar records as GrammarNode candidates.
- Define grammar dependency edges from explicit rule design.
- Separate hard `REQUIRES` from soft `PRECEDES`.

Primary sources:

- `grammar_profile/json/grammar_profile.json`
- `level_profiles/*.json`
- grammar design docs

Risks:

- Some dependencies may be pedagogical rather than source-explicit.
- Low-confidence dependency edges must be provisional.

Exit criteria:

- GrammarNode mount contract passes.
- Dependency graph has no unreviewed blocking cycles.
- Gate-ready grammar prerequisites are identified.

### ULGA-S4 VocabularyChunkMounting

Purpose:

- Mount active vocabulary and generator-safe chunks into ULGA.
- Preserve raw authority trace without exposing unsafe raw duplicates to generators.
- Add equivalence-aware chunk edges.

Primary sources:

- `vocabulary/json/vocabulary.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_equivalence_groups.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`

Required policies:

- Vocabulary generator use prefers active canonical rows.
- Chunk generator use prefers safe canonical chunks.
- Validator can accept equivalent chunk IDs where policy allows.

Exit criteria:

- VocabularyNode and ChunkNode mount contracts pass.
- Chunk equivalence does not collapse source trace.
- Unsafe raw chunk records are not exposed through `GENERATES`.

### ULGA-S5 ThemeSpiralAuthority

Purpose:

- Mount ThemeNode graph.
- Define `SPIRAL_TO`, `CONTAINS`, and `ALIGNS_WITH` edges for theme progression.
- Resolve plus-level descriptive-only theme inheritance.

Primary sources:

- `themes/theme_mapping.json`
- `themes/theme_catalog.json`
- `docs/THEME_PROFILE_DESIGN.md`

Exit criteria:

- Every active level profile has theme coverage.
- Plus-level themes inherit base categories with extension constraints.
- Theme Gate can distinguish primary, secondary, and blocked contexts.

### ULGA-S6 LearnerStateAuthority

Purpose:

- Define LearnerNode and mastery state contract.
- Model known, weak, blocked, stale, and target nodes.
- Define assessment evidence ingestion shape without implementing recommendation.

Inputs:

- learner ID or cohort ID
- current level
- target level
- mastery scores
- blocked nodes
- recent assessment results

Exit criteria:

- Learner state can be queried without changing static authority nodes.
- Mastery state can explain why a prerequisite is satisfied or missing.
- Blocked nodes are traceable by reason and timestamp.

### ULGA-S7 AntigravityPlanner

Purpose:

- Use ULGA graph and learner state to produce next candidate nodes.
- Surface prerequisite gaps and recommended exercise types.
- Remain advisory and gate-dependent.

Input:

- ULGA graph
- learner mastery state
- target level
- target theme
- blocked nodes
- available question types

Output:

- `next_best_nodes`
- `blocked_reason`
- `prerequisite_gap`
- `recommended_exercise_type`

Exit criteria:

- Planner explains why each node is recommended.
- Planner output can be rejected by Gate Engine.
- No generator runtime integration yet.

### ULGA-S8 GateEngine

Purpose:

- Implement deterministic gates over planner candidates.
- Enforce dependency, grammar, vocabulary, chunk, theme, and level constraints.

Gate types:

- Dependency Gate
- Grammar Gate
- Vocabulary Gate
- Chunk Gate
- Theme Gate
- Level Gate

Exit criteria:

- Gate trace explains every blocked node.
- Above-level content is blocked unless an explicit bridge policy allows it.
- Unsafe chunk and inactive vocabulary records are blocked.

### ULGA-S9 RecommendationEngine

Purpose:

- Add ranking after graph and gates are stable.
- Use planner candidates, gate trace, learner state, frequency, difficulty, and theme fit.

Important boundary:

RecommendationEngine ranks approved options. It does not create authority, override gates, or mutate the graph.

Exit criteria:

- Ranking is explainable.
- Ranking can be tested against fixed learner-state fixtures.
- Recommendation output is stable under repeated runs with the same inputs.

## Readiness For ULGA-S2

Ready with warnings.

Ready because:

- Grammar, vocabulary, chunk, theme, and level profile authorities already exist.
- Chunk safe layer shows a working authority separation between raw source, equivalence, and generator-safe output.
- Schema contract can be implemented without changing existing databases.

Warnings:

- Requested LPA/ULGA discussion notes were not found in the workspace.
- Sentence pattern authority has no source yet.
- Learner state authority has no source yet.
- Theme plus-level mappings need inheritance handling.

## Non-Goals Until After ULGA-S8

- No formal Learning Path generator.
- No adaptive recommendation algorithm.
- No generator prompt integration.
- No validator runtime integration.
- No automatic CEFR inference.
- No destructive deduplication.

