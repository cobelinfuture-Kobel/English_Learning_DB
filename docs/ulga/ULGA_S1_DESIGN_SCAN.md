# ULGA-S1 Universal Learning Graph Authority Design Scan

## Scope

This is a design-only architecture audit for the first Universal Learning Graph Authority (ULGA) blueprint in `English_Learning_DB`.

ULGA is not a Learning Path. ULGA is the unified authority graph layer that connects Grammar, Vocabulary, Chunk, Theme, Sentence Pattern, Learner State, Dependency, Gate, Planner, Assessment, and Media knowledge. A Learning Path is only a query result over ULGA.

No implementation code, formal graph JSON, data cleaning, generator runtime change, validator runtime change, or recommendation algorithm was produced in this scan.

## Files Inspected

Found and inspected:

- `docs/A1_C1_情境.txt`
- `README.md`
- `docs/LEVEL_PROFILE_DESIGN.md`
- `docs/THEME_PROFILE_DESIGN.md`
- `docs/VOCAB_SOURCE_IMPORT_DESIGN.md`
- `docs/VOCAB_CEFR_FREQUENCY_POLICY.md`
- `docs/VOCAB_DUPLICATE_POLICY_DESIGN.md`
- `docs/THEME_MAPPING_SCHEMA.md`
- `grammar_profile/json/grammar_profile.json`
- `vocabulary/json/vocabulary.json`
- `themes/theme_mapping.json`
- `themes/theme_catalog.json`
- `level_profiles/A1.json`
- `chunk_profile/json/chunks.json`
- `chunk_profile/json/chunk_equivalence_groups.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`
- `chunk_profile/json/chunks_generator_safe.json`
- Chunk authority reports under `chunk_profile/reports/`

Requested but not found by filename scan:

- `A1資料庫自動化設計.txt`
- `學習路徑與依賴圖.txt`
- `20260615_03_LPA-S1 設計掃描.txt`
- `ULGA-S1 設計討論.txt`

This is a documentation risk, not an implementation blocker. The current repo already contains enough normalized authority artifacts to define the first ULGA boundary and contract, but the missing design notes should be reconciled before ULGA-S2 implementation.

## Current Authority State

### Grammar Authority

`grammar_profile/json/grammar_profile.json` contains 1,222 EGP records. Each record already has stable fields that can mount into ULGA:

- `id`
- `super_category`
- `sub_category`
- `level`
- `lexical_range`
- `guideword`
- `can_do_statement`
- `example`
- `source_sheet`
- `source_row`
- `import_warnings`

Grammar is currently the strongest formal authority source because it has can-do statements and examples. It is suitable for dependency and gate modeling, but dependency edges are not yet formalized.

### Vocabulary Authority

`vocabulary/json/vocabulary.json` contains 15,696 EVP-derived rows with CEFR, topic, part of speech, duplicate status, active flag, frequency metadata, and recovery metadata.

Relevant authority signals:

- Difficulty: `level`
- Frequency: `frequency_band`, `frequency_score`, `corpus_rank`
- Topic/theme alignment: `topic`, `theme_candidates`
- Deduplication: `duplicate_status`, `source_rows`
- Reliability: `topic_status`, `pos_status`, `recovery_confidence`, `review_required`

Vocabulary is ready to be mounted as ULGA nodes, but should be mounted with active/canonical filtering rules rather than direct raw-row usage.

### Chunk Authority

Chunk authority has moved beyond raw extraction:

- `chunks.json`: 4,546 EVP chunk candidates.
- S1 dedup authority: 3,247 surfaces, 1,106 duplicate surfaces, 1,299 duplicate entries.
- S1B evidence recovery: 924 confirmed exact duplicate review groups, 0 unmatched chunks.
- Safe layer: 3,522 generator-safe canonical chunks.
- `chunk_equivalence_groups.json`: 924 exact duplicate equivalence groups.
- `chunk_usage_class_mapping.json`: usage classes for 4,546 chunk IDs.
- `chunks_generator_safe.json`: canonical safe layer for downstream generation.

Chunk data proves why Learning Path is too narrow as the top-level abstraction. Chunks require equivalence, surface form, usage class, frequency proxy, theme hint, validator equivalence acceptance, and generator-safe canonicalization. These are graph authority concerns, not linear path concerns.

### Theme Authority

Theme data exists in two complementary layers:

- `themes/theme_mapping.json`: level-to-theme categories and notes.
- `themes/theme_catalog.json`: normalized theme IDs, parent theme, progression stage, and active vocabulary count.

Theme profiles define context and communicative scope. They should be graph nodes that align grammar, vocabulary, chunks, media, and assessments around use cases.

### Level Profile Authority

`level_profiles` currently define CEFR and plus-level profiles. They are operational constraints for generation and validation, but they are not enough to model cross-domain prerequisites. ULGA should treat level profiles as policy metadata for Difficulty Authority and Gate Engine decisions.

## Why LPA-S1 Should Upgrade To ULGA-S1

Learning Path Authority (LPA) implies the system's central object is a sequence. The repo has already outgrown that:

- Grammar progression is not linear; it depends on category, tense, clause complexity, and can-do intent.
- Vocabulary progression depends on CEFR, frequency, topic, active state, and duplicate status.
- Chunk progression depends on surface equivalence, usage class, guideword, theme hint, and generator-safe canonicalization.
- Theme progression is spiral; the same theme reappears at higher levels with different language demands.
- Learner state will make the next item conditional on mastery, blocked nodes, gaps, and assessment outcomes.
- Gate decisions must block content that violates prerequisites even if it appears in a plausible path.

ULGA is therefore the correct upper layer. Learning Path becomes a graph query such as: "given learner state, target level, target theme, and blocked nodes, return the next reachable nodes and exercise types." The path is output, not authority.

## ULGA Boundary

### ULGA Owns

- Canonical node types for learning objects.
- Canonical edge types for dependencies and alignments.
- Authority source metadata and confidence.
- Cross-domain constraints between grammar, vocabulary, chunk, theme, assessment, media, and learner state.
- Graph validation contract.
- Gate inputs and outputs.
- Planner inputs and outputs.

### ULGA Does Not Own

- Raw source import pipelines.
- JSON cleaning or deduplication implementation.
- Generator prompt construction.
- Validator runtime behavior.
- Formal recommendation ranking algorithms.
- Learning Path storage as a hand-authored object.

### Learning Path Boundary

A Learning Path is a query result over ULGA. It may be cached later, but its authority comes from the graph and learner state at query time.

Example query shape:

```text
find reachable nodes
where target_level = A2
and target_theme = food_and_dining
and learner has mastered prerequisites
and gates pass
order by difficulty, frequency, theme fit, and assessment gap
```

## Node Types

### GrammarNode

Represents one EGP grammar learning target.

Primary source: `grammar_profile/json/grammar_profile.json`

Core fields:

- `node_id`: `grammar:{egp_id}`
- `level`
- `super_category`
- `sub_category`
- `guideword`
- `can_do_statement`
- `example`
- `source_row`

Authority role: grammar difficulty, syntactic dependency, grammar gate.

### VocabularyNode

Represents one EVP vocabulary record or canonical active vocabulary item.

Primary source: `vocabulary/json/vocabulary.json`

Core fields:

- `node_id`: `vocab:{vocab_id}`
- `word`
- `level`
- `part_of_speech`
- `topic`
- `frequency_band`
- `active`
- `duplicate_status`
- `recovery_confidence`

Authority role: lexical difficulty, frequency, topic alignment, vocabulary gate.

### ChunkNode

Represents one chunk, phrase, phrasal verb, or multi-word entry.

Primary source: `chunk_profile/json/chunks_generator_safe.json` for generator-safe usage; `chunks.json` for raw authority trace.

Core fields:

- `node_id`: `chunk:{canonical_chunk_id}` or `safe_chunk:{safe_id}`
- `chunk`
- `normalized_chunk`
- `level`
- `chunk_type`
- `guideword`
- `usage_class`
- `theme_hint`
- `equivalent_ids`
- `validator_accepts_equivalents`

Authority role: phrase/chunk difficulty, equivalence, chunk gate, generator-safe selection.

### ThemeNode

Represents a communicative theme, category, or parent theme.

Primary source: `themes/theme_catalog.json`, `themes/theme_mapping.json`

Core fields:

- `node_id`: `theme:{theme_id}`
- `theme_name`
- `level`
- `parent_theme`
- `progression_stage`
- `description`
- `active_vocabulary_count`

Authority role: contextual alignment, spiral progression, theme gate.

### SentencePatternNode

Represents a reusable sentence pattern or structural frame.

Current source status: not yet formalized.

Expected fields:

- `node_id`: `pattern:{pattern_id}`
- `pattern_text`
- `level`
- `grammar_refs`
- `slot_constraints`
- `example`

Authority role: bridges GrammarNode and generated sentence form. This should not be inferred automatically in S1.

### SkillNode

Represents a learning skill such as reading, listening, speaking, writing, grammar recognition, chunk production, or vocabulary recall.

Core fields:

- `node_id`: `skill:{skill_id}`
- `skill_domain`
- `mode`
- `level`
- `assessment_methods`

Authority role: connects learning objects to practice and assessment modalities.

### LearnerNode

Represents one learner or learner cohort state container.

Core fields:

- `node_id`: `learner:{learner_id}`
- `current_level`
- `target_level`
- `mastery_state_ref`
- `blocked_nodes`
- `recent_assessment_refs`

Authority role: not a static content node. It is a state node used by planner and gate queries.

### AssessmentNode

Represents a question, task, diagnostic, rubric, or assessment result type.

Core fields:

- `node_id`: `assessment:{assessment_id}`
- `assessment_type`
- `target_nodes`
- `skill_domain`
- `difficulty`
- `evidence_model`

Authority role: measures mastery and updates learner state.

### MediaNode

Represents media assets or media requirements, not necessarily generated media files.

Core fields:

- `node_id`: `media:{media_id}`
- `media_type`
- `complexity`
- `linked_theme`
- `linked_assessment`
- `generation_status`

Authority role: controls media fit, not language difficulty by itself.

## Edge Types

### REQUIRES

`A REQUIRES B` means A should not be introduced unless B is already mastered or permitted by a gate exception.

Primary use:

- Grammar prerequisites.
- Chunk prerequisites requiring vocabulary or grammar.
- Assessment prerequisites.

### CONTAINS

Parent-child containment.

Examples:

- ThemeNode contains VocabularyNode.
- ThemeNode contains ChunkNode.
- SkillNode contains AssessmentNode families.

### USES

One node uses another as a component.

Examples:

- SentencePatternNode uses GrammarNode.
- AssessmentNode uses VocabularyNode.
- ChunkNode uses VocabularyNode when decomposable.

### SPIRAL_TO

Represents repeated theme or skill progression at a higher complexity level.

Examples:

- `theme:a1_food_and_dining SPIRAL_TO theme:a2_food_and_dining`
- `skill:short_answer SPIRAL_TO skill:paragraph_response`

### PRECEDES

Soft ordering edge, weaker than REQUIRES.

Example:

- Present simple precedes present perfect as a recommended sequence, but may not be an absolute dependency in every theme.

### ALIGNS_WITH

Cross-authority semantic alignment.

Examples:

- VocabularyNode aligns with ThemeNode.
- ChunkNode aligns with ThemeNode.
- AssessmentNode aligns with SkillNode.

### BLOCKS

Explicit exclusion relationship.

Examples:

- A Level Gate blocks C1 chunks in A2 generation.
- A Theme Gate blocks unrelated topic nodes.

### RECOMMENDS

Planner suggestion edge. This is advisory and should never replace gate decisions.

### ASSESSES

AssessmentNode assesses GrammarNode, VocabularyNode, ChunkNode, SkillNode, or a composite.

### GENERATES

A generator or pattern produces candidate content from graph nodes. In S1 this is a contract edge only, not runtime implementation.

## Authority Hierarchy

### Difficulty Authority

Combines CEFR level, plus-level policy, lexical range, frequency, chunk priority, sentence length, and media complexity.

Primary sources:

- EGP level
- EVP level
- Level profiles
- Vocabulary frequency policy
- Chunk safe layer priority

### Dependency Authority

Owns prerequisite edges and blocked progression.

Current status:

- Grammar categories imply dependency but are not formalized.
- Theme spiral exists conceptually.
- Chunk equivalence exists, but chunk prerequisite dependencies do not.

### Theme Authority

Owns ThemeNode definitions, theme progression, topic alignment, and theme gates.

Primary sources:

- `themes/theme_mapping.json`
- `themes/theme_catalog.json`
- chunk theme hints
- vocabulary topics

### Frequency Authority

Owns lexical sampling pressure and overload prevention.

Primary sources:

- `frequency_band`
- `frequency_score`
- `corpus_rank`
- frequency policy docs
- chunk frequency proxy score

### Learner State Authority

Owns mastery state, blocked nodes, assessment history, recency, and known gaps.

Current status: not implemented. S1 defines the boundary only.

### Antigravity Planner

Uses the ULGA graph and learner state to propose next best nodes. It does not bypass gates and does not own source truth.

### Gate Engine

Deterministic enforcement layer that decides whether a candidate node or generated content is allowed.

## Antigravity Planner Contract

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

Planner rule: the planner may recommend, but the Gate Engine must approve.

## Gate Engine

### Dependency Gate

Blocks nodes whose required prerequisites are not mastered.

### Grammar Gate

Blocks grammar structures outside the target level/profile or unsupported by learner state.

### Vocabulary Gate

Blocks inactive, redundant, too-rare, or above-ceiling vocabulary unless explicitly allowed.

### Chunk Gate

Blocks unsafe chunks, non-canonical generator entries, or chunks with unresolved equivalence policy. Validator may accept equivalents even when generator uses canonical-only.

### Theme Gate

Blocks nodes that do not align with the target theme or allowed secondary themes.

### Level Gate

Blocks nodes above target CEFR/plus-level ceiling unless a bridge policy explicitly allows them.

## Integration Risks

- Missing requested design discussion files reduce confidence in historical LPA intent.
- `A1_C1_情境.txt` appears encoding-damaged in the shell output, though normalized theme JSON is readable.
- SentencePatternNode has no current authority source and should remain a placeholder until a source is defined.
- Learner State Authority is not present yet; planner and gates must not be implemented before its contract exists.
- Chunk exact duplicate review remains a warning source, but the safe layer already provides generator-safe canonical entries.
- Theme plus-level mappings are descriptive-only and need inherited category policy during graph mounting.

## S1 Verdict

WARNING

Reason: ULGA-S1 design can proceed and the repo has enough authority artifacts for a first graph contract, but several requested design notes were not found and SentencePattern/LearnerState authorities are not yet backed by source data.

