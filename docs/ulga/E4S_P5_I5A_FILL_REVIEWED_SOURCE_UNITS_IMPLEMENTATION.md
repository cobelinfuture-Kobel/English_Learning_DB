# E4S P5 I5A Fill Reviewed Source Units Implementation

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I5A_ListeningCandidateSeedBatch001_FillReviewedSourceUnits
```

Decision:

```text
E4S-P5-I5A_ListeningCandidateSeedBatch001_FillReviewedSourceUnits -> COMPLETED_SEED_INPUT_FILLED_PACKAGE_REBUILD_PENDING
```

Updated artifact:

```text
ulga/listening/seeds/e4s_p5_seed_batch_001.json
```

Commit:

```text
6f4b3ef5c3fe32c1562ecbebece6f3de1dc7c115
```

## Seed Fill Summary

```text
batch_status = REVIEWED_SOURCE_UNITS_FILLED
seed_001_sentence = FILLED_REVIEWED_SOURCE_UNIT
seed_002_dialogue = FILLED_REVIEWED_SOURCE_UNIT
seed_003_passage = FILLED_REVIEWED_SOURCE_UNIT
candidate_seed_count = 3
```

Filled reviewed source units:

```text
sentence source_unit_id = p5_sentence_002
dialogue source_unit_id = p5_dialogue_002
passage source_unit_id = p5_passage_002
```

## Scope Boundary

I5A filled the seed batch input file only. It did not manually rewrite the built package or validator report.

Reason:

```text
The built candidate package is generated output from tools/build_e4s_listening_candidate_package.py. To avoid hand-crafted generated JSON, package/report refresh should be produced by the local builder and validator commands in the next evidence step.
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| Reviewed sentence source unit supplied | PASS |
| Reviewed dialogue source unit supplied | PASS |
| Reviewed passage source unit supplied | PASS |
| Seed batch file updated | PASS |
| Candidate seed count | 3 |
| Candidate package rebuilt in this handoff | NO |
| Validator report refreshed in this handoff | NO |

Distance vector:

```text
E4S-P5-I5A_REVIEWED_SOURCE_UNITS -> FILLED
E4S-P5-I5A_SEED_BATCH_JSON -> UPDATED
D_P5_I5A_REVIEWED_SOURCE_UNIT_INPUT = 0 required input gates left
D_P5_I5B_PACKAGE_REBUILD_AND_VALIDATE = 1 required evidence gate left
```

## Next Shortest Step

```text
E4S-P5-I5B_ListeningCandidateSeedBatch001_BuildValidateReadback
```

Required local commands:

```text
git pull origin main
python tools/build_e4s_listening_candidate_package.py --seed-candidates ulga/listening/seeds/e4s_p5_seed_batch_001.json --output ulga/listening/candidates/e4s_listening_candidate_package.json
python tools/validate_e4s_listening_candidates.py --candidate-package ulga/listening/candidates/e4s_listening_candidate_package.json --source-manifest ulga/graph/e4s_source_manifest.json --report-output ulga/listening/reports/e4s_listening_validator_report.json
python -m unittest tests.test_build_e4s_listening_candidate_package
python -m unittest tests.test_validate_e4s_listening_candidates
git status
```

Expected validator status:

```text
PASS_WITH_WARNINGS
```

Reason:

```text
The dialogue and passage sources are internal/restricted source candidates, so public distribution should remain blocked and validator warnings are expected.
```
