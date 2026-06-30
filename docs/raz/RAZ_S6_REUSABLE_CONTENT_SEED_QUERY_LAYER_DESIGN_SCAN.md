# RAZ-S6 Reusable Content Seed Query Layer Design Scan

## 1. Preflight

Task: `RAZ-S6_ReusableContentSeed_QueryLayer_DesignScan`

Workspace:

```text
E:\Devspace_Test\English_Learning_DB
```

Scope:

```text
DESIGN SCAN ONLY
READ-ONLY ANALYSIS
NO QUERY IMPLEMENTATION
NO DERIVED OUTPUT MUTATION
NO RAW JSON MUTATION
NO AUTHORITY PROMOTION
NO EXERCISE / DIALOGUE / READING GENERATION
```

Files inspected:

```text
docs/ulga/ULGA_S10I_STATIC_CANDIDATE_QUERY_LAYER_DESIGN_SCAN.md
docs/ulga/ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
ulga/query/static_candidate_query_layer.py
raz_output_jsons/derived/reports/raz_tagging_schema_validation.json
raz_output_jsons/derived/reports/raz_tagging_summary.json
raz_output_jsons/derived/reports/raz_tagging_warnings.json
raz_output_jsons/derived/Level_*/enriched/*.json
raz_output_jsons/derived/Level_*/enriched/*.jsonl
```

Files created:

```text
docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md
```

Files intentionally not modified:

```text
tools/raz_normalized_tagging_pipeline.py
tests/test_raz_normalized_tagging_pipeline.py
RAZ_BookID.py
BookID_prompt.txt
raz_output_jsons/Level_*/**/*.json
raz_output_jsons/derived/**/*.json
raz_output_jsons/derived/**/*.jsonl
ulga/query/**/*.py
ulga/validators/**/*.py
ulga/graph/**/*.json
ulga/reports/**/*.json
```

Risk level:

```text
Low
```

---

## 2. Upstream Readiness

S6 depends on S4/S5A/S5B outputs.

Current derived report status:

```text
schema.status: PASS
schema.error_count: 0
summary.dry_run: false
summary.raw_files_seen: 566
sentence_enriched_count: 7487
page_unit_enriched_count: 4925
reuse_unit_enriched_count: 2010
warning_count: 2463
```

Authority boundary:

```text
authority_status: candidate_only
raw_mutation: false
audio_policy: audio_fields_removed_from_normalized_and_enriched_text_outputs
```

S6 conclusion:

```text
RAZ enriched candidate layer is query-ready for a first reusable-content seed query layer.
```

Important constraint:

```text
Query-ready does not mean authority-promoted.
All query results remain candidate seeds.
```

---

## 3. Available Candidate Universe

S6 should treat three enriched record families as queryable content units:

| Record family | Count | Main use |
|---|---:|---|
| sentence_enriched | 7487 | word ordering, fill blank, sentence-level grammar/vocabulary exposure, dictation seed |
| page_unit_enriched | 4925 | page-level reading seed, comprehension seed, short answer seed |
| reuse_unit_enriched | 2010 | multi-sentence reusable seed, sequencing seed, retelling seed, reading/writing model seed |

Total queryable enriched units:

```text
14422
```

Level distribution across all three families:

| Level | Queryable units |
|---|---:|
| A | 1616 |
| B | 1658 |
| C | 2120 |
| D | 2304 |
| E | 3193 |
| F | 3531 |

Interpretation:

```text
A/B are sentence-heavy and simple.
C/D begin to provide strong reusable short-reading value.
E/F provide the strongest multi-sentence and retelling/query value, but require stronger QA filtering.
```

---

## 4. Queryable Tag Fields

S6 query layer should index and filter these fields.

### 4.1 Source fields

```text
source_tags.source
source_tags.source_type
source_tags.extraction_method
source_tags.extractor_version
source_tags.raz_level
source_tags.book_id
source_tags.book_title
source_tags.page_number
source_tags.page_unit_id
source_tags.candidate_id
source_tags.raw_file_path
```

Use cases:

```text
- retrieve all units from one book
- retrieve by level
- retrieve by page range
- trace a result back to raw evidence
```

### 4.2 Content-unit fields

```text
content_unit_tags.content_unit_type
content_unit_tags.sentence_authority_eligible
content_unit_tags.is_story_sentence
content_unit_tags.is_heading
content_unit_tags.is_direct_speech
content_unit_tags.is_question
content_unit_tags.is_imperative
content_unit_tags.sentence_count
content_unit_tags.has_multi_sentence_unit
content_unit_tags.has_direct_speech
content_unit_tags.has_sequence
content_unit_tags.has_heading
```

Use cases:

```text
- include only sentence records
- include only multi_sentence_unit records
- exclude section_heading
- find direct speech for dialogue rewrite candidates
- find sequence-bearing units for sequencing exercises
```

### 4.3 Theme fields

```text
theme_tags.primary_theme
theme_tags.mapped_theme
theme_tags.subthemes
theme_tags.theme_confidence
theme_tags.theme_source
```

Current theme distribution across queryable units:

| Theme | Count |
|---|---:|
| Animals | 2125 |
| Unknown | 2038 |
| Math | 1404 |
| Food | 988 |
| Home | 855 |
| Nature | 821 |
| DailyRoutine | 588 |
| Weather | 498 |
| Transportation | 476 |
| School | 472 |
| Travel | 438 |
| Science | 424 |
| Feelings | 383 |
| Body | 374 |
| Actions | 371 |
| StoryFable | 313 |
| Pets | 311 |
| Holidays | 292 |
| Health | 288 |
| Clothing | 209 |

Query rule:

```text
Default query should exclude Unknown theme unless allow_unknown_theme=true.
```

Reason:

```text
Unknown theme still has 2038 records and can reduce query precision.
```

### 4.4 Linguistic fields

```text
linguistic_tags.raz_level
linguistic_tags.grammar_tags
linguistic_tags.sentence_pattern_tags
linguistic_tags.vocabulary_tags[].normalized_word
linguistic_tags.vocabulary_tags[].pos
linguistic_tags.vocabulary_tags[].lookup_status
linguistic_tags.chunk_tags
```

Current limitation:

```text
Grammar and vocabulary fields are rule-based.
Vocabulary is not yet linked to EVP/NGSL authority.
Grammar is not yet linked to EGP/Grammar Authority.
```

Query rule:

```text
Grammar/vocabulary filters are allowed as soft filters.
They must not be presented as final authority evidence.
```

### 4.5 Pedagogical fields

```text
pedagogical_tags.skill_area
pedagogical_tags.question_type_candidates
pedagogical_tags.exercise_seed
pedagogical_tags.assessment_seed
```

Current skill distribution:

| Skill | Count |
|---|---:|
| reading | 14422 |
| vocabulary | 14422 |
| grammar | 14388 |
| listening | 6806 |
| comprehension | 4020 |
| retelling | 4020 |
| speaking | 1266 |

Current question-type distribution:

| Question type | Count |
|---|---:|
| reading_comprehension | 14422 |
| fill_blank | 14388 |
| word_ordering | 14388 |
| dictation | 6806 |
| listening_choice | 6806 |
| retelling_prompt | 4020 |
| sentence_ordering | 4020 |
| short_answer | 4020 |
| speaking_response | 1266 |

Query rule:

```text
question_type_candidates are generation hints, not generated questions.
S6 must return seeds, not actual exercises.
```

### 4.6 Reuse fields

```text
reuse_tags.is_reusable_unit
reuse_tags.reusability_tags
reuse_tags.derivation_potential.short_reading
reuse_tags.derivation_potential.writing_model
reuse_tags.derivation_potential.dialogue_rewrite
reuse_tags.derivation_potential.exercise_generation
reuse_tags.derivation_potential.listening_audio
```

Current reusability distribution:

| Reusability tag | Count |
|---|---:|
| future_unknown_use | 14422 |
| exercise_seed | 14388 |
| grammar_pattern_seed | 14388 |
| vocabulary_exposure_seed | 14388 |
| listening_audio_seed | 6806 |
| assessment_seed | 4020 |
| comprehension_question_seed | 4020 |
| retelling_seed | 4020 |
| sequencing_seed | 4020 |
| short_reading_seed | 4020 |
| picture_prompt_seed | 3274 |
| dialogue_rewrite_seed | 1266 |

Derivation potential summary:

```text
short_reading=high: 4020
writing_model=medium: 4020
dialogue_rewrite=possible: 1266
exercise_generation=high: 4020
exercise_generation=possible: 10402
listening_audio=possible: 6806
listening_audio=unknown: 7616
```

Query rule:

```text
For high-value reusable seeds, prefer page_unit/reuse_unit with:
- short_reading=high
- exercise_generation=high
- sentence_count >= 2
- has_heading=false
- mapped_theme != Unknown
```

### 4.7 QA fields

```text
qa_tags.authority_status
qa_tags.promotion_status
qa_tags.review_status
qa_tags.tagging_status
qa_tags.needs_human_review
qa_tags.final_eligible
qa_tags.confidence.content_unit_type
qa_tags.confidence.theme
qa_tags.confidence.grammar
qa_tags.confidence.vocabulary
qa_tags.confidence.pattern
qa_tags.warnings
```

Current QA warning distribution from enriched records:

| Warning | Count |
|---|---:|
| unknown_theme | 2038 |
| unknown_pattern | 549 |
| unknown_grammar | 391 |
| section_heading_detected | 34 |

Query rule:

```text
Default query should exclude records where needs_human_review=true.
Default query should exclude section_heading records.
Default query should allow unknown_grammar only if grammar_strict=false.
Default query should exclude unknown_theme unless allow_unknown_theme=true.
```

---

## 5. S6 Query Layer Goal

S6 query layer should answer one question:

```text
Given a teaching / content-generation need, which RAZ enriched candidate seeds are safe and useful enough to retrieve?
```

It should not answer:

```text
What final content should be published?
What final questions should be generated?
Which record is authoritative?
Which grammar/vocabulary fact is canonically true?
```

S6 output is a ranked list of candidate seeds with explanation and guardrails.

---

## 6. Proposed Output Objects

S6 should not directly expose full enriched records by default. It should return compact seed cards.

### 6.1 `ReusableContentSeedCard`

```json
{
  "seed_id": "RAZ_F_1098_P003",
  "seed_type": "page_unit",
  "source": {
    "source": "RAZ",
    "raz_level": "F",
    "book_id": "1098",
    "book_title": "Does It Sink or Float?",
    "page_number": 3,
    "raw_file_path": "raz_output_jsons/Level_F/raz_F_1098_audio_timeline_extract.json"
  },
  "text_preview": "Some things sink in water...",
  "text": "optional_if_include_text_true",
  "content_unit": {
    "content_unit_type": "multi_sentence_unit",
    "sentence_count": 4,
    "has_heading": false,
    "has_direct_speech": false,
    "has_sequence": false
  },
  "theme": {
    "mapped_theme": "Science",
    "primary_theme": "Science",
    "subthemes": ["physical_science"],
    "theme_confidence": 0.92
  },
  "pedagogy": {
    "skill_area": ["reading", "vocabulary", "grammar", "comprehension", "retelling"],
    "question_type_candidates": ["reading_comprehension", "sentence_ordering", "retelling_prompt"],
    "reusability_tags": ["short_reading_seed", "sequencing_seed", "retelling_seed"]
  },
  "qa": {
    "authority_status": "candidate_only",
    "promotion_status": "not_promoted",
    "review_status": "pending",
    "final_eligible": false,
    "needs_human_review": false,
    "warnings": []
  },
  "ranking": {
    "seed_score": 0.0,
    "score_reasons": []
  }
}
```

### 6.2 `ReusableSeedQueryResponse`

```json
{
  "query_status": "PASS",
  "query_type": "find_reusable_seeds",
  "filters_applied": {},
  "guardrails": {
    "authority_promotion_allowed": false,
    "generated_content_returned": false,
    "unknown_theme_policy": "exclude_by_default",
    "section_heading_policy": "exclude_by_default"
  },
  "result_count": 0,
  "limit": 20,
  "offset": 0,
  "results": [],
  "warnings": []
}
```

---

## 7. Proposed Query Types

### 7.1 `find_reusable_seeds`

Purpose:

```text
General search across sentence/page/reuse enriched records.
```

Core filters:

```text
levels
record_types
mapped_themes
skill_area
question_type_candidates
reusability_tags
min_sentence_count
max_sentence_count
has_direct_speech
has_sequence
include_unknown_theme
include_heading
include_human_review_required
```

### 7.2 `find_short_reading_seeds`

Default filter:

```text
record_types in [page_unit, reuse_unit]
reusability_tags includes short_reading_seed
sentence_count >= 2
has_heading=false
mapped_theme != Unknown
needs_human_review=false
```

Use cases:

```text
short reading passage
reading comprehension seed
guided writing model seed
retelling input
```

### 7.3 `find_exercise_seeds`

Default filter:

```text
reusability_tags includes exercise_seed
question_type_candidates intersects requested question types
content_unit_type != section_heading
mapped_theme != Unknown unless explicitly allowed
```

Use cases:

```text
fill_blank
word_ordering
sentence_ordering
short_answer
reading_comprehension
```

### 7.4 `find_dialogue_rewrite_seeds`

Default filter:

```text
reusability_tags includes dialogue_rewrite_seed
or content_unit_tags.has_direct_speech=true
record_types in [page_unit, reuse_unit]
needs_human_review=false
```

Use cases:

```text
future dialogue rewrite candidate selection
role-play source selection
speaking-response prompt seed
```

### 7.5 `find_picture_prompt_seeds`

Default filter:

```text
reusability_tags includes picture_prompt_seed
record_types in [sentence, page_unit]
level in [A, B, C]
content_unit_type != section_heading
```

Use cases:

```text
picture description sentence seed
simple image prompt design
A1 speaking support
```

### 7.6 `find_theme_seeds`

Default filter:

```text
mapped_theme in requested themes
mapped_theme != Unknown
sort by theme_confidence desc, seed_score desc
```

Use cases:

```text
Animals reading set
Food writing model set
Weather comprehension set
School vocabulary exposure set
```

### 7.7 `explain_seed`

Purpose:

```text
Return full provenance and why a seed was selected.
```

Must include:

```text
source_tags
content_unit_tags
theme_tags
pedagogical_tags
reuse_tags
qa_tags
score reasons
known limitations
```

---

## 8. Proposed Request Schema

```json
{
  "query_type": "find_reusable_seeds",
  "filters": {
    "levels": ["C", "D", "E", "F"],
    "record_types": ["page_unit", "reuse_unit"],
    "mapped_themes": ["Animals", "Food"],
    "skill_area": ["reading", "comprehension"],
    "question_type_candidates": ["reading_comprehension", "short_answer"],
    "reusability_tags": ["short_reading_seed", "comprehension_question_seed"],
    "min_sentence_count": 2,
    "max_sentence_count": 6,
    "has_direct_speech": null,
    "has_sequence": null,
    "include_unknown_theme": false,
    "include_heading": false,
    "include_human_review_required": false,
    "grammar_strict": false
  },
  "ranking_policy": {
    "prefer_higher_theme_confidence": true,
    "prefer_multi_sentence": true,
    "prefer_reuse_unit": true,
    "prefer_lower_warning_count": true,
    "prefer_level_band": ["C", "D", "E"]
  },
  "limit": 20,
  "offset": 0,
  "include_text": true,
  "include_explanation": true
}
```

Forbidden request keys:

```text
learner_id
student_id
mastery
learner_state
adaptive
personalized
assessment_feedback
event_log
runtime_profile
promote_to_authority
generate_exercise
generate_dialogue
generate_reading
```

Reason:

```text
S6 is static/offline candidate seed retrieval.
It must not depend on learner state or produce generated content.
```

---

## 9. Ranking Policy Design

S6 ranking is not the same as ULGA S10 static ranking.

S6 seed score should be local to RAZ reusable content retrieval.

Proposed scoring components:

| Component | Direction | Rationale |
|---|---|---|
| authority safety | required | candidate_only, not_promoted, final_eligible=false |
| content type fit | positive | page/reuse units preferred for reading; sentence preferred for word ordering |
| reusability tag match | positive | direct match to requested teaching use |
| question type match | positive | direct match to requested exercise type |
| theme match | positive | exact mapped_theme match |
| theme confidence | positive | reduce noisy theme results |
| sentence count fit | positive | match target granularity |
| warning count | negative | prefer cleaner seeds |
| heading / human-review flag | exclusion by default | avoid non-story heading pollution |
| unknown_theme | exclusion by default | improve precision |

Suggested score shape:

```text
seed_score = base_match_score
           + reusability_match_bonus
           + pedagogy_match_bonus
           + theme_confidence_bonus
           + sentence_count_fit_bonus
           - warning_penalty
```

Important:

```text
S6 score is retrieval utility score.
It is not CEFR level.
It is not authority strength.
It is not learner personalization.
```

---

## 10. Guardrails

Default guardrails:

```text
1. Never return promoted=true.
2. Never mutate candidate records.
3. Never write generated content.
4. Never treat RAZ candidate seed as final authority.
5. Exclude section_heading by default.
6. Exclude needs_human_review by default.
7. Exclude Unknown theme by default.
8. Clamp limit to a maximum, recommended MAX_LIMIT=100.
9. Reject learner/adaptive request keys.
10. Return warnings when soft filters are used.
```

Warning codes to define in S6:

```text
UNKNOWN_THEME_EXCLUDED_BY_DEFAULT
UNKNOWN_THEME_INCLUDED_BY_REQUEST
SECTION_HEADING_EXCLUDED_BY_DEFAULT
HUMAN_REVIEW_REQUIRED_EXCLUDED_BY_DEFAULT
GRAMMAR_FILTER_IS_RULE_BASED
VOCABULARY_FILTER_IS_RULE_BASED
CEFR_NOT_AUTHORITY_LINKED
LIMIT_CLAMPED_TO_MAXIMUM
NO_RESULTS_FOUND
STATIC_ONLY_REQUIRED
GENERATED_CONTENT_NOT_RETURNED
AUTHORITY_PROMOTION_NOT_ALLOWED
```

---

## 11. Output Directory Proposal for Future Implementation

Recommended future files:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
tests/ulga/test_raz_reusable_content_seed_query_layer.py
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
docs/raz/RAZ_S6A_REUSABLE_CONTENT_SEED_QUERY_LAYER_IMPLEMENTATION.md
```

Reason for placing implementation under `ulga/query`:

```text
RAZ is a supporting corpus, but the retrieval behavior should align with ULGA's static query-layer contract.
```

Reason for keeping source data under `raz_output_jsons/derived`:

```text
RAZ enriched data is still candidate evidence, not graph authority.
```

---

## 12. Contract With S11 Reading / Dialogue Authority

S6 should feed future S11 content work as a candidate seed retriever.

S6 -> Reading:

```text
find_short_reading_seeds
find_theme_seeds
find_exercise_seeds with reading_comprehension / short_answer
```

S6 -> Dialogue:

```text
find_dialogue_rewrite_seeds
find_direct_speech_candidates
find_speaking_response_seeds
```

S6 -> Assessment / Wrong-question analysis:

```text
find_exercise_seeds
filter by question_type_candidates
filter by grammar_tags / vocabulary_tags / theme_tags
```

Boundary:

```text
S6 supplies seed candidates only.
S11 or later layers decide whether to transform, review, or promote content.
```

---

## 13. Known Limitations

```text
1. Theme coverage is good enough for first query-layer use but not complete.
2. Unknown theme remains 2038 records.
3. Grammar tags are rule-based and not EGP-authority-linked.
4. Vocabulary tags are tokenized and not EVP/NGSL-authority-linked.
5. Audio has been stripped from normalized/enriched text outputs; listening seed means source audio may exist, not final listening authority.
6. question_type_candidates are hints, not generated tasks.
7. Reuse scores are local retrieval scores, not pedagogical mastery scores.
8. RAZ level is not identical to CEFR level.
```

---

## 14. Implementation Readiness

Ready for implementation:

```text
YES
```

Reason:

```text
- Derived A-F enriched files exist.
- Schema validation passed.
- Candidate counts are stable.
- Tags are sufficient for first retrieval layer.
- S10 static query layer offers a pattern for static-only query contract.
- S11 Reading/Dialogue authority needs seed selection support.
```

Recommended next task:

```text
RAZ-S6A_ReusableContentSeed_QueryLayer_Implementation
```

Implementation priority:

```text
1. Load all Level_A-F enriched sentence/page/reuse files.
2. Normalize records into internal seed cards.
3. Implement static-only request validation.
4. Implement query functions.
5. Implement guardrail warnings.
6. Implement local retrieval scoring.
7. Add validator and unit tests.
8. Add summary and validation reports.
```

Do not implement yet:

```text
exercise generation
dialogue generation
reading passage generation
candidate promotion
learner-state personalization
runtime/API integration
```

---

## 15. Closeout Marker

```text
RAZ-S6_ReusableContentSeed_QueryLayer_DesignScan_COMPLETE
```
