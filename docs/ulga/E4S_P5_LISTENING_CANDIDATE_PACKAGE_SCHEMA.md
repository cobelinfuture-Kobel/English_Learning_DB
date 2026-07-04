# E4S P5 Listening Candidate Package Schema Design Scan

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
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
2. docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
3. docs/ulga/E4S_P0_CLOSEOUT_SOURCE_AUTHORITY_FOUNDATION_READBACK_QA.md
4. docs/ulga/E4S_P5_LISTENING_PRACTICE_SYSTEM_START_GATE_PREFLIGHT.md
5. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
6. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
7. ulga/graph/e4s_source_manifest.json
8. ulga/reports/e4s_source_manifest_summary.json
9. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
10. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
11. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
12. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable for This Sub-task:

```text
docs/ulga/E4S_P5_LISTENING_CANDIDATE_PACKAGE_SCHEMA.md
```

This task defines the future listening candidate package schema only. It does not create `ulga/listening/candidates/e4s_listening_candidate_package.json`, does not implement the validator, does not run validation, does not generate audio, does not generate TTS, does not generate timing metadata, does not generate listening questions, does not create playback UI, does not create learner-facing output, and does not update learner state.

---

## 2. Core Execution

### 2.1 Phase 5 S3 Decision

Decision:

```text
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan -> COMPLETED
```

Candidate package schema state after this task:

```text
E4S-P5_CANDIDATE_PACKAGE_SCHEMA -> DEFINED
E4S-P5_CANDIDATE_PACKAGE_DATA -> NOT_CREATED
E4S-P5_VALIDATOR_IMPLEMENTATION -> NOT_STARTED
E4S-P5_IMPLEMENTATION -> STILL_REQUIRES_OPERATOR_APPROVAL
```

Rationale:

```text
P5-S1 defined source eligibility and audio policy. P5-S2 defined the validator contract. P5-S3 now defines the candidate package schema that future package builders and validators must use. This does not create package data or execute any implementation.
```

---

### 2.2 Intended Future Package Location

Future logical default path:

```text
ulga/listening/candidates/e4s_listening_candidate_package.json
```

This task does not create the path above.

Future report path expected by the validator contract:

```text
ulga/listening/reports/e4s_listening_validator_report.json
```

This task does not create the report path above.

---

### 2.3 Top-Level Package Schema

Future candidate package top-level shape:

```json
{
  "schema_version": "E4S_LISTENING_CANDIDATE_PACKAGE_V1",
  "epic_id": "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem",
  "phase_id": "E4S-P5_ListeningPracticeSystem",
  "task_id": "<creating_task_id>",
  "package_id": "<stable_package_id>",
  "package_policy": {},
  "source_manifest_ref": {},
  "validator_contract_ref": {},
  "audio_policy_ref": {},
  "public_distribution_policy": {},
  "learner_state_policy": {},
  "candidate_counts": {},
  "candidates": []
}
```

Required top-level fields:

```text
schema_version
epic_id
phase_id
task_id
package_id
package_policy
source_manifest_ref
validator_contract_ref
audio_policy_ref
public_distribution_policy
learner_state_policy
candidate_counts
candidates
```

Required top-level constants:

```text
schema_version = E4S_LISTENING_CANDIDATE_PACKAGE_V1
phase_id = E4S-P5_ListeningPracticeSystem
public_distribution_policy.default = blocked
learner_state_policy.learner_state_update = forbidden
learner_state_policy.adaptive_assignment = forbidden
```

---

### 2.4 Package Policy Object

Required `package_policy` fields:

```text
package_scope
candidate_only
audio_generation_status
tts_generation_status
timing_generation_status
question_generation_status
learner_facing_output_status
validator_required
source_promotion_status
content_promotion_status
public_distribution_default
```

Required values for design-stage packages:

```text
package_scope = listening_candidate_metadata_only
candidate_only = true
audio_generation_status = forbidden_until_later_approval
tts_generation_status = forbidden_until_later_approval
timing_generation_status = forbidden_until_later_approval
question_generation_status = forbidden_until_later_approval
learner_facing_output_status = forbidden_until_later_approval
validator_required = true
source_promotion_status = forbidden
content_promotion_status = forbidden
public_distribution_default = blocked
```

---

### 2.5 Source Manifest Reference Object

Required `source_manifest_ref` fields:

```text
manifest_path
manifest_schema_version
manifest_phase_id
manifest_record_count
manifest_hash_or_commit_ref
source_manifest_contract_path
```

Expected default values:

```text
manifest_path = ulga/graph/e4s_source_manifest.json
manifest_schema_version = E4S_SOURCE_MANIFEST_V1
manifest_phase_id = E4S-P0_SourceAuthorityAndCorpusRoadmap
source_manifest_contract_path = docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
```

The package must not copy source payload text from restricted references without explicit source-unit review and eligibility classification.

---

### 2.6 Validator Contract Reference Object

Required `validator_contract_ref` fields:

```text
validator_contract_path
validator_contract_task_id
validator_contract_version
required_report_schema_version
required_error_code_set
strict_mode_default
```

Expected default values:

```text
validator_contract_path = docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
validator_contract_task_id = E4S-P5-S2_ListeningValidatorContract_DesignScan
validator_contract_version = E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1
strict_mode_default = false
```

---

### 2.7 Audio Policy Reference Object

Required `audio_policy_ref` fields:

```text
audio_policy_path
audio_policy_task_id
audio_policy_version
audio_generation_default
tts_generation_default
timing_generation_default
playback_ui_default
voice_policy_required
storage_policy_required
```

Expected default values:

```text
audio_policy_path = docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
audio_policy_task_id = E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan
audio_policy_version = E4S_P5_LISTENING_AUDIO_POLICY_V1
audio_generation_default = forbidden
tts_generation_default = forbidden
timing_generation_default = forbidden
playback_ui_default = forbidden
voice_policy_required = true
storage_policy_required = true
```

---

### 2.8 Candidate Record Base Schema

Every future candidate record must contain at least:

```text
candidate_id
candidate_type
eligibility_class
candidate_status
source_trace
source_text
source_metadata
level_situation_metadata
listening_policy
audio_policy
tts_policy
voice_policy
storage_policy
timing_policy
public_distribution_policy
learner_state_policy
validator_handoff
created_by_task_id
```

Candidate IDs must be stable and deterministic:

```text
candidate_id = p5_<candidate_type_short>_<source_id_slug>_<source_unit_id_slug>
```

Candidate records must be sorted by `candidate_id`.

---

### 2.9 Candidate Type Enum

Allowed candidate types:

```text
sentence_listening_candidate
dialogue_listening_candidate
passage_listening_candidate
```

Blocked candidate types in V1:

```text
word_only_audio_candidate
phonics_drill_candidate
pronunciation_assessment_candidate
open_speaking_candidate
asr_response_candidate
adaptive_review_candidate
learner_specific_assignment_candidate
```

Reason:

```text
V1 candidate package is for source-grounded listening candidate metadata only. Phonics, pronunciation assessment, ASR, speaking, adaptive review, and learner-specific assignment require separate contracts.
```

---

### 2.10 Eligibility Class Enum

Allowed eligibility classes:

```text
P5_ELIGIBLE_VERIFIED_SENTENCE
P5_ELIGIBLE_VERIFIED_DIALOGUE
P5_ELIGIBLE_VERIFIED_PASSAGE
P5_DESIGN_CANDIDATE_ONLY
P5_REFERENCE_ONLY
P5_BLOCKED_STATUS_ARTIFACT
P5_BLOCKED_GENERATED_UNREVIEWED
P5_BLOCKED_LICENSE_OR_DISTRIBUTION
P5_BLOCKED_UNKNOWN_TRACE
```

Package rule:

```text
Only P5_ELIGIBLE_VERIFIED_SENTENCE, P5_ELIGIBLE_VERIFIED_DIALOGUE, and P5_ELIGIBLE_VERIFIED_PASSAGE may proceed to future validator PASS consideration.
All other classes must remain blocked or design-only.
```

---

### 2.11 Source Trace Object

Required `source_trace` fields:

```text
source_id
source_family
authority_role
source_path_or_reference
source_record_hash_or_stable_ref
source_unit_id
source_unit_type
source_unit_ref
license_status
review_status
promotion_rule
allowed_use
blocked_use
manual_review_status
public_distribution_status
```

Source trace rules:

```text
source_id must exist in the source manifest
source_family must be routable by P5-S1 policy
authority_role must be allowed by P5 validator contract
source_unit_id must be stable
status/governance/readback artifacts must never be content sources
RAZ word list evidence must never be direct audio source
reference-only sources must never be direct listening content
unreviewed generated candidates must never be direct listening content
```

---

### 2.12 Source Text Object

Required `source_text` fields:

```text
source_text_raw
source_text_normalized
text_language
text_normalization_policy
text_segmentation_policy
text_review_status
sensitive_content_review_status
child_suitability_review_status
```

Text rules:

```text
source_text_normalized must be non-empty for eligible candidates
text_normalization_policy must be versioned before implementation
text_segmentation_policy must match candidate_type
restricted source text must not be copied for public distribution without license approval
```

---

### 2.13 Source Metadata Object

Required `source_metadata` fields:

```text
source_title_or_display_name
source_level_system
raw_level_code
normalized_level_band
level_claim_status
source_owner_or_origin
source_license_note
source_review_owner
source_review_date_or_ref
```

Metadata rules:

```text
source level is source metadata only
source level is not learner placement
source metadata alone cannot assign learner path
source metadata alone cannot authorize audio or public output
```

---

### 2.14 Level / Situation Metadata Object

Required `level_situation_metadata` fields:

```text
normalized_level_band
level_claim_status
situation_domain
situation_context
communicative_function
interaction_mode
skill_fit
situation_claim_status
situation_sensitivity_flag
```

Allowed `skill_fit` values for this package:

```text
listening_candidate
multi_skill_reference_only
unknown_blocked
```

Rules:

```text
listening_candidate does not mean audio-ready
multi_skill_reference_only cannot become direct content
unknown_blocked must fail or remain blocked
```

---

### 2.15 Listening Policy Object

Required `listening_policy` fields:

```text
listening_item_type_candidates
listening_item_generation_status
question_generation_status
answer_generation_status
distractor_generation_status
scoring_status
student_facing_status
```

Allowed future `listening_item_type_candidates` values:

```text
listen_and_choose_picture
listen_and_choose_sentence
listen_and_fill_word
dictation_lite
listen_and_order_sentences
short_dialogue_listening
passage_main_idea_listening
```

Current required values:

```text
listening_item_generation_status = forbidden_in_schema_design
question_generation_status = forbidden_in_schema_design
answer_generation_status = forbidden_in_schema_design
distractor_generation_status = forbidden_in_schema_design
scoring_status = forbidden_in_schema_design
student_facing_status = forbidden_until_later_approval
```

---

### 2.16 Audio / TTS / Voice / Storage / Timing Policy Objects

Required `audio_policy` fields:

```text
audio_generation_status
audio_asset_id
audio_asset_path
audio_policy_version
human_audio_permission_status
```

Required `tts_policy` fields:

```text
tts_permission_status
tts_generation_status
tts_provider
tts_voice_id
tts_policy_version
```

Required `voice_policy` fields:

```text
voice_policy_status
voice_policy_version
accent_label
speed_profile
speaker_role_mapping_status
pronunciation_override_policy_status
```

Required `storage_policy` fields:

```text
storage_policy_status
storage_policy_version
intended_storage_layer
public_storage_status
asset_naming_policy_status
```

Required `timing_policy` fields:

```text
timing_policy_status
timing_policy_version
timing_required_status
timing_metadata_path
timing_alignment_method
```

Current design-stage required values:

```text
audio_generation_status = forbidden
audio_asset_id = null
audio_asset_path = null
tts_generation_status = forbidden
tts_provider = null
tts_voice_id = null
public_storage_status = blocked
timing_metadata_path = null
timing_alignment_method = none
```

---

### 2.17 Public Distribution Policy Object

Required `public_distribution_policy` fields:

```text
public_distribution_status
license_clearance_status
source_attribution_status
derivative_audio_permission_status
child_safety_status
privacy_status
```

Required default values:

```text
public_distribution_status = blocked
license_clearance_status = not_cleared_by_default
derivative_audio_permission_status = not_cleared_by_default
```

---

### 2.18 Learner State Policy Object

Required `learner_state_policy` fields:

```text
learner_state_update_status
learner_response_capture_status
adaptive_assignment_status
review_scheduling_status
mastery_score_status
weakness_tag_status
placement_status
```

Required default values:

```text
learner_state_update_status = forbidden
learner_response_capture_status = forbidden
adaptive_assignment_status = forbidden
review_scheduling_status = forbidden
mastery_score_status = forbidden
weakness_tag_status = forbidden
placement_status = forbidden
```

---

### 2.19 Validator Handoff Object

Required `validator_handoff` fields:

```text
validator_required
validator_contract_path
validator_contract_version
expected_report_path
blocking_error_codes_ref
warning_codes_ref
pass_fail_gate_ref
candidate_order_key
```

Required values:

```text
validator_required = true
validator_contract_path = docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
validator_contract_version = E4S_P5_LISTENING_VALIDATOR_CONTRACT_V1
expected_report_path = ulga/listening/reports/e4s_listening_validator_report.json
candidate_order_key = candidate_id
```

---

### 2.20 Sentence Candidate Variant

Additional required fields for `sentence_listening_candidate`:

```text
sentence_id
sentence_boundary_policy
sentence_context_ref
sentence_order_ref
sentence_audio_scope
```

Required rules:

```text
candidate_type = sentence_listening_candidate
source_unit_type = sentence
eligibility_class may be P5_ELIGIBLE_VERIFIED_SENTENCE only after validator gates
sentence_audio_scope = single_sentence
```

---

### 2.21 Dialogue Candidate Variant

Additional required fields for `dialogue_listening_candidate`:

```text
dialogue_id
dialogue_turns
turn_count
speaker_roles
speaker_order_policy
multi_speaker_audio_policy
p4_handoff_status
```

Each dialogue turn must contain:

```text
turn_id
speaker_role
speaker_order
turn_text
turn_boundary_policy
```

Required rules:

```text
candidate_type = dialogue_listening_candidate
source_unit_type = dialogue
p4_handoff_status must be reviewed or explicitly blocked
speaker_roles must be stable before future audio generation
multi_speaker_audio_policy must exist before future TTS/human audio
```

---

### 2.22 Passage Candidate Variant

Additional required fields for `passage_listening_candidate`:

```text
passage_id
sentence_ids
sentence_order
paragraph_or_page_ref
passage_boundary_policy
p1_handoff_status
```

Required rules:

```text
candidate_type = passage_listening_candidate
source_unit_type = passage
sentence_ids must be stable
sentence_order must be deterministic
p1_handoff_status must be reviewed or explicitly blocked
passage_boundary_policy must exist before future audio generation
```

---

### 2.23 Candidate Counts Object

Required `candidate_counts` fields:

```text
total_candidates
by_candidate_type
by_eligibility_class
by_source_family
by_public_distribution_status
by_learner_facing_status
by_audio_generation_status
by_validator_readiness
```

Rules:

```text
counts must be derived from candidate records
counts must not be manually asserted if builder exists
counts must not be interpreted as learner progress
counts must not authorize implementation by themselves
```

---

### 2.24 Deterministic Ordering Rules

Package ordering rules:

```text
candidates sorted by candidate_id ascending
dialogue_turns sorted by speaker_order ascending
passage sentence_ids sorted by sentence_order ascending
issues and reports sorted according to validator contract
JSON key order should be stable where implementation language allows
```

Duplicate handling:

```text
duplicate candidate_id must fail future validation
duplicate source_unit_id may be allowed only across different candidate_type if explicit policy allows
duplicate dialogue turn_id within same dialogue must fail future validation
duplicate passage sentence order within same passage must fail future validation
```

---

### 2.25 Forbidden Package Contents

The package must not contain:

```text
audio binary data
base64 audio
TTS-generated text-to-audio output
timing arrays generated from real audio
listening questions
answers
distractors
scoring rubrics
learner_id
learner response history
mastery score
weakness tags
review schedule
adaptive assignment
student-facing HTML
public downloadable audio path
content promotion flag
source authority promotion flag
```

---

### 2.26 Minimal Example Shape

This is a shape example only, not package data:

```json
{
  "schema_version": "E4S_LISTENING_CANDIDATE_PACKAGE_V1",
  "epic_id": "E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem",
  "phase_id": "E4S-P5_ListeningPracticeSystem",
  "task_id": "E4S-P5-FUTURE_CandidatePackageBuilder",
  "package_id": "p5_listening_candidate_package_v1",
  "package_policy": {
    "package_scope": "listening_candidate_metadata_only",
    "candidate_only": true,
    "audio_generation_status": "forbidden_until_later_approval",
    "tts_generation_status": "forbidden_until_later_approval",
    "timing_generation_status": "forbidden_until_later_approval",
    "question_generation_status": "forbidden_until_later_approval",
    "learner_facing_output_status": "forbidden_until_later_approval",
    "validator_required": true,
    "source_promotion_status": "forbidden",
    "content_promotion_status": "forbidden",
    "public_distribution_default": "blocked"
  },
  "candidates": []
}
```

The example intentionally contains no actual candidate records.

---

## 3. Gate & Distance Update

### 3.1 Acceptance Gates for P5-S3

| Gate | Result | Evidence |
|---|---:|---|
| P5-S2 validator contract acknowledged | PASS | Validator contract exists |
| P5-S3 deliverable created | PASS | This file |
| Intended future package path defined | PASS | Section 2.2 |
| Top-level package schema defined | PASS | Section 2.3 |
| Package policy object defined | PASS | Section 2.4 |
| Source manifest ref object defined | PASS | Section 2.5 |
| Validator contract ref object defined | PASS | Section 2.6 |
| Audio policy ref object defined | PASS | Section 2.7 |
| Candidate base schema defined | PASS | Section 2.8 |
| Candidate type enum defined | PASS | Section 2.9 |
| Eligibility class enum defined | PASS | Section 2.10 |
| Source trace object defined | PASS | Section 2.11 |
| Source text object defined | PASS | Section 2.12 |
| Source metadata object defined | PASS | Section 2.13 |
| Level/situation metadata object defined | PASS | Section 2.14 |
| Listening policy object defined | PASS | Section 2.15 |
| Audio/TTS/voice/storage/timing policy objects defined | PASS | Section 2.16 |
| Public distribution policy object defined | PASS | Section 2.17 |
| Learner state policy object defined | PASS | Section 2.18 |
| Validator handoff object defined | PASS | Section 2.19 |
| Sentence/dialogue/passage variants defined | PASS | Sections 2.20-2.22 |
| Deterministic ordering rules defined | PASS | Section 2.24 |
| Forbidden contents defined | PASS | Section 2.25 |
| Runtime impact avoided | PASS | Documentation only |
| Candidate JSON package avoided | PASS | No package data created |
| Validator implementation avoided | PASS | No Python code |
| Audio/TTS/timing generation avoided | PASS | No audio/TTS/timing output |
| Listening question generation avoided | PASS | No questions/answers/distractors |
| Learner-facing output avoided | PASS | No site/listening output |
| Learner state avoided | PASS | No learner files |
| Source/content promotion avoided | PASS | No promotion artifacts |

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
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
```

Sub-task Status:

```text
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan -> COMPLETED
```

P5 design gate state:

```text
E4S-P5_SOURCE_ELIGIBILITY_POLICY -> DEFINED
E4S-P5_VALIDATOR_CONTRACT -> DEFINED
E4S-P5_CANDIDATE_PACKAGE_SCHEMA -> DEFINED
```

P5 implementation-readiness state:

```text
E4S-P5_IMPLEMENTATION_READINESS -> READY_FOR_READBACK_QA
E4S-P5_IMPLEMENTATION -> NOT_OPENED_BY_THIS_DESIGNSCAN
```

Remaining minimum design/schema distance before implementation-readiness readback:

```text
D_P5_DESIGN_SCHEMA = 0 required design/schema gates left
```

Implementation still requires explicit operator approval after readback.

Known blocked work:

```text
validator Python implementation
candidate JSON package generation
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
issue_id: E4S-P5-S3-DEFER-001
severity: high
affected_file_or_artifact: ulga/listening/candidates/e4s_listening_candidate_package.json
classification: FUTURE_WORK
why_deferred: P5-S3 defines schema only and does not create package data.
recommended_future_task: future operator-approved P5 candidate package builder implementation after readback
blocks_current_task: no
```

```text
issue_id: E4S-P5-S3-DEFER-002
severity: high
affected_file_or_artifact: tools/validate_e4s_listening_candidates.py
classification: FUTURE_WORK
why_deferred: Validator implementation requires S2 contract and S3 schema, but is not part of this design scan.
recommended_future_task: future operator-approved P5 validator implementation after readback
blocks_current_task: no
```

```text
issue_id: E4S-P5-S3-DEFER-003
severity: high
affected_file_or_artifact: audio / TTS / timing assets
classification: FUTURE_WORK
why_deferred: Audio/TTS/timing generation remains forbidden until candidate data and validator implementation pass future gates.
recommended_future_task: future operator-approved P5 audio implementation after validator/package gates
blocks_current_task: no
```

```text
issue_id: E4S-P5-S3-DEFER-004
severity: high
affected_file_or_artifact: listening questions / student-facing UI
classification: FUTURE_WORK
why_deferred: Question generation and learner-facing UI require candidate package data, validator pass, audio policy, and separate learner-facing approval.
recommended_future_task: future learner-facing listening UI gate
blocks_current_task: no
```

---

## 5. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P5-READBACK_ListeningDesignSchemaReadinessQA
```

Only next allowed action:

```text
Create docs/ulga/E4S_P5_LISTENING_DESIGN_SCHEMA_READINESS_QA.md to verify that P5-S1, P5-S2, and P5-S3 are present, summarize PASS / WARNING / DEFERRED state, confirm D_P5_DESIGN_SCHEMA = 0, and decide whether a future operator-approved implementation task may start with validator implementation or candidate package builder implementation.
```

Stop condition:

```text
Stop here. Do not implement the validator, do not create listening candidate JSON packages, and do not generate audio, TTS, timing, playback, listening questions, or listening UI from this design scan.
```
