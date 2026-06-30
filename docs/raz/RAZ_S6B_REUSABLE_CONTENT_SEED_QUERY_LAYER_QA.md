# RAZ-S6B Reusable Content Seed Query Layer QA

## 1. Preflight

Task: `RAZ-S6B_ReusableContentSeed_QueryLayer_QA`

Workspace:

```text
E:\Devspace_Test\English_Learning_DB
```

QA type:

```text
STATIC / OFFLINE QUERY QA
NO NEW QUERY FEATURE
NO RAW JSON MUTATION
NO DERIVED RAZ OUTPUT MUTATION
NO AUTHORITY PROMOTION
NO CONTENT GENERATION
```

Files inspected / executed:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
tests/ulga/test_raz_reusable_content_seed_query_layer.py
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
raz_output_jsons/derived/Level_*/enriched/*.json
raz_output_jsons/derived/Level_*/enriched/*.jsonl
```

Files created:

```text
docs/raz/RAZ_S6B_REUSABLE_CONTENT_SEED_QUERY_LAYER_QA.md
```

Files updated by validator/report refresh:

```text
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
```

Files intentionally not modified:

```text
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
tests/ulga/test_raz_reusable_content_seed_query_layer.py
ulga/query/__init__.py
tools/raz_normalized_tagging_pipeline.py
raz_output_jsons/Level_*/**/*.json
raz_output_jsons/derived/Level_*/**/*.json
raz_output_jsons/derived/Level_*/**/*.jsonl
ulga/graph/**/*.json
```

Note:

```text
RAZ_BookID.py and BookID_prompt.txt are not present in this English_Learning_DB workspace snapshot and were not modified.
```

Risk level:

```text
Low
```

---

## 2. Compile and Unit Test QA

Command executed:

```text
python -m py_compile ulga/query/raz_reusable_content_seed_query_layer.py ulga/validators/validate_raz_reusable_content_seed_query_layer.py tests/ulga/test_raz_reusable_content_seed_query_layer.py && python -m unittest tests.ulga.test_raz_reusable_content_seed_query_layer
```

Result:

```text
Ran 6 tests in 0.285s
OK
```

QA verdict:

```text
UNIT_TEST_PASS
```

---

## 3. Validator QA

Command executed:

```text
python ulga/validators/validate_raz_reusable_content_seed_query_layer.py
```

Result:

```text
Validating RAZ Reusable Content Seed Query Layer...
PASS: RAZ Reusable Content Seed Query Layer validator succeeded.
```

QA verdict:

```text
VALIDATOR_PASS
```

---

## 4. Report Consistency QA

Summary report:

```text
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
```

Validation report:

```text
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
```

Consistency checks:

```text
summary.status == PASS: true
validation.status == PASS: true
cards_loaded == summary.total_seed_cards: true
cards_loaded == validation.total_seed_cards_checked: true
record_counts_match_expected: true
all_levels_present: true
```

Loaded seed cards:

```text
14422
```

Record type counts:

```text
sentence: 7487
page_unit: 4925
reuse_unit: 2010
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

QA verdict:

```text
REPORT_CONSISTENCY_PASS
```

---

## 5. Theme and Warning Distribution Check

Top mapped themes from summary:

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

QA warning counts:

```text
unknown_theme: 2038
unknown_pattern: 549
unknown_grammar: 391
section_heading_detected: 34
```

Interpretation:

```text
Warnings remain expected residual metadata warnings from S5A/S5B.
They are not schema or query failures.
Default query guardrails exclude Unknown theme and section heading records.
```

QA verdict:

```text
WARNING_DISTRIBUTION_ACCEPTED_WITH_GUARDRAILS
```

---

## 6. Query Smoke QA

Smoke queries were run against current A-F derived enriched data.

| Query | Result count | Total matches before paging | First seed |
|---|---:|---:|---|
| find_short_reading_seeds | 10 | 3606 | RAZ_F_89_REUSE_000007 |
| find_exercise_seeds / reading_comprehension | 10 | 12316 | RAZ_F_89_REUSE_000007 |
| find_theme_seeds / Science page-reuse | 10 | 213 | RAZ_F_1098_REUSE_000010 |
| find_picture_prompt_seeds | 10 | 2873 | RAZ_B_2342_P009 |
| find_dialogue_rewrite_seeds | 10 | 597 | RAZ_F_92_REUSE_000008 |

For each smoke query, the following checks passed:

```text
no_error: true
has_results: true
authority_status == candidate_only: true
final_eligible == false: true
generated_content_returned == false: true
authority_promotion_allowed == false: true
Unknown theme excluded by default: true
heading / human_review excluded by default: true
```

QA verdict:

```text
QUERY_SMOKE_PASS
```

---

## 7. Guardrail QA

Rejected request checks:

| Request | Expected code | Actual result |
|---|---|---|
| static_only=false | STATIC_ONLY_REQUIRED | PASS |
| learner_id filter | ADAPTIVE_FIELD_REJECTED | PASS |
| generate_exercise filter | ADAPTIVE_FIELD_REJECTED | PASS |
| invalid record_type | INVALID_RECORD_TYPE_FILTER | PASS |
| unknown query_type | UNKNOWN_QUERY_TYPE | PASS |

Unknown theme behavior:

```text
Default query excludes Unknown theme.
Querying Unknown theme requires include_unknown_theme=true.
Because Unknown theme records also require human review, practical retrieval also requires include_human_review_required=true.
```

Explicit Unknown theme check:

```text
filters:
  mapped_themes: [Unknown]
  include_unknown_theme: true
  include_human_review_required: true

result_count: 5
total_matches_before_paging: 2038
first_seed: RAZ_F_2649_REUSE_000004
first_seed_theme: Unknown
first_seed_needs_human_review: true
first_seed_warnings: [unknown_theme]
```

QA verdict:

```text
GUARDRAIL_PASS
```

---

## 8. Explain Seed QA

Sample explained seed:

```text
seed_id: RAZ_F_1098_REUSE_000010
seed_type: reuse_unit
book_title: Does It Sink or Float?
theme: Science
sentence_count: 4
authority_status: candidate_only
seed_score: 3.42
```

QA verdict:

```text
EXPLAIN_SEED_PASS
```

---

## 9. Mutation Boundary QA

Confirmed from this QA run:

```text
raw RAZ JSON files were not intentionally modified.
derived Level_A-F enriched JSON / JSONL files were not intentionally modified.
query code was not modified during S6B.
validator code was not modified during S6B.
test code was not modified during S6B.
summary and validation reports were refreshed by validator/report flow.
S6B QA document was created.
```

Important boundary:

```text
S6B did not generate exercises.
S6B did not generate dialogues.
S6B did not generate readings.
S6B did not promote any candidate.
```

QA verdict:

```text
MUTATION_BOUNDARY_PASS
```

---

## 10. Known QA Notes

```text
1. The workspace is not a git repository, so git status / diff confirmation is unavailable.
2. Unknown theme records are intentionally hard to retrieve because they also require human review.
3. Grammar and vocabulary filtering remain rule-based until RAZ seed cards are linked to EGP/EVP authorities.
4. CEFR remains not authority-linked in S6A seed cards.
5. Listening seed is not final listening authority because enriched text outputs do not carry final audio authority.
```

---

## 11. Final QA Status

Overall status:

```text
RAZ-S6B_ReusableContentSeed_QueryLayer_QA_PASS
```

Reason:

```text
- Compile passed.
- Unit tests passed.
- Validator passed.
- Summary and validation reports are consistent.
- A-F coverage is complete.
- Real query smoke tests passed.
- Guardrail rejection checks passed.
- Unknown theme / heading / human-review exclusion behavior is conservative and correct.
- No generation or promotion path was enabled.
```

Blockers:

```text
None for static reusable seed query usage.
```

---

## 12. Recommended Next Task

Recommended next task:

```text
ULGA-S11C_ReadingDialogueContentAuthority_SchemaImplementation
```

Reason:

```text
S6A/S6B now provide a stable RAZ reusable seed query layer.
This can feed Reading / Dialogue Content Authority schema work without making RAZ records final authority.
```

Optional later task:

```text
RAZ-S6C_SeedQueryAuthorityLinkage_DesignScan
```

Purpose:

```text
Design how RAZ seed vocabulary / grammar tags can link to EVP / EGP / ULGA authority nodes.
```

---

## 13. Closeout Marker

```text
RAZ-S6B_ReusableContentSeed_QueryLayer_QA_PASS
```
