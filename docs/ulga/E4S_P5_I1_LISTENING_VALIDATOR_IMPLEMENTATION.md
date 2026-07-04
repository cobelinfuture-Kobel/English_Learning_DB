# E4S P5 I1 Listening Validator Implementation Readback

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Chinese Name:

```text
英語四技能來源可追蹤練習系統
```

Current Phase:

```text
E4S-P5_ListeningPracticeSystem
```

Current Sub-task:

```text
E4S-P5-I1_ListeningValidatorImplementation
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P5_LISTENING_DESIGN_SCHEMA_READINESS_QA.md
2. docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
3. docs/ulga/E4S_P5_LISTENING_CANDIDATE_PACKAGE_SCHEMA.md
4. docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
5. ulga/graph/e4s_source_manifest.json
6. tools/validate_e4s_source_manifest.py
7. tests/test_validate_e4s_source_manifest.py
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Implementation Files:

```text
tools/validate_e4s_listening_candidates.py
tests/test_validate_e4s_listening_candidates.py
```

This implementation adds the P5 listening candidate validator and tests only. It does not create `ulga/listening/candidates/e4s_listening_candidate_package.json`, does not generate audio, does not generate TTS, does not generate timing metadata, does not generate listening questions, does not create playback UI, does not create learner-facing output, and does not update learner state.

---

## 2. Core Execution

### 2.1 Implementation Decision

Decision:

```text
E4S-P5-I1_ListeningValidatorImplementation -> IMPLEMENTED_REPOSITORY_WRITE
```

Implementation state:

```text
E4S-P5_VALIDATOR_IMPLEMENTATION -> IMPLEMENTED
E4S-P5_CANDIDATE_PACKAGE_DATA -> NOT_CREATED
E4S-P5_AUDIO_TTS_TIMING -> NOT_CREATED
E4S-P5_LEARNER_FACING_OUTPUT -> NOT_CREATED
```

Execution note:

```text
Files were written through GitHub API. This handoff did not execute local tests, GitHub Actions, Python scripts, validators, package builders, audio pipelines, TTS providers, or UI builds.
```

---

### 2.2 Validator Implementation Summary

Created:

```text
tools/validate_e4s_listening_candidates.py
```

The validator implements:

```text
candidate package JSON loading
source manifest JSON loading
source_id cross-reference checks
source_family / authority_role checks
source trace completeness checks
candidate package schema checks
candidate record schema checks
sentence / dialogue / passage variant checks
license / public distribution checks
TTS / audio / voice / storage / timing policy checks
learner-facing output blocking
learner-state update blocking
adaptive assignment blocking
content/source promotion blocking
deterministic candidate ordering checks
duplicate candidate_id checks
deterministic validation report generation
CLI arguments for candidate package, source manifest, report output, and strict mode
```

CLI surface:

```text
python tools/validate_e4s_listening_candidates.py \
  --candidate-package <path> \
  --source-manifest <path> \
  --report-output <path> \
  [--strict-mode]
```

Default logical paths:

```text
candidate_package_path = ulga/listening/candidates/e4s_listening_candidate_package.json
source_manifest_path = ulga/graph/e4s_source_manifest.json
report_output_path = ulga/listening/reports/e4s_listening_validator_report.json
```

The default package/report folders are not created by this readback. They are only defaults used by the future CLI execution path.

---

### 2.3 Test Implementation Summary

Created:

```text
tests/test_validate_e4s_listening_candidates.py
```

The tests cover:

```text
valid fixture package passes
duplicate candidate_id failure
non-deterministic candidate order failure
status artifact used as content failure
RAZ word list used as audio source failure
generated unreviewed content failure
restricted source marked public failure
public audio without license clearance failure
missing TTS permission failure
learner-state update attempt failure
content promotion attempt failure
passage sentence-order / segmentation failure
validation report output shape
```

Test fixture policy:

```text
Tests create in-memory / temporary fixture candidate packages only.
No production candidate package JSON is created under ulga/listening/candidates/.
No audio, TTS, timing, question, UI, or learner-state fixture is created.
```

---

### 2.4 Implemented Blocking Contract Coverage

Implemented blocking codes include:

```text
P5_MISSING_SOURCE_TRACE
P5_UNKNOWN_SOURCE_ID
P5_UNKNOWN_SOURCE_FAMILY
P5_UNAPPROVED_AUTHORITY_ROLE
P5_STATUS_ARTIFACT_USED_AS_CONTENT
P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT
P5_GENERATED_UNREVIEWED_CONTENT
P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE
P5_REFERENCE_ONLY_USED_AS_CONTENT
P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN
P5_RESTRICTED_SOURCE_MARKED_PUBLIC
P5_MISSING_REVIEW_STATUS
P5_MISSING_TEXT_UNIT_ID
P5_MISSING_SOURCE_TEXT_NORMALIZED
P5_BAD_SEGMENTATION_POLICY
P5_DIALOGUE_MISSING_TURN_MODEL
P5_PASSAGE_MISSING_SENTENCE_ORDER
P5_SENTENCE_MISSING_CONTEXT_REF
P5_MISSING_AUDIO_POLICY_VERSION
P5_MISSING_TTS_PERMISSION
P5_TTS_ENABLED_WITHOUT_POLICY
P5_MISSING_VOICE_POLICY
P5_MISSING_STORAGE_POLICY
P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE
P5_TIMING_PRESENT_WITHOUT_POLICY
P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL
P5_LEARNER_STATE_UPDATE_ATTEMPT
P5_ADAPTIVE_ASSIGNMENT_ATTEMPT
P5_CONTENT_PROMOTION_ATTEMPT
P5_NON_DETERMINISTIC_ORDER
P5_DUPLICATE_CANDIDATE_ID
P5_BAD_PACKAGE_PHASE
P5_BAD_SCHEMA_VERSION
```

Implemented warning codes include:

```text
P5_WARN_INTERNAL_ONLY_SOURCE
P5_WARN_TIMING_OPTIONAL_MISSING
P5_WARN_LEVEL_BAND_UNVERIFIED
```

The remaining S2 warning codes are intentionally still contract-reserved for later richer package data:

```text
P5_WARN_SITUATION_METADATA_COARSE
P5_WARN_AUDIO_POLICY_PLACEHOLDER
P5_WARN_P4_HANDOFF_PENDING
P5_WARN_P1_HANDOFF_PENDING
P5_WARN_CHILD_SUITABILITY_REVIEW_PENDING
P5_WARN_PUBLIC_ATTRIBUTION_PENDING
P5_WARN_PRONUNCIATION_POLICY_PENDING
```

---

### 2.5 Validation Report Contract

The validator report includes:

```text
schema_version
validator_contract_version
epic_id
phase_id
task_id
status
issue_count
blocking_issue_count
warning_count
source_record_count
candidate_count
eligible_candidate_count
blocked_candidate_count
public_distribution_candidate_count
internal_only_candidate_count
learner_facing_candidate_count
learner_state_attempt_count
adaptive_attempt_count
issues
warnings
gate_metrics
next_shortest_step
```

Report status values implemented:

```text
PASS
PASS_WITH_WARNINGS
FAIL_BLOCKING_ERRORS
```

Schema-level failures and forbidden-transition failures are represented through `FAIL_BLOCKING_ERRORS` with specific issue codes in this first implementation.

---

## 3. Gate & Distance Update

### 3.1 Acceptance Gates for P5-I1

| Gate | Result | Evidence |
|---|---:|---|
| Operator implementation approval recorded | PASS | Current request |
| P5 design/schema readiness existed before implementation | PASS | P5 readiness QA |
| Validator Python file created | PASS | `tools/validate_e4s_listening_candidates.py` |
| Validator tests created | PASS | `tests/test_validate_e4s_listening_candidates.py` |
| Source manifest cross-reference logic added | PASS | Validator implementation |
| Candidate package schema checks added | PASS | Validator implementation |
| Blocking error codes implemented | PASS | Validator implementation |
| Report schema implemented | PASS | Validator implementation |
| Deterministic ordering checks implemented | PASS | Validator implementation |
| Forbidden transition checks implemented | PASS | Validator implementation |
| Fixture-only tests added | PASS | Test implementation |
| Production candidate JSON package avoided | PASS | No `ulga/listening/candidates/e4s_listening_candidate_package.json` created |
| Audio/TTS/timing generation avoided | PASS | No audio/TTS/timing output |
| Listening question generation avoided | PASS | No questions/answers/distractors |
| Learner-facing output avoided | PASS | No `site/listening` output |
| Learner state avoided | PASS | No learner-state files |
| Source/content promotion avoided | PASS | No promotion artifacts |
| Local tests run in this handoff | NOT_RUN | GitHub API write only |
| CI run in this handoff | NOT_RUN | No workflow readback executed |

---

### 3.2 Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P5_ListeningPracticeSystem
```

Current Sub-task:

```text
E4S-P5-I1_ListeningValidatorImplementation
```

Sub-task Status:

```text
E4S-P5-I1_ListeningValidatorImplementation -> IMPLEMENTED_PENDING_TEST_READBACK
```

Validator implementation state:

```text
E4S-P5_VALIDATOR_IMPLEMENTATION -> IMPLEMENTED
```

Candidate package builder state:

```text
E4S-P5_CANDIDATE_PACKAGE_BUILDER -> NOT_STARTED
```

Candidate package data state:

```text
E4S-P5_CANDIDATE_PACKAGE_DATA -> NOT_CREATED
```

Implementation distance:

```text
D_P5_VALIDATOR_TEST_READBACK = 1 test/readback gate left
```

Known blocked work:

```text
production candidate JSON package generation
audio generation
TTS generation
timing generation
listening question generation
playback UI
student-facing listening HTML
learner response capture
learner-state update
adaptive scheduling
public distribution
```

---

## 4. Deferred Issues Register

```text
issue_id: E4S-P5-I1-DEFER-001
severity: high
affected_file_or_artifact: local test / CI result
classification: FUTURE_WORK
why_deferred: This GitHub API handoff writes files but does not execute local or CI tests.
recommended_future_task: E4S-P5-I1_ListeningValidator_TestReadback
blocks_current_task: no
```

```text
issue_id: E4S-P5-I1-DEFER-002
severity: high
affected_file_or_artifact: ulga/listening/candidates/e4s_listening_candidate_package.json
classification: FUTURE_WORK
why_deferred: Validator implementation must land before production candidate package data is generated.
recommended_future_task: E4S-P5-I2_ListeningCandidatePackageBuilderImplementation after validator test readback
blocks_current_task: no
```

```text
issue_id: E4S-P5-I1-DEFER-003
severity: medium
affected_file_or_artifact: advanced warning-code coverage
classification: FUTURE_WORK
why_deferred: Some warning codes are reserved for richer future package data and handoff states.
recommended_future_task: future warning coverage patch after candidate builder data exists
blocks_current_task: no
```

```text
issue_id: E4S-P5-I1-DEFER-004
severity: high
affected_file_or_artifact: audio / TTS / timing assets
classification: FUTURE_WORK
why_deferred: Audio/TTS/timing generation remains forbidden until candidate data and validator reports pass future gates.
recommended_future_task: future operator-approved P5 audio implementation after validation gates
blocks_current_task: no
```

---

## 5. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P5-I1_ListeningValidator_TestReadback
```

Only next allowed action:

```text
Run or read back tests for tools/validate_e4s_listening_candidates.py and tests/test_validate_e4s_listening_candidates.py, then record whether the implementation is PASS, PASS_WITH_WARNINGS, or FAIL.
```

Suggested command for local operator execution:

```text
python -m unittest tests.test_validate_e4s_listening_candidates
```

Stop condition:

```text
Stop here. Do not create production listening candidate JSON packages and do not generate audio, TTS, timing, playback, listening questions, or listening UI from this implementation handoff.
```
