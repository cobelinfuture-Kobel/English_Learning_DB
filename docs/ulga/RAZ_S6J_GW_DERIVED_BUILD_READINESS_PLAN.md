# RAZ-S6J_GW_DerivedBuildReadinessPlan

## 1. Task Name

- `RAZ-S6J_GW_DerivedBuildReadinessPlan`

## 2. Objective

- Define a safe derived build readiness plan for `RAZ` levels `G-W`.
- Keep this task planning-only.
- Do not run the full `G-W` derived build.
- Do not expose `G-W` in the reusable seed query layer yet.
- Do not change runtime, API, scheduler, dashboard, planner, or authority state.

## 3. Scope Guardrails

- Do not rebuild `G-W` derived artifacts in this task.
- Do not promote content.
- Do not implement CEFR scoring.
- Do not implement adaptive candidate selection.
- Do not hardcode `G-W` or `A-W` as a permanent universe.
- Do not weaken `S6F` drift validation.

## 4. Change Impact Before Modification

- Affected files:
  - `docs/ulga/RAZ_S6J_GW_DERIVED_BUILD_READINESS_PLAN.md`
  - `ulga/reports/raz_gw_derived_build_readiness_plan.json`
- Risk level: `Low`
- Real-trading impact: `None direct`; planning/reporting only.
- Restart required: `No`

## 5. Preflight

Read back:

- `docs/ulga/RAZ_S6I_GW_SOURCE_PLACEMENT_RECHECK_AFTER_OPERATOR_FIX.md`
- `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `tools/raz_normalized_tagging_pipeline.py`
- `tools/raz/build_raz_level_manifest.py`

Validation baseline:

- `validate_raz_level_discovery.py` -> `PASS`
- `validate_raz_reusable_content_seed_query_layer.py` -> `PASS`
- `validate_raz_downstream_discovery_drift.py` -> `PASS_WITH_WARNINGS`
- pytest pack -> `27 passed, 8 subtests passed`

## 6. Files Inspected

- `raz_output_jsons/Level_G` through `raz_output_jsons/Level_W`
- `raz_output_jsons/derived/Level_F/enriched/raz_F_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_F/enriched/raz_F_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_F/enriched/raz_F_reuse_unit_enriched.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_gw_source_placement_recheck_after_operator_fix.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 7. Files Created

- `docs/ulga/RAZ_S6J_GW_DERIVED_BUILD_READINESS_PLAN.md`
- `ulga/reports/raz_gw_derived_build_readiness_plan.json`

## 8. Files Modified

- None

## 9. Current A-F / G-W State

Current observed state:

- `S6D` currently detects `A-W`.
- The reusable seed query layer currently exposes only `A-F`.
- `G-W` raw timeline, sentence candidate, page unit, and reuse candidate evidence all exist.
- `G-W` normalized and enriched derived artifacts do not exist yet.
- `G-W` therefore are not queryable derived corpus yet.

Baseline contrast:

| Scope | Discovery | Normalized | Enriched | Seed Query Layer |
| --- | --- | --- | --- | --- |
| `A-F` | present | present | present | exposed |
| `G-W` | present | absent | absent | not exposed |

Interpretation:

- `READY_FOR_REUSE_UNIT_PIPELINE` in `S6D` means raw/discovery readiness.
- It does not mean `QUERY_LAYER_READY` for `G-W`.

## 10. A-F Derived Schema Baseline

Observed `A-F` enriched record families:

- Sentence enriched records contain:
  - `candidate_id`
  - `source_page_unit_id`
  - `text`
  - `source_tags`
  - `content_unit_tags`
  - `theme_tags`
  - `linguistic_tags`
  - `pedagogical_tags`
  - `reuse_tags`
  - `qa_tags`
- Page-unit enriched records contain:
  - `page_unit_id`
  - `book_id`
  - `level`
  - `title`
  - `page_number`
  - `sentence_candidate_ids`
  - `sentence_count`
  - `text`
  - `source_tags`
  - `authority_status`
  - `promotion_status`
  - `review_status`
  - `content_unit_tags`
  - `theme_tags`
  - `pedagogical_tags`
  - `reuse_tags`
  - `qa_tags`
- Reuse-unit enriched records contain:
  - `reuse_unit_id`
  - `source_page_unit_id`
  - `book_id`
  - `level`
  - `title`
  - `page_number`
  - `source_sentence_candidate_ids`
  - `clean_text`
  - `sentence_count`
  - `source_tags`
  - `authority_status`
  - `promotion_status`
  - `review_status`
  - `content_unit_tags`
  - `theme_tags`
  - `pedagogical_tags`
  - `reuse_tags`
  - `qa_tags`

Seed query layer expectations:

- It only reads enriched derived files.
- It converts enriched records into seed cards with required fields:
  - `seed_id`
  - `seed_type`
  - `source`
  - `text_preview`
  - `text`
  - `content_unit`
  - `theme`
  - `linguistic`
  - `pedagogy`
  - `qa`
  - `ranking`
- Guardrails remain:
  - `static_only = true`
  - `authority_promotion_allowed = false`
  - queryable levels are discovery-based, not hardcoded at runtime

## 11. G-W Raw Candidate Baseline

Current `G-W` raw artifacts match the families consumed by `tools/raz_normalized_tagging_pipeline.py`:

- `book_metadata`
- `sentence_candidates`
- `page_units`
- `reuse_unit_candidates`
- `clean_summary`

The raw sample for `Level_G` already includes:

- candidate identifiers
- page linkage
- book metadata
- raw sentence text
- page-unit text
- reuse-unit text
- authority fields
- audio fields and audio trace data

Compatibility assessment:

- Structural compatibility with the current pipeline: `PASS_WITH_WARNINGS`
- Reason:
  - required raw field families exist
  - but `G-W` still lack actual normalized/enriched outputs, so end-to-end count parity and warning behavior are not yet proven

## 12. Artifact Gap Matrix Summary

Representative gap summary:

| Level | Raw Sentence | Raw Page | Raw Reuse | Normalized Sentence | Normalized Page | Normalized Reuse | Enriched Sentence | Enriched Page | Enriched Reuse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `G` | 2336 | 930 | 801 | 0 | 0 | 0 | 0 | 0 | 0 |
| `H` | 2654 | 1015 | 879 | 0 | 0 | 0 | 0 | 0 | 0 |
| `I` | 3341 | 1087 | 1000 | 0 | 0 | 0 | 0 | 0 | 0 |
| `J` | 5218 | 1033 | 1024 | 0 | 0 | 0 | 0 | 0 | 0 |
| `K` | 6365 | 1030 | 1018 | 0 | 0 | 0 | 0 | 0 | 0 |
| `L-W` | present | present | present | 0 | 0 | 0 | 0 | 0 | 0 |

Gap conclusion:

- All `G-W` levels are `DERIVED_BUILD_READY`.
- No `G-W` level is yet `NORMALIZED_READY`.
- No `G-W` level is yet `ENRICHED_READY`.
- No `G-W` level is yet `QUERY_LAYER_READY`.

## 13. Readiness Terminology Policy

Recommended readiness meanings:

1. `RAW_TIMELINE_PRESENT`
   - Timeline JSON exists.
2. `RAW_CANDIDATE_READY`
   - Sentence candidate, page unit, and reuse candidate evidence exists.
3. `DERIVED_BUILD_READY`
   - Raw candidates are sufficient to run normalized and enriched builders.
4. `NORMALIZED_READY`
   - Normalized sentence/page/reuse artifacts exist and pass schema validation.
5. `ENRICHED_READY`
   - Enriched sentence/page/reuse artifacts exist and pass quality checks.
6. `QUERY_LAYER_READY`
   - Enriched artifacts are available and the seed query layer validation includes the level.
7. `ADAPTIVE_CANDIDATE_READY`
   - Canonical unit, tag enrichment, CEFR carrier, adaptive carrier, and quality flags are sufficient for adaptive candidate inclusion.

Important contract:

- Do not interpret `S6D READY_FOR_REUSE_UNIT_PIPELINE` as `QUERY_LAYER_READY` for `G-W`.

## 14. Canonical Unit Contract Summary

Proposed shared contract:

```json
{
  "unit_id": "",
  "source_system": "RAZ",
  "source_level": "",
  "source_book_id": "",
  "source_title": "",
  "source_filename": "",
  "unit_type": "sentence | page_unit | reuse_unit | passage_unit | dialogue_unit",
  "raw_text": "",
  "normalized_text": "",
  "text_span": {
    "page_index": null,
    "sentence_index": null,
    "start_time": null,
    "end_time": null
  },
  "grammar_tags": [],
  "vocabulary_tags": [],
  "chunk_tags": [],
  "theme_tags": [],
  "pattern_tags": [],
  "discourse_tags": [],
  "dialogue_tags": [],
  "complexity_features": {
    "token_count": null,
    "sentence_count": null,
    "clause_count": null,
    "avg_sentence_length": null,
    "has_dialogue": null,
    "has_quotation": null,
    "multi_sentence_page": null
  },
  "cefr_projection_carrier": {
    "candidate_bands": [],
    "primary_band": null,
    "confidence": null,
    "evidence": []
  },
  "adaptive_selection_carrier": {
    "eligible_for_review": false,
    "eligible_for_reinforcement": false,
    "eligible_for_new_learning": false,
    "target_skill_tags": [],
    "prerequisite_tags": [],
    "difficulty_signal": null
  },
  "quality_flags": [],
  "warning_flags": [],
  "human_review_required": false,
  "source_trace": {},
  "authority_status": "candidate_only",
  "promotion_allowed": false
}
```

Recommended migration approach:

- Treat this as an additive canonical envelope.
- Do not rewrite existing `A-F` enriched artifacts in this task.
- Map current `theme_tags / linguistic_tags / pedagogical_tags / reuse_tags / qa_tags` into this envelope in a later implementation task.

## 15. Tag Carrier Field Summary

Sentence unit should carry:

- `grammar_tags`
- `vocabulary_tags`
- `chunk_tags`
- `theme_tags`
- `pattern_tags`
- `discourse_tags`
- `dialogue_tags`
- `quality_flags`
- `warning_flags`

Page-unit and reuse-unit should carry:

- `theme_tags`
- `pattern_tags`
- `discourse_tags`
- `dialogue_tags`
- `quality_flags`
- `warning_flags`

Guideline:

- Keep current A-F compatibility by wrapping existing tags, not replacing them destructively.

## 16. CEFR / Adaptive Carrier Field Summary

CEFR carrier fields:

- `candidate_bands`
- `primary_band`
- `confidence`
- `evidence`

Adaptive carrier fields:

- `eligible_for_review`
- `eligible_for_reinforcement`
- `eligible_for_new_learning`
- `target_skill_tags`
- `prerequisite_tags`
- `difficulty_signal`

Boundary:

- These are carrier fields only.
- This task does not calculate CEFR projection.
- This task does not calculate adaptive ranking or learner-specific selection.

## 17. Build Sequence Recommendation

Recommended execution sequence for a later implementation task:

1. Choose an explicit pilot level set at run time.
2. Run `tools/raz_normalized_tagging_pipeline.py` with `--levels <pilot>` and optional `--limit-per-level`.
3. Write normalized outputs to:
   - `raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_sentence_normalized.jsonl`
   - `raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_page_unit_normalized.json`
   - `raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_reuse_unit_normalized.json`
4. Write enriched outputs to:
   - `raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_sentence_enriched.jsonl`
   - `raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_page_unit_enriched.json`
   - `raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_reuse_unit_enriched.json`
5. Review:
   - `raz_output_jsons/derived/reports/raz_tagging_summary.json`
   - `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
   - `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
6. Rebuild `S6D` discovery inventory.
7. Run validators and pytest pack.
8. Only in a separate later task, evaluate seed query layer expansion.

## 18. Pilot Batch Recommendation

Primary recommendation:

- Pilot batch: `G` only

Reason:

- It is the smallest blast radius.
- It verifies the post-placement-fix path with minimal rollback surface.
- It proves raw-to-derived count parity and warning behavior before adding a second upper-beginner level.

Recommended stage two if `G` passes:

- `H`

Explicit non-recommendation:

- Do not run `G-W` full batch as the first derived build step.

## 19. Validators Required After Pilot

- `python ulga/validators/validate_raz_level_discovery.py`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `python ulga/validators/validate_raz_downstream_discovery_drift.py`

## 20. QA Gates After Pilot

- Normalized counts must equal raw candidate counts for sentence/page/reuse units.
- Enriched outputs must contain no forbidden audio fields.
- All records must keep `authority_status = candidate_only`.
- No path may set `promotion_allowed = true`.
- Sentence/page/reuse linkage fields must remain traceable to raw IDs and raw file path.
- Warning and human-review flags must remain populated for low-confidence or ambiguous tagging cases.
- Seed query layer must remain `A-F` only until a separate explicit expansion task.
- `S6F` drift validator must remain `PASS` or `PASS_WITH_WARNINGS` with `must_fix_count = 0`.

## 21. Validator Results

- `python ulga/validators/validate_raz_level_discovery.py`
  - `PASS`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
  - `PASS`
- `python ulga/validators/validate_raz_downstream_discovery_drift.py`
  - `PASS_WITH_WARNINGS`
  - `must_fix_count = 0`

## 22. Test Results

- `python -m pytest tests/ulga/test_raz_downstream_discovery_drift.py tests/test_raz_normalized_tagging_pipeline.py tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`
- Result: `27 passed, 8 subtests passed in 17.27s`

## 23. Risk Assessment

- `Low-Medium`

Main risks:

- `G-W` are structurally compatible with the current pipeline, but no end-to-end derived build evidence exists yet.
- Upper levels likely produce more dialogue, quotation, long-clause, and mixed-theme cases than `A-F`.
- `S6D` readiness wording can be misread as query readiness if terminology is not tightened.
- Source PDF directories remain absent, so later source-side reconciliation may still require operator follow-up.

## 24. Authority Boundary Statement

- No content was generated.
- No content was promoted into Reading Authority.
- No content was promoted into Writing, Dialogue, Exercise, or Assessment Authority.
- `candidate_only` remains enforced.
- `promotion_allowed` remains blocked.
- `G-W` were not exposed in the seed query layer.

## 25. Readiness Plan Status

- `PASS_WITH_WARNINGS`

Reason:

- The plan clearly separates raw readiness from enriched query readiness.
- The artifact gap between `A-F` and `G-W` is defined.
- A canonical unit contract is proposed.
- CEFR and adaptive carrier fields are defined without implementation.
- Validators and tests remain stable.
- Warnings remain because `G-W` normalized/enriched artifacts do not exist yet and the drift validator still carries legacy warning-only findings.

## 26. Next Recommended Task

- Run a `G`-only derived build smoke pilot, compare raw-to-derived count parity and warning distribution, then decide whether `H` can enter the second pilot batch before any seed-query expansion planning.
