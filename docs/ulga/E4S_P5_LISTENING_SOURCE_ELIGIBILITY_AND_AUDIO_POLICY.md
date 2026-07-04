# E4S P5 Listening Source Eligibility and Audio Policy Design Scan

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
E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P0_CLOSEOUT_SOURCE_AUTHORITY_FOUNDATION_READBACK_QA.md
2. docs/ulga/E4S_P5_LISTENING_PRACTICE_SYSTEM_START_GATE_PREFLIGHT.md
3. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
4. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
5. ulga/graph/e4s_source_manifest.json
6. ulga/reports/e4s_source_manifest_summary.json
7. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
8. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
9. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
10. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable for This Sub-task:

```text
docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
```

This task defines the Phase 5 listening source eligibility and audio policy only. It does not generate audio, create TTS output, create timing files, create playback UI, create listening questions, create learner-facing output, update learner state, modify runtime code, or promote any source into listening authority.

---

## 2. Core Execution

### 2.1 Phase 5 S1 Decision

Decision:

```text
E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan -> COMPLETED
```

Phase 5 implementation state after this task:

```text
E4S-P5_ListeningPracticeSystem -> POLICY_DEFINED_FOR_DESIGNSCAN_ONLY
E4S-P5_IMPLEMENTATION -> STILL_BLOCKED
```

Rationale:

```text
P0 is closed as a source authority foundation. P5 may now define listening-specific source eligibility and audio policy, but the project still lacks a P5 validator contract, a P5 candidate package schema, and verified listening source packages. Therefore no implementation or learner-facing output is allowed in this task.
```

---

### 2.2 Listening Source Eligibility Classes

Phase 5 source units must be classified before any future audio or listening item can be created.

| Eligibility Class | Meaning | May Become Listening Candidate? | Required Handling |
|---|---|---:|---|
| `P5_ELIGIBLE_VERIFIED_SENTENCE` | A sentence unit with source trace, authority lane, level/situation metadata, license/review status, and validator-ready text | yes, after P5 validator exists | package as future listening candidate only |
| `P5_ELIGIBLE_VERIFIED_DIALOGUE` | A dialogue unit with speaker turns, source trace, review status, and future dialogue/speaking handoff evidence | yes, after P4/P5 review | package as future listening dialogue candidate only |
| `P5_ELIGIBLE_VERIFIED_PASSAGE` | A passage unit with source trace, stable text segmentation, level/situation metadata, and review status | yes, after P1/P5 review | package as future listening passage candidate only |
| `P5_DESIGN_CANDIDATE_ONLY` | Metadata or source family can inform policy design but does not contain verified audio-ready text units | no direct audio | use for schema/query design only |
| `P5_REFERENCE_ONLY` | Vocabulary, grammar, frequency, status, or governance sources | no | reference only; no direct listening asset |
| `P5_BLOCKED_STATUS_ARTIFACT` | Status page, readback, dashboard, or project progress artifact | no | must never become listening source |
| `P5_BLOCKED_GENERATED_UNREVIEWED` | AI/generated candidate text without promotion/review | no | manual review and promotion required before candidate packaging |
| `P5_BLOCKED_LICENSE_OR_DISTRIBUTION` | Source with restricted license that cannot support audio/public distribution | no public output | internal metadata only unless separate license policy approves |
| `P5_BLOCKED_UNKNOWN_TRACE` | Missing source ID, source path, review status, or provenance | no | fail validation / require intake repair |

---

### 2.3 Current Manifest Source-Family Routing for P5

The current P0 manifest summary records 16 source records and includes reading, dialogue, parent functional sentence, generated candidate, reference, governance, and status families. P5 must not interpret that manifest as direct audio authority.

| Current Source Family / Role Pattern | P5 Use | P5 Restriction |
|---|---|---|
| `raz_reading_corpus` / `reading_corpus_candidate` | possible future passage/sentence candidate source | requires source trace, review, segmentation, validator, and license/distribution check |
| `story_dialogue_corpus` / `dialogue_corpus_candidate` | possible future dialogue candidate source | requires dialogue turn schema, speaker-role review, P4/P5 handoff, and validator |
| `parent_functional_sentence_corpus` / `functional_sentence_corpus` | possible future short sentence/function listening candidate | requires text-unit extraction contract and P5 validator |
| `generated_content_candidate` / `generated_candidate` | no direct P5 use | must not become audio/listening source without manual review and promotion task |
| `raz_wordlist` / `evidence_only` | evidence/reference only | must not become vocabulary authority or direct listening content |
| `grammar_profile`, `vocabulary_profile`, `frequency_profile`, `cambridge_vocabulary`, `chunk_authority` | metadata/reference only | may inform level/vocabulary review; no direct audio |
| `assessment_pattern_corpus` | assessment pattern reference | no listening item generation in P5-S1 |
| `writing_template_corpus` | writing template reference | no direct listening audio |
| `governance`, `roadmap`, `status_artifact` | governance/status only | never source content, never audio content, never learner-facing output |

---

### 2.4 Required Source Trace for Future Listening Candidates

Any future P5 candidate package must carry these fields before it can be validated:

```text
source_id
source_family
authority_role
source_path_or_reference
source_record_hash_or_stable_ref
source_unit_id
source_unit_type
source_text_raw
source_text_normalized
text_segmentation_policy
source_level_system
raw_level_code
normalized_level_band
level_claim_status
situation_domain
situation_context
communicative_function
interaction_mode
skill_fit
license_status
review_status
promotion_rule
blocked_use
allowed_use
public_distribution_status
manual_review_status
validator_version
created_by_task_id
```

Future dialogue candidates must additionally carry:

```text
dialogue_id
turn_id
speaker_role
speaker_order
turn_text
turn_boundary_policy
multi_speaker_audio_policy
```

Future passage candidates must additionally carry:

```text
passage_id
sentence_ids
sentence_order
paragraph_or_page_ref
passage_boundary_policy
```

Future sentence candidates must additionally carry:

```text
sentence_id
sentence_boundary_policy
sentence_context_ref
```

---

### 2.5 Audio Generation Policy

Audio generation is not active in this task.

Current policy:

```text
P5_AUDIO_GENERATION = FORBIDDEN_IN_S1
P5_TTS_GENERATION = FORBIDDEN_IN_S1
P5_AUDIO_FILE_CREATION = FORBIDDEN_IN_S1
P5_TIMING_FILE_CREATION = FORBIDDEN_IN_S1
P5_PLAYBACK_UI_CREATION = FORBIDDEN_IN_S1
```

Future audio may be considered only after a later approved task defines and validates:

```text
1. candidate package schema
2. listening validator contract
3. text normalization policy
4. sentence/dialogue/passage segmentation policy
5. TTS permission policy
6. human-audio permission policy
7. license and public-distribution policy
8. voice/accent/speed policy
9. timing metadata policy
10. storage and naming policy
11. replay and caching policy
12. no-learner-state boundary
```

---

### 2.6 TTS Policy Boundary

TTS is not enabled by this document.

Future TTS may only be allowed under a separate approved task if all of the following are true:

```text
source unit is P5 eligible
source trace is complete
text is validator-clean
license permits derived audio or internal use only is explicitly scoped
voice/accent/speed policy is selected
public distribution status is explicit
storage path is approved
asset naming policy is approved
no learner-facing UI is created unless separately approved
no learner state is updated
```

Blocked TTS uses:

```text
TTS from status artifacts
TTS from readback documents
TTS from roadmap documents
TTS from unreviewed generated candidates
TTS from vocabulary lists as standalone authority
TTS from RAZ word list evidence
TTS from sources with unknown license status
TTS from sources missing source trace
TTS for public distribution before license review
TTS for adaptive learner assignment before P7
```

---

### 2.7 Audio Asset Storage Policy Boundary

No audio asset folder is created by this task.

Future storage policy must be defined before audio generation and should reserve these logical layers:

```text
ulga/listening/candidates/          # metadata packages only, no audio by default
ulga/listening/audio_internal/       # future internal-only generated or human audio
ulga/listening/timing_internal/      # future timing metadata, if approved
ulga/listening/reports/              # future validator reports
site/listening/                      # blocked until learner-facing approval
```

Storage rules:

```text
audio_internal must not be public by default
site/listening is forbidden before learner-facing approval
asset filename must include stable package ID, not source title alone
asset metadata must reference source_unit_id and validator_version
restricted_reference_only sources must not produce public audio
```

---

### 2.8 Voice / Accent / Speed Policy Boundary

No voice is selected by this task.

Future voice policy must define:

```text
voice_provider
voice_name_or_human_speaker_id
accent_label
speed_profile
child_suitability_review
speaker_role_mapping
multi_speaker_dialogue_policy
pronunciation_override_policy
versioned_voice_policy_id
```

Default future design assumption:

```text
single-sentence listening: one neutral learner-safe voice
short dialogue listening: explicit speaker-role mapping required
passage listening: stable speed profile required
pronunciation teaching: separate phonics/pronunciation policy required
```

---

### 2.9 Timing Metadata Policy Boundary

Timing metadata is not created by this task.

Future timing policy must define:

```text
audio_asset_id
source_unit_id
segment_id
segment_type
start_ms
end_ms
alignment_method
alignment_confidence
manual_review_status
timing_policy_version
```

Blocked timing uses:

```text
auto-aligning restricted source text for public output
using timing as evidence of learner progress
using timing to create adaptive assignment
creating playback UI before learner-facing approval
```

---

### 2.10 Listening Item-Type Boundary

This task defines possible future listening item types but does not create items.

Allowed future item-type candidates, after validator and source package gates:

| Future Item Type | Requires Audio? | Requires Timing? | Current S1 Status |
|---|---:|---:|---|
| `listen_and_choose_picture` | yes | optional | design only |
| `listen_and_choose_sentence` | yes | optional | design only |
| `listen_and_fill_word` | yes | optional | design only |
| `dictation_lite` | yes | optional | design only |
| `listen_and_order_sentences` | yes | optional | design only |
| `short_dialogue_listening` | yes | optional / recommended | design only |
| `passage_main_idea_listening` | yes | optional | design only |

Blocked item work in S1:

```text
question generation
answer generation
distractor generation
scoring implementation
worksheet export
HTML rendering
student-facing UI
learner response capture
```

---

### 2.11 Validator Requirements Before Learner-Facing Use

A future P5 validator must block at least these conditions:

```text
P5_MISSING_SOURCE_TRACE
P5_UNKNOWN_SOURCE_FAMILY
P5_UNAPPROVED_AUTHORITY_ROLE
P5_STATUS_ARTIFACT_USED_AS_CONTENT
P5_GENERATED_UNREVIEWED_CONTENT
P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE
P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN
P5_MISSING_REVIEW_STATUS
P5_MISSING_TEXT_UNIT_ID
P5_BAD_SEGMENTATION_POLICY
P5_MISSING_AUDIO_POLICY_VERSION
P5_MISSING_TTS_PERMISSION
P5_MISSING_VOICE_POLICY
P5_MISSING_STORAGE_POLICY
P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL
P5_LEARNER_STATE_UPDATE_ATTEMPT
P5_ADAPTIVE_ASSIGNMENT_ATTEMPT
```

Validator must report at least:

```text
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
next_shortest_step
```

---

### 2.12 Public Distribution Restrictions

Default policy:

```text
P5_PUBLIC_DISTRIBUTION = BLOCKED_BY_DEFAULT
```

Public distribution may not occur unless a later task verifies:

```text
source license permits public derivative output
TTS or human audio license permits public distribution
no restricted reference text is embedded improperly
source attribution requirements are satisfied
student-facing output has its own approval gate
privacy and child-safety requirements are satisfied
```

Internal-only design is allowed for future approved tasks, but only with explicit labeling:

```text
internal_only
restricted_reference_only
not_for_public_distribution
not_student_facing
```

---

### 2.13 No-Learner-State / No-Adaptive-Use Boundary

P5-S1 does not create learner progress, learner state, placement, review scheduling, weakness tags, mastery scores, or adaptive recommendations.

Invalid claims:

```text
The learner improved listening because P5 policy exists.
The learner should receive this audio because the source level is A1.
The learner has mastered a sentence because the audio exists.
The system can schedule listening review from source metadata alone.
The source is listening authority because it appears in the manifest.
A generated candidate can become listening content without review.
```

---

## 3. Gate & Distance Update

### 3.1 Acceptance Gates for P5-S1

| Gate | Result | Evidence |
|---|---:|---|
| P0 closeout acknowledged | PASS | P0 closeout allows P5-S1 DesignScan only |
| P5-S1 deliverable created | PASS | This file |
| Listening source eligibility classes defined | PASS | Section 2.2 |
| Current manifest source-family routing defined | PASS | Section 2.3 |
| Required source trace defined | PASS | Section 2.4 |
| Audio generation policy boundary defined | PASS | Section 2.5 |
| TTS boundary defined | PASS | Section 2.6 |
| Audio storage boundary defined | PASS | Section 2.7 |
| Voice/accent/speed boundary defined | PASS | Section 2.8 |
| Timing metadata boundary defined | PASS | Section 2.9 |
| Listening item-type boundary defined | PASS | Section 2.10 |
| Future validator requirements defined | PASS | Section 2.11 |
| Public distribution restriction defined | PASS | Section 2.12 |
| No-learner-state / no-adaptive-use boundary defined | PASS | Section 2.13 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Validator modification avoided | PASS | No Python change |
| Audio/TTS generation avoided | PASS | No audio/TTS output |
| Learner-facing output avoided | PASS | No site/listening output |
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
E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan
```

Sub-task Status:

```text
E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan -> COMPLETED
```

P5 policy state:

```text
E4S-P5_ListeningPracticeSystem -> SOURCE_ELIGIBILITY_AND_AUDIO_POLICY_DEFINED
```

P5 implementation state:

```text
E4S-P5_IMPLEMENTATION -> STILL_BLOCKED
```

Remaining minimum distance before any P5 implementation task:

```text
D_P5_IMPLEMENTATION_OPEN = 2 required design/validation gates left
```

Required gates still left:

```text
1. E4S-P5-S2_ListeningValidatorContract_DesignScan
2. E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
```

Known blocked work:

```text
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
issue_id: E4S-P5-S1-DEFER-001
severity: high
affected_file_or_artifact: tools/validate_e4s_listening_candidates.py
classification: FUTURE_WORK
why_deferred: P5-S1 defines validator requirements only and does not implement validator code.
recommended_future_task: E4S-P5-S2_ListeningValidatorContract_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P5-S1-DEFER-002
severity: high
affected_file_or_artifact: ulga/listening/candidates/
classification: FUTURE_WORK
why_deferred: Candidate packages require schema and validator gates before creation.
recommended_future_task: E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P5-S1-DEFER-003
severity: high
affected_file_or_artifact: audio / TTS assets
classification: FUTURE_WORK
why_deferred: Audio/TTS generation is explicitly forbidden in P5-S1.
recommended_future_task: future operator-approved P5 audio implementation after validator and package gates
blocks_current_task: no
```

```text
issue_id: E4S-P5-S1-DEFER-004
severity: high
affected_file_or_artifact: site/listening/
classification: FUTURE_WORK
why_deferred: Learner-facing listening UI requires separate approval after source, validator, package, and audio policies pass.
recommended_future_task: future learner-facing listening UI gate
blocks_current_task: no
```

```text
issue_id: E4S-P5-S1-DEFER-005
severity: medium
affected_file_or_artifact: ulga/graph/e4s_source_manifest.json
classification: FUTURE_WORK
why_deferred: This task routes existing manifest families but does not add P5-specific fields or records.
recommended_future_task: future manifest expansion only if P5 candidate packages require source registry fields
blocks_current_task: no
```

---

## 5. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P5-S2_ListeningValidatorContract_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md to define the blocking validator contract for future listening candidate packages, including error codes, warning codes, report schema, required inputs, forbidden transitions, and pass/fail gates.
```

Stop condition:

```text
Stop here. Do not generate audio, TTS, timing, playback, listening questions, listening candidate JSON packages, or listening UI from this design scan.
```
