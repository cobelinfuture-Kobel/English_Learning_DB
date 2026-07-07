# R7-M78A CI Readback and Closeout

## Task

```text
R7-M78A_Batch01RAZUsageEvidenceSelectionPlanArtifactBuilder
```

## Local validation

Operator local run:

```text
python ulga/builders/build_grammar_node_egp_batch01_raz_usage_evidence_candidates.py
Batch 01 RAZ usage evidence candidates build: PASS
Source files: 2252
RAZ usage candidates: 150

python ulga/builders/build_grammar_node_egp_batch01_raz_usage_evidence_candidates_filtered.py
Batch 01 filtered RAZ usage evidence build: PASS
Raw candidates: 150
Filtered candidates: 88
Removed candidates: 62

python ulga/builders/build_grammar_node_egp_batch01_raz_usage_evidence_selection_plan.py
Batch 01 RAZ usage evidence selection plan build: PASS
Source filtered candidates: 88
Selected candidates: 29

python ulga/validators/validate_grammar_node_egp_batch01_raz_usage_evidence_selection_plan.py
Batch 01 RAZ usage evidence selection plan validation: PASS

pytest tests/ulga/test_grammar_node_egp_batch01_raz_usage_evidence_selection_plan.py
6 passed
```

## Generated artifacts committed

```text
commit = 7608fcd
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_selection_plan.json
ulga/reports/grammar_node_egp_batch01_raz_usage_evidence_selection_plan_summary.json
```

## GitHub Actions evidence

Operator screenshot/readback confirmed:

```text
ReadingV1 P1 Tests #230 = PASS
English DB CI Readback #262 = PASS
commit = 7608fcd
branch = main
```

## Local sync

Operator local status after push:

```text
## main...origin/main
```

## Artifact summary

```text
validation_status = PASS
source_filtered_candidate_count = 88
selected_candidate_count = 29
unselected_candidate_count = 59
target_count = 5
targets_without_selected_candidates = 0
operator_review_required = true
authority_write_allowed = false
evidence_refs_write_allowed = false
coverage_increase_allowed = false
final_acceptance_allowed = false
```

## Closeout

```text
R7_M78A_STATUS = PASS_CI_SYNCED_AND_CLEAN
LAST_COMPLETED_STATUS = R7_M78A_PASS_CI_SYNCED_AND_CLEAN
NEXT_SHORT_STEP = R7-M79A_Batch01RAZUsageEvidenceSelectionPlanReadback
STOP_REASON = NONE
```
