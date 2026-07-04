# E4S P5 I2 Listening Candidate Package Builder Implementation Readback

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
E4S-P5-I2_ListeningCandidatePackageBuilderImplementation
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P5_I1_LISTENING_VALIDATOR_TEST_EVIDENCE_READBACK.md
2. tools/validate_e4s_listening_candidates.py
3. tests/test_validate_e4s_listening_candidates.py
4. docs/ulga/E4S_P5_LISTENING_CANDIDATE_PACKAGE_SCHEMA.md
5. docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
6. docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
7. ulga/graph/e4s_source_manifest.json
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Implementation Files:

```text
tools/build_e4s_listening_candidate_package.py
tests/test_build_e4s_listening_candidate_package.py
```

This implementation adds a metadata-only listening candidate package builder and tests. It does not commit a production `ulga/listening/candidates/e4s_listening_candidate_package.json` file in this handoff, does not generate audio, does not generate TTS, does not generate timing metadata, does not generate listening questions, does not create playback UI, does not create learner-facing output, and does not update learner state.

---

## 2. Core Execution

### 2.1 Implementation Decision

Decision:

```text
E4S-P5-I2_ListeningCandidatePackageBuilderImplementation -> IMPLEMENTED_REPOSITORY_WRITE
```

Implementation state:

```text
E4S-P5_CANDIDATE_PACKAGE_BUILDER -> IMPLEMENTED_PENDING_TEST_READBACK
E4S-P5_CANDIDATE_PACKAGE_DATA -> NOT_COMMITTED_BY_THIS_HANDOFF
E4S-P5_AUDIO_TTS_TIMING -> NOT_CREATED
E4S-P5_LEARNER_FACING_OUTPUT -> NOT_CREATED
```

Execution note:

```text
Files were written through GitHub API. This handoff did not execute local tests, GitHub Actions, Python scripts, package builders, validators, audio pipelines, TTS providers, or UI builds.
```

---

### 2.2 Builder Implementation Summary

Created:

```text
tools/build_e4s_listening_candidate_package.py
```

The builder implements:

```text
source manifest JSON loading
optional seed candidate JSON loading
empty metadata package generation
metadata-only candidate record generation
source_id cross-reference against source manifest
approved P5 source family / authority role checks
sentence candidate variant generation
dialogue candidate variant generation
passage candidate variant generation
deterministic candidate_id generation
deterministic candidate sorting
package-level policy object generation
source_manifest_ref generation
validator_contract_ref generation
audio_policy_ref generation
public_distribution_policy generation
learner_state_policy generation
validator_handoff generation
candidate_counts derivation
CLI arguments for source manifest, seed candidates, output path, package id, and dry-run
```

CLI surface:

```text
python tools/build_e4s_listening_candidate_package.py \
  --source-manifest <path> \
  --seed-candidates <path> \
  --output <path> \
  --package-id <id> \
  [--dry-run]
```

Default logical paths:

```text
source_manifest_path = ulga/graph/e4s_source_manifest.json
output_path = ulga/listening/candidates/e4s_listening_candidate_package.json
```

The default output path is a CLI default only. This implementation handoff does not commit a production package JSON file.

---

### 2.3 Test Implementation Summary

Created:

```text
tests/test_build_e4s_listening_candidate_package.py
```

The tests cover:

```text
empty package generation and validator PASS
sentence seed package generation and validator PASS
deterministic candidate sorting
dialogue seed generation with internal-only warning from validator
passage seed generation with ordered passage variant
non-P5 source family rejection
missing dialogue turns rejection
derived candidate_counts
CLI-style temporary output package validation
```

Test fixture policy:

```text
Tests use in-memory / temporary fixture packages only.
No production package JSON is created under ulga/listening/candidates/.
No audio, TTS, timing, question, UI, or learner-state fixture is created.
```

---

### 2.4 Builder Safety Contract

Builder explicitly keeps these outputs blocked:

```text
audio_generation_status = forbidden
tts_generation_status = forbidden
timing_generation_status = forbidden_in_package_policy / not_created_in_candidate_policy
question_generation_status = forbidden_in_schema_design
student_facing_status = forbidden_until_later_approval
learner_state_update_status = forbidden
adaptive_assignment_status = forbidden
source_promotion_status = forbidden
content_promotion_status = forbidden
public_distribution_status = blocked
```

Supported P5 source families in this implementation:

```text
parent_functional_sentence_corpus -> sentence_listening_candidate
story_dialogue_corpus -> dialogue_listening_candidate
raz_reading_corpus -> passage_listening_candidate
```

Rejected by default:

```text
governance
roadmap
status_artifact
raz_wordlist
grammar_profile
vocabulary_profile
frequency_profile
chunk_authority
cambridge_vocabulary
writing_template_corpus
assessment_pattern_corpus
generated_content_candidate
unknown or unapproved source families
```

---

### 2.5 Production Package Data Decision

Production package data state:

```text
ulga/listening/candidates/e4s_listening_candidate_package.json -> NOT_COMMITTED_BY_THIS_HANDOFF
```

Reason:

```text
The builder and tests should be pulled and run locally or through CI first. After tests pass, an operator-approved package build/readback can create or refresh the production metadata package and run the I1 validator against it.
```

---

## 3. Gate & Distance Update

### 3.1 Acceptance Gates for P5-I2

| Gate | Result | Evidence |
|---|---:|---|
| Operator implementation approval recorded | PASS | Current request |
| P5-I1 validator local test PASS existed before I2 | PASS | P5-I1 TestEvidenceReadback |
| Builder Python file created | PASS | `tools/build_e4s_listening_candidate_package.py` |
| Builder tests created | PASS | `tests/test_build_e4s_listening_candidate_package.py` |
| Source manifest input supported | PASS | Builder implementation |
| Seed candidate input supported | PASS | Builder implementation |
| Empty metadata package supported | PASS | Builder implementation/test |
| Sentence/dialogue/passage variants supported | PASS | Builder implementation/test |
| Deterministic candidate ordering implemented | PASS | Builder implementation/test |
| Candidate counts derived | PASS | Builder implementation/test |
| Validator handoff fields generated | PASS | Builder implementation |
| Audio/TTS/timing generation avoided | PASS | No audio/TTS/timing output |
| Listening question generation avoided | PASS | No questions/answers/distractors |
| Learner-facing output avoided | PASS | No `site/listening` output |
| Learner state avoided | PASS | No learner-state files |
| Source/content promotion avoided | PASS | No promotion artifacts |
| Production candidate package committed | NOT_DONE | Needs local/CI builder+validator evidence |
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
E4S-P5-I2_ListeningCandidatePackageBuilderImplementation
```

Sub-task Status:

```text
E4S-P5-I2_ListeningCandidatePackageBuilderImplementation -> IMPLEMENTED_PENDING_TEST_READBACK
```

Validator implementation state:

```text
E4S-P5_VALIDATOR_IMPLEMENTATION -> TESTED_LOCAL_PASS
```

Candidate package builder state:

```text
E4S-P5_CANDIDATE_PACKAGE_BUILDER -> IMPLEMENTED_PENDING_TEST_READBACK
```

Candidate package data state:

```text
E4S-P5_CANDIDATE_PACKAGE_DATA -> NOT_COMMITTED_BY_THIS_HANDOFF
```

Implementation distance:

```text
D_P5_BUILDER_TEST_READBACK = 1 test/readback gate left
```

Known blocked work:

```text
production candidate JSON package generation / commit
validator report for production candidate package
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
issue_id: E4S-P5-I2-DEFER-001
severity: high
affected_file_or_artifact: local test / CI result
classification: REQUIRED_EVIDENCE
why_deferred: This GitHub API handoff writes files but does not execute local or CI tests.
recommended_future_task: E4S-P5-I2_ListeningCandidatePackageBuilder_TestReadback
blocks_current_task: no
blocks_next_implementation_task: yes
```

```text
issue_id: E4S-P5-I2-DEFER-002
severity: high
affected_file_or_artifact: ulga/listening/candidates/e4s_listening_candidate_package.json
classification: FUTURE_WORK
why_deferred: Production metadata package should be created only after builder tests pass and operator approves a package build/readback.
recommended_future_task: E4S-P5-I3_ListeningCandidatePackageBuildAndValidate after I2 test pass
blocks_current_task: no
blocks_next_implementation_task: yes_until_test_pass
```

```text
issue_id: E4S-P5-I2-DEFER-003
severity: high
affected_file_or_artifact: audio / TTS / timing assets
classification: FUTURE_WORK
why_deferred: Audio/TTS/timing generation remains forbidden until candidate data exists, passes validator, and later audio gates are approved.
recommended_future_task: future operator-approved P5 audio implementation after validation gates
blocks_current_task: no
blocks_next_implementation_task: no
```

---

## 5. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P5-I2_ListeningCandidatePackageBuilder_TestReadback
```

Required local commands:

```text
git pull origin main
python -m unittest tests.test_build_e4s_listening_candidate_package
python -m unittest tests.test_validate_e4s_listening_candidates
```

Optional dry-run smoke command after tests:

```text
python tools/build_e4s_listening_candidate_package.py --dry-run
```

Stop condition:

```text
Stop here. Do not commit production listening candidate JSON packages and do not generate audio, TTS, timing, playback, listening questions, or listening UI from this implementation handoff.
```
