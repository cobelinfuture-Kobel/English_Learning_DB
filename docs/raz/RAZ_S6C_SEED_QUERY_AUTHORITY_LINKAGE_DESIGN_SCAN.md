# RAZ-S6C Seed Query Authority Linkage Design Scan

## 1. Preflight

Task: `RAZ-S6C_SeedQueryAuthorityLinkage_DesignScan`

Workspace:

```text
E:\Devspace_Test\English_Learning_DB
```

Scope:

```text
DESIGN SCAN ONLY
NO LINKAGE IMPLEMENTATION
NO QUERY CODE MUTATION
NO VALIDATOR MUTATION
NO RAW RAZ JSON MUTATION
NO DERIVED RAZ OUTPUT MUTATION
NO AUTHORITY GRAPH MUTATION
NO CONTENT AUTHORITY SCHEMA IMPLEMENTATION
NO AUTHORITY PROMOTION
NO CONTENT GENERATION
```

Files inspected:

```text
docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md
docs/raz/RAZ_S6A_REUSABLE_CONTENT_SEED_QUERY_LAYER_IMPLEMENTATION.md
docs/raz/RAZ_S6B_REUSABLE_CONTENT_SEED_QUERY_LAYER_QA.md
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/graph/grammar_nodes.json
ulga/graph/vocabulary_nodes.json
ulga/graph/theme_nodes.json
ulga/graph/sentence_patterns.json
ulga/graph/chunk_nodes.json
ulga/graph/ulga_graph.vocabulary_nodes.json
ulga/graph/ulga_graph.grammar_nodes.json
ulga/graph/ulga_graph.sentence_patterns.json
```

Files created:

```text
docs/raz/RAZ_S6C_SEED_QUERY_AUTHORITY_LINKAGE_DESIGN_SCAN.md
```

Files intentionally not modified:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
tests/ulga/test_raz_reusable_content_seed_query_layer.py
ulga/query/__init__.py
ulga/graph/**/*.json
ulga/reports/**/*.json
raz_output_jsons/Level_*/**/*.json
raz_output_jsons/derived/**/*.json
raz_output_jsons/derived/**/*.jsonl
tools/raz_normalized_tagging_pipeline.py
```

Risk level:

```text
Low
```

---

## 2. Current S6 State

S6A/S6B established a static RAZ seed query layer.

Current queryable universe:

```text
total_seed_cards: 14422
sentence: 7487
page_unit: 4925
reuse_unit: 2010
```

Coverage:

| Level | sentence | page_unit | reuse_unit | total |
|---|---:|---:|---:|---:|
| A | 808 | 804 | 4 | 1616 |
| B | 829 | 802 | 27 | 1658 |
| C | 1064 | 808 | 248 | 2120 |
| D | 1180 | 735 | 389 | 2304 |
| E | 1670 | 904 | 619 | 3193 |
| F | 1936 | 872 | 723 | 3531 |

S6B QA status:

```text
RAZ-S6B_ReusableContentSeed_QueryLayer_QA_PASS
```

S6A query layer can retrieve:

```text
short_reading_seeds
exercise_seeds
dialogue_rewrite_seeds
picture_prompt_seeds
theme_seeds
seed explanations
```

But current RAZ seed cards still have this important limitation:

```text
Grammar and vocabulary tags are rule-based.
Vocabulary is not EVP-linked.
Grammar is not EGP-linked.
CEFR is not authority-linked.
Theme is mapped but not yet explicitly linked to Theme Authority nodes.
Pattern tags are rule-based and not yet linked to Sentence Pattern Authority nodes.
```

Therefore:

```text
S6A/S6B = query-ready
S6C = authority-linkage contract design
S11C = should consume S6C linkage contract before schema implementation
```

---

## 3. Problem Statement

RAZ seed cards are useful candidate content units, but they are not yet linked to formal ULGA authority nodes.

Without a linkage layer, future Reading / Dialogue Content Authority schema may incorrectly store RAZ seed metadata as if it were final authority.

That creates these risks:

```text
1. RAZ rule-based grammar tags may be mistaken for EGP-backed Grammar Authority.
2. RAZ tokenized vocabulary may be mistaken for EVP-backed Vocabulary Authority.
3. RAZ mapped_theme may be mistaken for Theme Authority node refs.
4. RAZ sentence_pattern_tags may be mistaken for Pattern Authority refs.
5. G/H/I future level expansion may require schema rework if level scope is hard-coded.
6. Content Authority records may lack unresolved-ref tracking.
7. Generated Reading/Dialogue candidates may bypass linkage validation.
```

S6C exists to prevent those issues.

---

## 4. Design Goal

S6C should define how a RAZ seed card can produce authority linkage evidence.

The output of future implementation should be:

```text
RAZ seed card
+
Authority linkage evidence
+
Unresolved-link diagnostics
+
Linkage confidence
+
Source traceability
```

It should not produce:

```text
promoted Reading Authority
generated dialogue
generated exercise
generated reading passage
learner-state personalization
adaptive ranking
final CEFR certification
```

---

## 5. Linkage Target Authorities

S6C should support links to these existing authority families.

### 5.1 Grammar Authority

Existing artifact:

```text
ulga/graph/grammar_nodes.json
```

Observed node shape:

```text
id: grammar:GRAMMAR_NODE_000001
node_type: grammar
label: FORM: COMBINING TWO ADJECTIVES WITH 'BUT'
cefr_level: A2
metadata.canonical_grammar_key
metadata.grammar_family
metadata.grammar_subtype
metadata.can_do_statement
```

Future linkage input from RAZ seed:

```text
linguistic.grammar_tags
linguistic.sentence_pattern_tags
content_unit.is_question
content_unit.is_imperative
text evidence
```

Recommended link type:

```text
USES_GRAMMAR_CANDIDATE
```

Not recommended yet:

```text
USES_GRAMMAR_AUTHORITY
```

Reason:

```text
RAZ grammar tags are rule-based and need resolver/validator review before becoming hard authority refs.
```

### 5.2 Vocabulary Authority

Existing artifact:

```text
ulga/graph/vocabulary_nodes.json
```

Observed node shape:

```text
id: vocabulary:cattle:v_2
node_type: vocabulary
label: cattle
cefr_level: B1
metadata.canonical_lemma
metadata.source_vocabulary_id
metadata.evp_level
metadata.frequency_rank
metadata.frequency_score
metadata.part_of_speech
```

Future linkage input from RAZ seed:

```text
linguistic.vocabulary_tags[].normalized_word
linguistic.vocabulary_tags[].pos
text tokenization
RAZ level
source book/title/page
```

Recommended link type:

```text
CONTAINS_VOCABULARY_CANDIDATE
```

Resolver should produce:

```text
exact_match
lemma_match
pos_disambiguated_match
multi_candidate_match
unresolved
blocked_function_word
blocked_non_content_token
```

### 5.3 Theme Authority

Existing artifact:

```text
ulga/graph/theme_nodes.json
```

Observed node shape:

```text
id: theme:a1_personal_information_and_greetings
node_type: theme
label: theme label
cefr_level: A1
metadata.theme_id
metadata.parent_theme
metadata.level_scope
metadata.progression_stage
```

Future linkage input from RAZ seed:

```text
theme.mapped_theme
theme.primary_theme
theme.subthemes
theme.theme_confidence
source.raz_level
book_title
```

Recommended link type:

```text
BELONGS_TO_THEME_CANDIDATE
```

Important:

```text
RAZ mapped_theme such as Home, Food, Animals, Science, Weather is not automatically the same as a Theme Authority node id.
Theme linkage requires a mapping table or resolver.
```

### 5.4 Sentence Pattern Authority

Existing artifact:

```text
ulga/graph/sentence_patterns.json
```

Observed node shape:

```text
id: pattern:PATTERN_NODE_000001
node_type: sentence_pattern
label: I am {adjective/noun_phrase}.
cefr_level: A1
metadata.canonical_pattern
metadata.normalized_pattern
metadata.pattern_family_id
metadata.pattern_type
metadata.slots
```

Future linkage input from RAZ seed:

```text
text
linguistic.sentence_pattern_tags
linguistic.grammar_tags
sentence_count
content_unit.is_question
content_unit.is_direct_speech
```

Recommended link type:

```text
MATCHES_PATTERN_CANDIDATE
```

Important:

```text
A sentence can match zero, one, or many pattern candidates.
Multi-sentence units may link to multiple pattern refs.
```

### 5.5 Chunk Authority

Existing artifact:

```text
ulga/graph/chunk_nodes.json
```

Observed node shape:

```text
id: chunk:insofar_as
node_type: chunk
label: insofar as
cefr_level: C2
metadata.normalized_chunk
metadata.safe_chunk_id
metadata.usage_class
metadata.theme_hint
metadata.priority_band
metadata.frequency_proxy_score
```

Future linkage input from RAZ seed:

```text
text
linguistic.chunk_tags
n-gram phrase extraction
```

Recommended link type:

```text
CONTAINS_CHUNK_CANDIDATE
```

Important:

```text
Chunk matching should be exact phrase / normalized phrase first.
Do not infer idiom/chunk meaning from loose word overlap.
```

---

## 6. Proposed Linkage Evidence Record

Future implementation should produce a separate derived linkage artifact, not mutate seed cards directly.

Recommended future file:

```text
raz_output_jsons/derived/linkage/raz_seed_authority_linkage_candidates.jsonl
```

Recommended record shape:

```json
{
  "linkage_record_id": "RAZ_LINK_000001",
  "seed_id": "RAZ_F_1098_REUSE_000010",
  "seed_type": "reuse_unit",
  "source": {
    "source": "RAZ",
    "raz_level": "F",
    "book_id": "1098",
    "book_title": "Does It Sink or Float?",
    "page_number": 3,
    "raw_file_path": "raz_output_jsons/Level_F/raz_F_1098_audio_timeline_extract.json",
    "derived_file_path": "raz_output_jsons/derived/Level_F/enriched/raz_F_reuse_unit_enriched.json"
  },
  "text_fingerprint": {
    "text_hash": "sha256:...",
    "normalized_text_hash": "sha256:...",
    "sentence_count": 4
  },
  "authority_linkage": {
    "grammar_refs": [],
    "vocabulary_refs": [],
    "theme_refs": [],
    "pattern_refs": [],
    "chunk_refs": []
  },
  "unresolved_authority_refs": {
    "grammar": [],
    "vocabulary": [],
    "theme": [],
    "pattern": [],
    "chunk": []
  },
  "linkage_status": "partial_linked",
  "linkage_confidence": {
    "grammar": 0.0,
    "vocabulary": 0.0,
    "theme": 0.0,
    "pattern": 0.0,
    "chunk": 0.0,
    "overall": 0.0
  },
  "linkage_policy_version": "raz_seed_authority_linkage_v1",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "review_status": "pending",
  "warnings": []
}
```

---

## 7. Authority Ref Shape

Each authority ref should keep both target node identity and match evidence.

Recommended shape:

```json
{
  "authority_family": "vocabulary",
  "target_node_id": "vocabulary:water:v_123",
  "target_node_type": "vocabulary",
  "target_label": "water",
  "target_cefr_level": "A1",
  "match_type": "exact_token_match",
  "match_surface": "water",
  "match_normalized": "water",
  "source_field": "linguistic.vocabulary_tags[].normalized_word",
  "confidence": 0.95,
  "resolver": "raz_seed_vocabulary_resolver_v1",
  "resolver_status": "matched",
  "notes": []
}
```

Allowed `resolver_status`:

```text
matched
multi_match
unresolved
blocked
needs_human_review
```

Allowed `match_type` by authority family:

```text
vocabulary:
  exact_token_match
  lemma_match
  pos_disambiguated_match
  function_word_blocked
  unresolved_token

grammar:
  exact_tag_map
  grammar_family_map
  text_rule_match
  unresolved_rule_based_tag

theme:
  exact_theme_map
  parent_theme_map
  level_scoped_theme_map
  unknown_theme

pattern:
  exact_pattern_match
  normalized_pattern_match
  slot_pattern_match
  candidate_pattern_family_match
  no_pattern_match

chunk:
  exact_chunk_match
  normalized_chunk_match
  safe_chunk_match
  overlapping_phrase_ambiguous
  no_chunk_match
```

---

## 8. Linkage Status Enum

Recommended enum:

```text
not_linked
partial_linked
linked_with_warnings
fully_linked
blocked
needs_human_review
```

Meaning:

```text
not_linked:
  no resolver has been applied

partial_linked:
  at least one authority family has matched, but one or more expected families remain unresolved

linked_with_warnings:
  links exist but include multi_match / low confidence / Unknown theme / grammar rule-based warning

fully_linked:
  all required families for the seed type have acceptable links

blocked:
  seed should not be used for downstream Content Authority binding

needs_human_review:
  resolver output is not safe enough for automated downstream binding
```

Default for S6C future implementation:

```text
partial_linked or linked_with_warnings
```

Do not default to:

```text
fully_linked
```

---

## 9. Required Authority Families by Seed Type

Different seed types require different linkage completeness.

### 9.1 Sentence seed

Minimum expected families:

```text
vocabulary
grammar or pattern
```

Optional:

```text
theme
chunk
```

Use cases:

```text
word_ordering
fill_blank
sentence-level vocabulary exposure
dictation
```

### 9.2 Page unit seed

Minimum expected families:

```text
theme
vocabulary
grammar or pattern
```

Optional:

```text
chunk
```

Use cases:

```text
short reading seed
reading comprehension seed
short answer seed
picture prompt seed
```

### 9.3 Reuse unit seed

Minimum expected families:

```text
theme
vocabulary
grammar
pattern
```

Optional but recommended:

```text
chunk
```

Use cases:

```text
short reading seed
sequencing seed
retelling seed
dialogue rewrite seed
writing model seed
assessment seed
```

Reason:

```text
reuse_unit is most likely to feed future Content Authority, so linkage requirements should be stricter.
```

---

## 10. Linkage Policy by Downstream Use

S6C should define downstream gates.

| Downstream use | Minimum linkage status | Notes |
|---|---|---|
| Query preview | partial_linked | OK for exploration |
| RAZ seed search | partial_linked | Current S6A behavior |
| Reading candidate intake | linked_with_warnings | Must expose unresolved refs |
| Dialogue rewrite candidate intake | linked_with_warnings | Direct speech / role-play requires extra review |
| Exercise seed intake | linked_with_warnings | Question type still generation hint only |
| Assessment authority intake | fully_linked or human_reviewed | Should not use unresolved grammar/vocab |
| Promotion to final content authority | human_reviewed + validator pass | Never automatic in S6C |

---

## 11. Resolver Design

Future implementation should use separate resolver modules or functions.

Recommended future file:

```text
ulga/linkage/raz_seed_authority_linkage.py
```

Recommended resolver functions:

```text
resolve_vocabulary_refs(seed_card, vocabulary_index)
resolve_grammar_refs(seed_card, grammar_index)
resolve_theme_refs(seed_card, theme_index)
resolve_pattern_refs(seed_card, pattern_index)
resolve_chunk_refs(seed_card, chunk_index)
build_raz_seed_authority_linkage(seed_card, indexes)
validate_raz_seed_authority_linkage(record)
```

Index requirements:

```text
vocabulary_index:
  by normalized lemma
  by label
  by pos where available
  by CEFR level

grammar_index:
  by canonical_grammar_key
  by grammar_family
  by grammar_subtype
  by guideword / label keyword

theme_index:
  by normalized mapped theme
  by parent_theme
  by level_scope
  by theme_id

pattern_index:
  by normalized_pattern
  by pattern_family_id
  by pattern_type
  by slot signature

chunk_index:
  by normalized_chunk
  by safe_chunk_id
  by label
```

---

## 12. Vocabulary Linkage Rules

Input fields:

```text
seed_card.linguistic.vocabulary_tags[].normalized_word
seed_card.linguistic.vocabulary_tags[].pos
seed_card.text
```

Rules:

```text
1. Normalize token case.
2. Exclude punctuation and empty tokens.
3. Allow function words to resolve only if they exist as Vocabulary Authority nodes and are useful for the downstream use case.
4. Exact normalized lemma match is preferred.
5. POS match increases confidence.
6. Multiple EVP senses must not be collapsed silently.
7. If multiple nodes match the same token, emit multi_match unless POS/level/context disambiguates.
8. Unknown token goes to unresolved_authority_refs.vocabulary.
9. RAZ level may be used as a weak tie-breaker, not as authority proof.
```

Confidence guidance:

```text
exact lemma + POS match: 0.95
exact lemma without POS: 0.80
multi-match unresolved: 0.55
function word blocked: 0.20
unresolved: 0.0
```

---

## 13. Grammar Linkage Rules

Input fields:

```text
seed_card.linguistic.grammar_tags
seed_card.linguistic.sentence_pattern_tags
seed_card.content_unit
seed_card.text
```

Rules:

```text
1. Treat RAZ grammar_tags as weak tags.
2. Map simple internal tags to Grammar Authority candidates through a controlled mapping table.
3. Do not fuzzy-search EGP labels without a mapping table.
4. Use text-level signals only as supporting evidence.
5. Unknown grammar remains unresolved.
6. A seed can have multiple grammar candidates.
```

Required mapping table in future implementation:

```text
raz_grammar_tag_to_egp_candidate_map.json
```

Example mapping direction:

```json
{
  "be_verb": {
    "grammar_family": "VERBS",
    "grammar_subtype_candidates": ["be", "linking"],
    "resolver_confidence": 0.65,
    "requires_review": true
  },
  "there_is": {
    "grammar_family": "CLAUSES",
    "label_keywords": ["there is"],
    "resolver_confidence": 0.70,
    "requires_review": true
  }
}
```

Important:

```text
Mapping table output should still be candidate refs until QA.
```

---

## 14. Theme Linkage Rules

Input fields:

```text
seed_card.theme.mapped_theme
seed_card.theme.primary_theme
seed_card.theme.subthemes
seed_card.theme.theme_confidence
seed_card.source.raz_level
```

Rules:

```text
1. Unknown theme must remain unresolved and needs_human_review.
2. Mapped theme should resolve through a theme alias map.
3. Level-scoped themes should be preferred when available.
4. Parent theme fallback may be allowed but should lower confidence.
5. Theme confidence from S4/S5 should be carried into linkage confidence.
```

Required mapping table in future implementation:

```text
raz_theme_to_ulga_theme_map.json
```

Example:

```json
{
  "Food": {
    "theme_aliases": ["food", "food and drink", "restaurant"],
    "preferred_theme_nodes": ["theme:a1_food_and_drink"],
    "fallback_parent_theme": "Food",
    "resolver_confidence": 0.85
  },
  "Unknown": {
    "preferred_theme_nodes": [],
    "resolver_confidence": 0.0,
    "requires_human_review": true
  }
}
```

---

## 15. Pattern Linkage Rules

Input fields:

```text
seed_card.text
seed_card.linguistic.sentence_pattern_tags
seed_card.linguistic.grammar_tags
```

Rules:

```text
1. Sentence seeds may match one pattern.
2. Page/reuse units may match multiple patterns, one per sentence.
3. Pattern matching must preserve sentence order.
4. Slot inference should be conservative.
5. Do not mark a pattern ref as final unless normalized pattern match or reviewed slot match exists.
6. If no pattern is found, add unresolved pattern diagnostic.
```

Recommended future output shape:

```json
{
  "target_node_id": "pattern:PATTERN_NODE_000001",
  "match_type": "slot_pattern_match",
  "match_surface": "I am happy.",
  "matched_sentence_index": 0,
  "confidence": 0.72,
  "resolver_status": "matched"
}
```

---

## 16. Chunk Linkage Rules

Input fields:

```text
seed_card.text
seed_card.linguistic.chunk_tags
```

Rules:

```text
1. Exact normalized chunk match first.
2. Longest phrase match should win over shorter overlap.
3. Ambiguous overlapping phrase should produce warning.
4. Do not infer chunk from non-contiguous word overlap.
5. Chunk refs are optional for sentence/page seeds but useful for dialogue/writing seeds.
```

---

## 17. G/H/I and Future Level Expansion

S6C must not assume A-F forever.

Current S6A implementation has:

```text
LEVELS = ("A", "B", "C", "D", "E", "F")
```

This is acceptable for current S6A/S6B because only A-F were QA-confirmed.

Future expansion should be append-only:

```text
A-F remains unchanged.
G/H/I are added as new derived level folders.
Query layer discovers or registers new levels.
Reports rebuild coverage.
S6 QA reruns.
S11 content authority schema consumes level as data, not as hard-coded enum.
```

Recommended next implementation after S11C, or before G/H/I ingestion:

```text
RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation
```

Design requirements:

```text
1. Discover Level_* folders dynamically, or read from a level registry.
2. Preserve allowlist mode for QA-certified levels.
3. Report discovered_levels and query_enabled_levels separately.
4. Do not auto-enable unvalidated levels for downstream Content Authority binding.
5. G/H/I should enter with validation_status=pending until S4/S5/S6 QA passes.
```

Recommended level registry shape:

```json
{
  "source": "RAZ",
  "levels": [
    {
      "level": "A",
      "derived_path": "raz_output_jsons/derived/Level_A",
      "query_enabled": true,
      "qa_status": "PASS",
      "authority_binding_allowed": true
    },
    {
      "level": "G",
      "derived_path": "raz_output_jsons/derived/Level_G",
      "query_enabled": false,
      "qa_status": "pending",
      "authority_binding_allowed": false
    }
  ]
}
```

Important:

```text
Level expansion should not require rewriting A-F seed records.
```

---

## 18. S11C Schema Requirements From S6C

ULGA-S11C should reserve these fields.

### 18.1 Source seed refs

```json
{
  "source_seed_refs": [
    {
      "seed_id": "RAZ_F_1098_REUSE_000010",
      "seed_type": "reuse_unit",
      "source": "RAZ",
      "source_level": "F",
      "source_book_id": "1098",
      "source_page_number": 3,
      "seed_query_trace_id": "optional"
    }
  ]
}
```

### 18.2 Authority refs

```json
{
  "authority_refs": {
    "grammar_refs": [],
    "vocabulary_refs": [],
    "theme_refs": [],
    "pattern_refs": [],
    "chunk_refs": []
  }
}
```

### 18.3 Linkage status

```json
{
  "authority_linkage_status": "partial_linked",
  "authority_linkage_policy_version": "raz_seed_authority_linkage_v1",
  "unresolved_authority_refs": {
    "grammar": [],
    "vocabulary": [],
    "theme": [],
    "pattern": [],
    "chunk": []
  },
  "authority_linkage_warnings": []
}
```

### 18.4 Promotion boundary

```json
{
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "review_status": "pending",
  "final_eligible": false
}
```

S11C must not require:

```text
fully_linked
promoted
human_reviewed
```

for first schema implementation.

Reason:

```text
S11C should be able to store candidate Reading/Dialogue records while preserving unresolved authority refs.
```

---

## 19. Validator Contract for Future S6C Implementation

Future validator should check:

```text
1. Every linkage record has seed_id and seed_type.
2. seed_id exists in S6 seed query layer output.
3. authority_refs families are present.
4. unresolved_authority_refs families are present.
5. linkage_status is from enum.
6. authority_status remains candidate_only.
7. promotion_status remains not_promoted.
8. Unknown theme does not produce theme_refs.
9. unresolved Unknown theme produces needs_human_review or warning.
10. Vocabulary multi-match is not silently collapsed.
11. Grammar rule-based tag is not marked as authority-final.
12. Pattern refs preserve sentence index where applicable.
13. G/H/I levels are either query_enabled=false or qa_status PASS before downstream binding.
14. No generated Reading/Dialogue content appears in linkage records.
15. No raw or derived RAZ input files are mutated.
```

Suggested future report:

```text
ulga/reports/raz_seed_authority_linkage_summary.json
ulga/reports/raz_seed_authority_linkage_validation.json
```

Suggested metrics:

```text
total_seed_cards_seen
linkage_records_created
fully_linked_count
partial_linked_count
linked_with_warnings_count
needs_human_review_count
blocked_count
unresolved_vocabulary_count
unresolved_grammar_count
unresolved_theme_count
unresolved_pattern_count
unresolved_chunk_count
multi_match_vocabulary_count
unknown_theme_count
by_level
by_seed_type
by_authority_family
```

---

## 20. What S6C Does Not Decide

S6C should not decide:

```text
which seed becomes a final reading
which seed becomes a final dialogue
which generated rewrite is acceptable
which learner should receive which seed
which RAZ level equals which CEFR level
which unresolved grammar should be accepted
which candidate should be promoted
```

Those belong to later layers:

```text
S11C Reading/Dialogue Content Authority schema
S11D/S12 builders and validators
Assessment Authority
Learning Opportunity binding
Antigravity Planner
Human review / promotion gate
```

---

## 21. Recommended Implementation Roadmap

Recommended sequence:

```text
RAZ-S6C_SeedQueryAuthorityLinkage_DesignScan
↓
ULGA-S11C_ReadingDialogueContentAuthority_SchemaImplementation
↓
RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation
↓
RAZ-S6E_LevelExpansion_QA
↓
RAZ-S6F_SeedAuthorityLinkage_Implementation
↓
RAZ-S6G_SeedAuthorityLinkage_QA
```

Rationale:

```text
S6C defines contract.
S11C reserves proper schema fields.
S6D prevents A-F hardcoding before G/H/I expansion.
S6F implements actual linking after schema and level expansion boundaries are stable.
```

Alternative if S11C needs to start immediately:

```text
Use S6C fields as schema placeholders.
Do not require actual authority linkage implementation yet.
Store linkage_status = not_linked or partial_linked.
Store unresolved_authority_refs explicitly.
```

---

## 22. Final Recommendation

Proceed next with:

```text
ULGA-S11C_ReadingDialogueContentAuthority_SchemaImplementation
```

But S11C must follow the S6C contract:

```text
- preserve source_seed_refs
- reserve authority_refs
- reserve unresolved_authority_refs
- reserve authority_linkage_status
- keep candidate_only boundary
- do not hard-code RAZ A-F as the only possible levels
- do not require fully_linked before candidate content records can exist
```

---

## 23. Closeout Marker

```text
RAZ-S6C_SeedQueryAuthorityLinkage_DesignScan_COMPLETE
```
