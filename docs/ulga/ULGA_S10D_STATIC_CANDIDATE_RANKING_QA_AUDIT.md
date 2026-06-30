# ULGA S10D Static Candidate Ranking QA Audit

## 1. Task Summary

S10D performs a read-only quality audit of the S10C static/offline candidate ranking baseline. It measures top-N dominance, level distribution, A1 suitability, theme-specific coverage, inferred-score risk, blocked-candidate reasons, explain quality, score saturation, and duplicate-risk signals without changing any ranking output.

## 2. Files Created

- `ulga/audits/audit_static_candidate_ranking_quality.py`
- `ulga/reports/static_candidate_ranking_quality_audit.json`
- `tests/ulga/test_static_candidate_ranking_quality_audit.py`
- `docs/ulga/ULGA_S10D_STATIC_CANDIDATE_RANKING_QA_AUDIT.md`

## 3. Files Modified

- No S10C-owned artifacts were modified.
- S10D is read-only against the S10C ranking graph and summary inputs.
- S10D-owned report files may be generated or regenerated without affecting the S10C ranking graph, existing Authority graph, or requiring a ULGA pipeline rebuild.

## 4. Inputs Used

- `ulga/graph/static_candidate_ranking.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `ulga/validators/validate_static_candidate_ranking.py`
- `themes/theme_vocab_mapping.json`
- `ulga/graph/chunk_grammar_metadata.json`

## 5. Inputs Explicitly Forbidden

- `learner_state*`
- `mastery*`
- `retention*`
- `review_queue*`
- `assessment*`
- `attempt*`
- `personalized_exposure*`
- `planner*`
- `today_plan*`

## 6. Audit Scope

The audit checks:

1. Overall candidate distribution
2. Top-10 / 20 / 50 / 100 / 500 candidate-type dominance
3. Top-N level distribution
4. A1-only ranking quality
5. Theme-specific ranking quality
6. Chunk-dominance risk
7. Pattern suppression risk
8. Vocabulary suppression risk
9. Inferred-score risk
10. Blocked-candidate reason distribution
11. Adaptive leakage re-check
12. Explain quality
13. Score-component saturation
14. Duplicate-label / tie-density risk
15. Recommended next action

## 7. Status Rules

- `PASS`: no adaptive leakage, active candidates exist, and no quality warnings were raised.
- `PASS_WITH_WARNINGS`: no adaptive leakage, active candidates exist, and quality risks or critical QA findings were observed while the baseline remains usable for downstream design.
- `FAIL`: adaptive leakage detected, malformed upstream ranking blocks the audit, or no active candidates exist.

## 8. Audit Result

Current result: `PASS_WITH_WARNINGS`

Observed baseline characteristics:

- S10C output remains usable as a static baseline.
- Top-ranked windows are heavily chunk-dominant.
- Pattern and vocabulary coverage are suppressed in several top-N and theme-scoped views.
- Inferred and fallback signals are present and should be separated more clearly in future downstream contracts.

## 9. Test Results

The S10D test suite verifies:

- report generation
- schema contract
- read-only audit mode
- adaptive leakage remains false
- required QA sections exist
- recommendations are emitted
- status is valid

## 10. Known Limitations

- This is not adaptive ranking.
- This does not personalize for James or Cyndi.
- This does not use learner_state.
- This does not implement Antigravity Planner.
- This does not generate Reading, Dialogue, Exercise, or Assessment content.
- Theme filtering is keyword-based and intentionally lightweight.
- A1 suitability checks use rule-based heuristics, not expert manual item review.

## 11. Next Recommended Task

`ULGA-S10E_StaticCandidateRanking_BalancingContract_DesignScan`
