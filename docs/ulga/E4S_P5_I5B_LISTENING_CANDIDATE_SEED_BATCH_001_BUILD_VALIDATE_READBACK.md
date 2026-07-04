# E4S P5 I5B Listening Candidate Seed Batch 001 Build Validate Readback

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I5B_ListeningCandidateSeedBatch001_BuildValidateReadback
```

Decision:

```text
E4S-P5-I5B_ListeningCandidateSeedBatch001_BuildValidateReadback -> PASS_LOCAL_WITH_WARNINGS_UNCOMMITTED_GENERATED_ARTIFACTS
```

Reason:

```text
The operator built the candidate package from Seed Batch 001, ran validator, and ran both regression test suites. Validator returned PASS_WITH_WARNINGS as expected. Git status shows generated package/report files modified locally but not yet committed.
```

## Evidence

Build command:

```text
python tools/build_e4s_listening_candidate_package.py --seed-candidates ulga/listening/seeds/e4s_p5_seed_batch_001.json --output ulga/listening/candidates/e4s_listening_candidate_package.json
Wrote ulga/listening/candidates/e4s_listening_candidate_package.json
```

Validator summary:

```text
status = PASS_WITH_WARNINGS
issue_count = 2
blocking_issue_count = 0
warning_count = 2
candidate_count = 3
eligible_candidate_count = 3
internal_only_candidate_count = 3
learner_facing_candidate_count = 0
learner_state_attempt_count = 0
adaptive_attempt_count = 0
```

Warnings:

```text
P5_WARN_INTERNAL_ONLY_SOURCE -> STORY_DIALOGUE_CORPUS_REFERENCE
P5_WARN_INTERNAL_ONLY_SOURCE -> RAZ_READING_CORPUS_A_T_CANDIDATE
```

Regression tests:

```text
tests.test_build_e4s_listening_candidate_package -> 9 tests OK
tests.test_validate_e4s_listening_candidates -> 12 tests OK
```

Git status:

```text
modified: ulga/listening/candidates/e4s_listening_candidate_package.json
modified: ulga/listening/reports/e4s_listening_validator_report.json
no changes added to commit
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| Repo pull from origin/main | PASS |
| Package build from seed batch | PASS |
| Validator status | PASS_WITH_WARNINGS |
| Blocking issue count | 0 |
| Candidate count | 3 |
| Eligible candidate count | 3 |
| Builder regression test | PASS |
| Validator regression test | PASS |
| Generated package/report committed | NO |
| Working tree clean | NO |

Distance vector:

```text
E4S-P5-I5B_BUILD_VALIDATE -> PASS_WITH_WARNINGS
E4S-P5-I5B_GENERATED_ARTIFACTS -> LOCAL_MODIFIED_UNCOMMITTED
D_P5_I5B_FUNCTIONAL_VALIDATION = 0
D_P5_I5B_GITHUB_SYNC = 1 commit/push gate left
```

## Next Shortest Step

Commit the generated package and report locally:

```text
git add ulga/listening/candidates/e4s_listening_candidate_package.json ulga/listening/reports/e4s_listening_validator_report.json
git commit -m "data: refresh E4S P5 seed batch 001 candidate package"
git push origin main
git status
```

After push, the next readback should mark:

```text
E4S-P5-I5B_GENERATED_ARTIFACTS -> SYNCED_TO_GITHUB
E4S-P5-I5B_LOCAL_HYGIENE -> CLEAN
```
