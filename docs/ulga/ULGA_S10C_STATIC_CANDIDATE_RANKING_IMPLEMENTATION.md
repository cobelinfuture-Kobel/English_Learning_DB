# ULGA_S10C Static Candidate Ranking Implementation

## 1. Task Summary

Implemented a minimal static/offline candidate ranking layer for ULGA. This build ranks `vocabulary_candidate`, `chunk_candidate`, and `pattern_candidate` records using only static authority data. It does not read learner-specific state, does not call planner logic, and does not generate teaching content.

## 2. Files Created

- `ulga/builders/build_static_candidate_ranking.py`
- `ulga/validators/validate_static_candidate_ranking.py`
- `ulga/audits/audit_static_candidate_ranking.py`
- `ulga/graph/static_candidate_ranking.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `tests/fixtures/ulga/static_candidate_ranking_fixture.json`
- `tests/ulga/test_static_candidate_ranking.py`
- `docs/ulga/ULGA_S10C_STATIC_CANDIDATE_RANKING_IMPLEMENTATION.md`

## 3. Files Modified

- None outside the new S10C files above.

## 4. Inputs Used

- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/vocabulary_nodes.json`
- `vocabulary/json/vocabulary.json`
- `ulga/graph/chunk_nodes.json`
- `ulga/graph/chunk_grammar_metadata.json`
- `themes/theme_vocab_mapping.json`

## 5. Inputs Explicitly Forbidden

- `learner_state.json`
- `mastery*.json`
- `retention*.json`
- `review_queue*.json`
- `assessment*.json`
- `attempt*.json`
- `personalized_exposure*.json`
- `planner*.json`
- `today_plan*.json`
- `ulga/graph/exposure_mapping_bridge.json`
- `ulga/graph/reinforcement_candidate_expansion.json`

## 6. Static Ranking Formula

`static_score = dependency_readiness_score * 0.30 + frequency_score * 0.20 + theme_spiral_score * 0.20 + reinforcement_score * 0.20 + authority_confidence_score * 0.10`

All component scores are normalized to `0.0 <= score <= 1.0`. Final `static_score` is rounded to 4 decimals.

Implementation note:

- `reinforcement_score` in S10C is static reinforcement potential from existing authority connectivity only.
- It does not use learner exposure, learner history, mastery, retention, or assessment evidence.

## 7. Candidate Schema

Active candidates in `ulga/graph/static_candidate_ranking.json` follow:

```json
{
  "rank": 1,
  "candidate_id": "string",
  "candidate_type": "vocabulary_candidate",
  "label": "string",
  "level": "A1",
  "theme_refs": [],
  "static_score": 0.0,
  "score_breakdown": {
    "dependency_readiness_score": 0.0,
    "frequency_score": 0.0,
    "theme_spiral_score": 0.0,
    "reinforcement_score": 0.0,
    "authority_confidence_score": 0.0
  },
  "explain": [],
  "blocked": false,
  "block_reasons": []
}
```

Blocked candidates are emitted separately in `blocked_candidates` and excluded from `candidates`.

## 8. Validator Rules

The validator checks:

1. JSON parse succeeds
2. `schema_version` exists and matches S10C
3. `ranking_mode == static_offline`
4. `adaptive_enabled == false`
5. required top-level fields exist
6. `candidates` is a list
7. every candidate has required fields
8. all scores are between 0 and 1
9. `static_score` recomputes from `score_breakdown`
10. active candidates are sorted deterministically
11. forbidden adaptive keywords do not appear in output
12. active candidates have non-empty `explain`
13. `blocked=false` candidates have empty `block_reasons`
14. blocked candidates are excluded from active ranking

## 9. Audit Result

Current audit output in `ulga/reports/static_candidate_ranking_summary.json`:

- `status`: `PASS_WITH_WARNINGS`
- `candidate_count`: `20700`
- `active_candidate_count`: `11997`
- `blocked_candidate_count`: `8703`
- `adaptive_leakage_detected`: `false`
- `warnings`: `["inferred_scores_present"]`

## 10. Test Results

Executed:

```powershell
python ulga\builders\build_static_candidate_ranking.py
python ulga\validators\validate_static_candidate_ranking.py
python ulga\audits\audit_static_candidate_ranking.py
python -m pytest tests\ulga\test_static_candidate_ranking.py -q
python -m pytest tests\ulga\ -q
```

Results:

- Builder: PASS
- Validator: PASS
- Audit: PASS_WITH_WARNINGS
- `tests/ulga/test_static_candidate_ranking.py`: 11 passed
- `tests/ulga/`: 406 passed

## 11. Known Limitations

- This is not adaptive ranking.
- This does not personalize for James or Cyndi.
- This does not use learner_state.
- This does not implement Antigravity Planner.
- This does not generate Reading, Dialogue, Exercise, or Assessment content.
- Some static scores are inferred from authority shape where no direct normalized signal exists.
- Current top-ranked outputs skew toward high-support chunks because chunk authority carries strong static pattern-seed metadata.

## 12. Next Recommended Task

- `ULGA-S10D_StaticCandidateRanking_QA_Audit`
