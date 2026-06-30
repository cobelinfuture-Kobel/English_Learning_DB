# ULGA-S10K Static Candidate Query Layer QA

## 1. Scope

FULL STAGE QA only.

- no new query features
- no ranking mutation
- no adaptive behavior
- no upstream artifact mutation

## 2. S10J Carryover

- S10J passed with warnings
- derived fields remain derived
- theme / reading / dialogue view warnings remain
- plus-band mapping remains required
- B2 / C1 partial support remains
- C2 downstream view coverage remains missing
- broader pytest timeout remains to be classified

## 3. Files Inspected

- `docs/ulga/ULGA_S10I_STATIC_CANDIDATE_QUERY_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md`
- `ulga/query/__init__.py`
- `ulga/query/static_candidate_query_layer.py`
- `ulga/validators/validate_static_candidate_query_layer.py`
- `tests/ulga/test_static_candidate_query_layer.py`
- `ulga/reports/static_candidate_query_layer_summary.json`
- `ulga/reports/static_candidate_query_layer_validation.json`
- static ranking / views / reports / learner-related reference artifacts listed in S10K

## 4. Files Created

- `ulga/audits/audit_static_candidate_query_layer_qa.py`
- `ulga/reports/static_candidate_query_layer_qa_audit.json`
- `ulga/reports/static_candidate_query_layer_qa_mutation_snapshot.json`
- `tests/ulga/test_static_candidate_query_layer_qa.py`
- `docs/ulga/ULGA_S10K_STATIC_CANDIDATE_QUERY_LAYER_QA.md`

## 5. Files Modified

- none outside S10K-created QA files

## 6. QA Dimensions

- artifact presence and import health
- query function contract
- success and error schema
- static-only guardrails
- warning registry
- derived fields
- score policy
- explanation schema
- view-specific behavior
- multi-level coverage
- mutation integrity
- broader pytest timeout containment
- downstream consumer readiness

## 7. Query Function Contract QA

- all 9 public query functions exist
- all 9 execute against real artifacts
- all return structured responses
- no learner-specific input is required

Result: `PASS`

## 8. Response Schema QA

- canonical success response shape present
- candidate required fields present
- explanation schema present

Result: `PASS`

## 9. Error Schema QA

Verified:

- unknown view
- candidate not found
- `static_only=false`
- `learner_id`
- `student_id`
- `mastery`
- `adaptive`
- node_type / candidate_type conflict
- invalid limit
- invalid offset

Result: `PASS`

## 10. Static-only Guardrail QA

- forbidden adaptive / learner fields rejected
- raw ranking direct curriculum use remains warning-blocked
- learner exposure artifact not joined into candidate rows
- reinforcement expansion remains reference-only

Result: `PASS`

## 11. Warning Registry QA

- required warning code count: `20`
- missing required warning codes: `[]`
- expected warning surfaces verified in metadata / candidate warnings / explanation limitations

Result: `PASS`

## 12. Derived Field Consistency QA

- `node_type` deterministic from `candidate_type`
- `source_artifact` consistently derived
- `bridge_reason` matches view
- `supporting_authority_layer` remains list-shaped and includes candidate-family authority
- level field bundle consistently present

Result: `PASS_WITH_WARNINGS`

## 13. Score Policy QA

- `raw_static_score` and `view_score` both present in normal successful responses
- `view_score` marked policy-adjusted
- no reranking detected
- filtering preserves `view_rank`

Result: `PASS`

## 14. Candidate Explanation QA

- required explanation fields present
- explanation remains static-only
- no learner mastery / adaptive-next-node language found

Result: `PASS`

## 15. View-specific QA

- `balanced_global_view`: PASS
- `a1_safe_view`: PASS
- `theme_scoped_view`: PASS_WITH_WARNINGS
- `reading_bridge_view`: PASS_WITH_WARNINGS
- `dialogue_bridge_view`: PASS_WITH_WARNINGS
- `pattern_first_view`: PASS
- `vocabulary_first_view`: PASS
- `chunk_safe_view`: PASS
- `deduplicated_view`: PASS

Overall: `PASS_WITH_WARNINGS`

## 16. Multi-Level Coverage QA

- coverage matrix present
- plus bands correctly marked `requires_internal_band_mapping`
- `B2` and `C1` remain partial support
- `C2` remains `KNOWN_GAP_NOT_S10_BLOCKER`

Result: `PASS_WITH_WARNINGS`

## 17. Mutation Integrity QA

- protected upstream files hashed before and after QA execution
- mutation detected after bounded affected-area pytest and audit execution
- mutated protected files:
  - `ulga/graph/static_candidate_ranking.json`
  - `ulga/graph/static_candidate_ranking_views.json`
  - `ulga/reports/static_candidate_ranking_views_summary.json`
- root cause:
  existing ranking / views tests invoke builders and rewrite protected artifacts, which violates S10K mutation-integrity rules even though query-layer targeted tests themselves passed

Result: `FAIL`

## 18. Broader Pytest Timeout Analysis

- validator passed
- existing targeted query-layer tests passed
- S10K QA tests passed
- bounded affected-area pytest passed
- bounded affected-area pytest is not mutation-safe because legacy ranking/view tests rebuild artifacts
- prior full-suite timeout is best classified as `PREEXISTING_OR_SUITE_SIZE`

Result: `TIMEOUT_CONTAINED`

## 19. Downstream Consumer Readiness

- Reading Authority: `READY_WITH_WARNINGS`
- Dialogue Authority: `READY_WITH_WARNINGS`
- Worksheet / Exercise Builder: `READY_WITH_WARNINGS`
- Assessment Authority: `NOT_READY`
- Future Adaptive Planner: `FORBIDDEN_FOR_NOW`

## 20. Test Results

- `python -m pytest tests\ulga\test_static_candidate_query_layer.py -q`
- `python -m pytest tests\ulga\test_static_candidate_query_layer_qa.py -q`
- bounded affected-area pytest passed

## 21. Audit Result

- `python ulga\audits\audit_static_candidate_query_layer_qa.py`
- audit JSON written to `ulga/reports/static_candidate_query_layer_qa_audit.json`
- audit result: `FAIL`

## 22. Blocking Findings

- protected files mutated during QA
- current bounded affected-area smoke path is incompatible with S10K read-only mutation-integrity requirements

## 23. Warnings

- derived fields remain derived
- theme / reading / dialogue warnings remain
- plus-band internal mapping still required
- B2 / C1 downstream support remains partial
- C2 downstream support remains missing
- full-suite timeout remains contained, not eliminated

## 24. Decision

`S10K_RESULT = BLOCKED`

## 25. Recommended Next Task

`ULGA-S10K1_StaticCandidateQueryLayer_QAFix`
