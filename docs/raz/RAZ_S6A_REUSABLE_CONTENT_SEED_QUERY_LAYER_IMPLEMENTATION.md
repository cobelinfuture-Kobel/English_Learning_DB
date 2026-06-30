# RAZ-S6A Reusable Content Seed Query Layer Implementation

## 1. Preflight

Task: `RAZ-S6A_ReusableContentSeed_QueryLayer_Implementation`

Workspace:

```text
E:\Devspace_Test\English_Learning_DB
```

Implementation type:

```text
STATIC / OFFLINE QUERY LAYER
FULL STAGE-APPROPRIATE IMPLEMENTATION
NO RUNTIME/API INTEGRATION
NO RAW JSON MUTATION
NO DERIVED RAZ OUTPUT MUTATION
NO AUTHORITY PROMOTION
NO CONTENT GENERATION
```

Design source:

```text
docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md
```

Files created:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
tests/ulga/test_raz_reusable_content_seed_query_layer.py
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
docs/raz/RAZ_S6A_REUSABLE_CONTENT_SEED_QUERY_LAYER_IMPLEMENTATION.md
```

Files modified:

```text
ulga/query/__init__.py
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
ulga/graph/**/*.json
```

Risk level:

```text
Low
```

---

## 2. Implemented Query Layer

Implemented module:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
```

Primary responsibility:

```text
Load RAZ A-F enriched sentence/page/reuse records and expose them as static reusable content seed cards.
```

The query layer returns candidate seeds only. It does not generate, rewrite, promote, or mutate content.

Public functions:

```text
query_reusable_content_seeds
find_reusable_seeds
find_short_reading_seeds
find_exercise_seeds
find_dialogue_rewrite_seeds
find_picture_prompt_seeds
find_theme_seeds
explain_seed
load_seed_cards
generate_summary_report
```

Export update:

```text
ulga/query/__init__.py now exports the RAZ seed query functions under explicit RAZ seed names.
Existing S10 static candidate query exports were preserved.
```

---

## 3. Seed Card Contract

Each result is normalized into a compact seed card:

```text
seed_id
seed_type
source
text_preview
text
content_unit
theme
linguistic
pedagogy
qa
ranking
```

Authority boundary enforced on every returned card:

```text
authority_status: candidate_only
promotion_status: not_promoted
final_eligible: false
generated_content_returned: false
authority_promotion_allowed: false
```

---

## 4. Query Types Implemented

```text
find_reusable_seeds
find_short_reading_seeds
find_exercise_seeds
find_dialogue_rewrite_seeds
find_picture_prompt_seeds
find_theme_seeds
explain_seed
```

Default behavior:

```text
find_short_reading_seeds:
  record_types = page_unit / reuse_unit
  reusability_tags includes short_reading_seed
  min_sentence_count = 2

find_exercise_seeds:
  reusability_tags includes exercise_seed

find_dialogue_rewrite_seeds:
  record_types = page_unit / reuse_unit
  reusability_tags includes dialogue_rewrite_seed

find_picture_prompt_seeds:
  record_types = sentence / page_unit
  levels = A / B / C
  reusability_tags includes picture_prompt_seed

find_theme_seeds:
  mapped_theme is required by wrapper call
```

---

## 5. Request Guardrails

Implemented rejected request keys:

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

Implemented rejection codes:

```text
STATIC_ONLY_REQUIRED
ADAPTIVE_FIELD_REJECTED
INVALID_RECORD_TYPE_FILTER
INVALID_LEVEL_FILTER
UNKNOWN_QUERY_TYPE
SEED_NOT_FOUND
```

Default exclusion policy:

```text
Unknown theme: excluded unless include_unknown_theme=true
section heading: excluded unless include_heading=true
needs_human_review: excluded unless include_human_review_required=true
unknown_grammar: allowed unless grammar_strict=true
```

Warnings emitted by default:

```text
GENERATED_CONTENT_NOT_RETURNED
AUTHORITY_PROMOTION_NOT_ALLOWED
CEFR_NOT_AUTHORITY_LINKED
```

---

## 6. Ranking Policy

Local seed scoring was implemented for retrieval utility.

Score is based on:

```text
base static candidate score
reusability tag match
question type match
skill match
theme match
theme confidence
multi-sentence fit
reuse_unit preference
warning penalty
unknown theme penalty if explicitly included
```

Important boundary:

```text
seed_score is retrieval utility only.
seed_score is not CEFR confidence.
seed_score is not authority strength.
seed_score is not learner personalization.
```

---

## 7. Validator

Implemented validator:

```text
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
```

Validator checks:

```text
public functions exist
warning registry exists
A-F coverage exists
sample query responses are valid
seed card required fields exist
static_only false is rejected
learner/adaptive fields are rejected
invalid record_type is rejected
unknown query_type is rejected
summary report can be generated
validation report can be generated
```

Validator output path:

```text
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
```

---

## 8. Tests

Implemented tests:

```text
tests/ulga/test_raz_reusable_content_seed_query_layer.py
```

Coverage:

```text
load_seed_cards
short reading query
exercise seed query
theme query
explain_seed
static-only rejection
adaptive/generation request rejection
Unknown theme exclusion by default
Unknown theme inclusion by explicit request
heading / human-review exclusion by default
```

Test command run:

```text
python -m py_compile ulga/query/raz_reusable_content_seed_query_layer.py ulga/validators/validate_raz_reusable_content_seed_query_layer.py tests/ulga/test_raz_reusable_content_seed_query_layer.py && python -m unittest tests.ulga.test_raz_reusable_content_seed_query_layer
```

Result:

```text
Ran 6 tests in 0.659s
OK
```

---

## 9. Real Derived Data Smoke Query

Read-only smoke query was run against current A-F derived enriched data.

Seed cards loaded:

```text
14422
```

Coverage matrix:

| Level | sentence | page_unit | reuse_unit | total |
|---|---:|---:|---:|---:|
| A | 808 | 804 | 4 | 1616 |
| B | 829 | 802 | 27 | 1658 |
| C | 1064 | 808 | 248 | 2120 |
| D | 1180 | 735 | 389 | 2304 |
| E | 1670 | 904 | 619 | 3193 |
| F | 1936 | 872 | 723 | 3531 |

Sample query results:

| Query | Matches before paging | First seed |
|---|---:|---|
| find_short_reading_seeds | 3606 | RAZ_F_89_REUSE_000007 |
| find_exercise_seeds / reading_comprehension | 12316 | RAZ_F_89_REUSE_000007 |
| find_theme_seeds / Science page-reuse | 213 | RAZ_F_1098_REUSE_000010 |
| find_picture_prompt_seeds | 2873 | RAZ_B_2342_P009 |
| find_dialogue_rewrite_seeds | 597 | RAZ_F_92_REUSE_000008 |

Smoke result:

```text
PASS
```

---

## 10. Reports

Created:

```text
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
```

Summary confirms:

```text
total_seed_cards: 14422
sentence: 7487
page_unit: 4925
reuse_unit: 2010
raw_mutation: false
derived_output_mutation: false
authority_promotion: false
```

Validation confirms:

```text
status: PASS
required_public_functions: present
warning_registry_complete: true
sample query checks: PASS
rejected request checks: PASS
seed_card_contract: PASS
test_result: PASS
```

---

## 11. Known Limitations

```text
1. Grammar and vocabulary filters remain rule-based because S4 enriched tags are not yet linked to EGP/EVP authorities.
2. CEFR is not authority-linked in RAZ seed cards.
3. Unknown theme records are available only by explicit request.
4. Listening seed only means source audio may exist; enriched text output does not carry final audio authority.
5. Query layer returns seeds only; it does not generate exercises, dialogues, or readings.
6. S6A does not bind seeds to Learning Opportunity yet.
```

---

## 12. Recommended Next Task

Recommended next task:

```text
RAZ-S6B_ReusableContentSeed_QueryLayer_QA
```

Suggested QA scope:

```text
1. Run validator directly.
2. Compare summary/validation reports.
3. Sample top seed cards by query type.
4. Confirm Unknown theme and heading exclusion behavior.
5. Confirm no mutation of raw or derived RAZ outputs.
6. Confirm generated content / promotion guardrails.
```

After S6B passes, recommended follow-up:

```text
ULGA-S11C_ReadingDialogueContentAuthority_SchemaImplementation
```

Reason:

```text
S6A now provides stable RAZ seed retrieval for future Reading / Dialogue authority work.
```

---

## 13. Closeout Marker

```text
RAZ-S6A_ReusableContentSeed_QueryLayer_Implementation_PASS
```
