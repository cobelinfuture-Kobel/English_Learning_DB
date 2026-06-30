# ULGA S10G Static Candidate Ranking Views QA Audit

## 1. Task Summary

S10G performs a read-only QA audit of the S10F static candidate ranking views. It measures balance, traceability, score divergence, deduplication, theme relevance, opacity risk, and downstream readiness without changing S10F behavior.

## 2. Read-only Scope

S10G does not modify ranking behavior.

S10G does not rebuild S10F views.

S10G does not tune view_score.

S10G does not enable adaptive ranking.

S10G only audits whether S10F ranking views are safe and useful enough for downstream design.

## 3. Files Inspected

- `ulga/graph/static_candidate_ranking_views.json`
- `ulga/reports/static_candidate_ranking_views_summary.json`
- `ulga/graph/static_candidate_ranking.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `ulga/reports/static_candidate_ranking_quality_audit.json`
- `docs/ulga/ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_IMPLEMENTATION.md`
- `ulga/validators/validate_static_candidate_ranking_views.py`
- `ulga/validators/validate_static_candidate_ranking.py`
- `themes/theme_vocab_mapping.json`

## 4. Files Created

- `ulga/audits/audit_static_candidate_ranking_views_quality.py`
- `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- `tests/ulga/test_static_candidate_ranking_views_quality_audit.py`
- `docs/ulga/ULGA_S10G_STATIC_CANDIDATE_RANKING_VIEWS_QA_AUDIT.md`

## 5. Forbidden Files Not Touched

- `learner_state*`
- `mastery*`
- `retention*`
- `review_queue*`
- `assessment*`
- `attempt*`
- `personalized_exposure*`
- `planner*`
- `today_plan*`

## 6. S10F Baseline Recap

- S10F builder: `PASS`
- S10F validator: `PASS`
- S10F tests: `14 passed`
- S10F summary status: `PASS`
- adaptive leakage: `false`

## 7. Required View Presence

S10G verifies all required views exist:

- `raw_global_view`
- `balanced_global_view`
- `a1_safe_view`
- `theme_scoped_view`
- `reading_bridge_view`
- `dialogue_bridge_view`
- `pattern_first_view`
- `vocabulary_first_view`
- `chunk_safe_view`
- `deduplicated_view`

## 8. Raw Traceability Findings

S10G checks:

- `raw_rank`
- `raw_candidate_id`
- `raw_static_score`
- raw-id match back to S10C
- view-rank continuity

Traceability must remain intact for every view candidate.

## 9. Balanced Global View Findings

S10G audits whether `balanced_global_view` solved chunk dominance without erasing safe chunk exposure entirely. It checks top-20 and top-100 type balance, duplicate suppression, opacity ratio, and raw-vs-view score separation.

## 10. A1-Safe View Findings

S10G checks that `a1_safe_view` stays within `A1`, preserves pattern and vocabulary support, suppresses duplicates, and avoids advanced or opaque chunk forms. It also checks for over-correction that could make the view too lexical.

## 11. Reading Bridge View Findings

S10G checks whether `reading_bridge_view` contains enough pattern support for passage-building and not just lexical items. Vocabulary-heavy top windows are flagged for downstream caution.

## 12. Dialogue Bridge View Findings

S10G checks whether `dialogue_bridge_view` keeps useful conversational chunks without becoming too opaque or too under-supported by sentence patterns.

## 13. Theme-Scoped View Findings

S10G checks each required theme view for:

- candidate count
- top-20 type mix
- top-20 level mix
- theme relevance ratio
- duplicate suppression
- opaque chunk ratio

## 14. Deduplication Findings

S10G checks duplicate suppression in:

- `balanced_global_view`
- `a1_safe_view`
- `theme_scoped_view`
- `reading_bridge_view`
- `dialogue_bridge_view`
- `deduplicated_view`

It also checks whether canonical candidates preserve usable equivalent raw-id traceability.

## 15. Opaque Chunk Findings

S10G re-checks chunk opacity using existing suitability flags and label heuristics:

- `contains_sb_sth`
- `contains_slash_alternative`
- `contains_bracket_alternative`
- `movable_object_pattern`
- `idiomatic_or_low_transparency`
- `advanced_modal_or_perfect`

## 16. View Score Diagnostics

S10G compares `view_score` with `raw_static_score` to measure:

- mean absolute delta
- max absolute delta
- upward-bias ratio
- downward-bias ratio

This checks whether downstream scoring remains explainable and tied to raw evidence.

## 17. Adaptive Leakage Check

S10G recursively scans S10F views and the S10G audit report for forbidden adaptive leakage. Adaptive data must remain absent.

## 18. Downstream Readiness

S10G assigns only these statuses:

- `READY`
- `READY_WITH_WARNINGS`
- `NEEDS_TUNING`
- `NOT_READY`

These statuses are intended for downstream bridge-readiness design, not for view rebuilding.

## 19. Critical Findings

Critical findings are reserved for:

- missing required views
- broken raw traceability
- duplicate failures in protected top-20 windows
- adaptive leakage

## 20. Warnings

Warnings are expected to capture:

- balanced or A1 over-correction
- reading view lexical skew
- dialogue view chunk skew
- weak theme relevance
- high opacity load
- large view-score divergence

## 21. Final QA Status

Expected result is `PASS_WITH_WARNINGS`, assuming required views remain present and traceability stays intact.

## 22. Recommendation for Next Task

`ULGA-S10H_StaticRankingBridgeReadiness_DesignScan`
