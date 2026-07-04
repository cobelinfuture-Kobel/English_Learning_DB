# E4S P5 Listening Validator Contract Design Scan

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
E4S-P5-S2_ListeningValidatorContract_DesignScan
```

Data Sources and Ordering Basis:

```text
1. docs/ulga/E4S_P5_LISTENING_SOURCE_ELIGIBILITY_AND_AUDIO_POLICY.md
2. docs/ulga/E4S_P0_CLOSEOUT_SOURCE_AUTHORITY_FOUNDATION_READBACK_QA.md
3. docs/ulga/E4S_P5_LISTENING_PRACTICE_SYSTEM_START_GATE_PREFLIGHT.md
4. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
5. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
6. ulga/graph/e4s_source_manifest.json
7. ulga/reports/e4s_source_manifest_summary.json
8. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
9. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
10. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
11. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable for This Sub-task:

```text
docs/ulga/E4S_P5_LISTENING_VALIDATOR_CONTRACT.md
```

This task defines the Phase 5 listening validator contract only. It does not implement `tools/validate_e4s_listening_candidates.py`, does not create candidate JSON packages, does not generate audio, does not generate TTS, does not create timing files, does not create playback UI, does not create listening questions, does not create learner-facing output, and does not update learner state.

---

## 2. Core Execution

### 2.1 Phase 5 S2 Decision

Decision:

```text
E4S-P5-S2_ListeningValidatorContract_DesignScan -> COMPLETED
```

Phase 5 validator state after this task:

```text
E4S-P5_VALIDATOR_CONTRACT -> DEFINED
E4S-P5_VALIDATOR_IMPLEMENTATION -> NOT_STARTED
E4S-P5_IMPLEMENTATION -> STILL_BLOCKED
```

Rationale:

```text
P5-S1 defined source eligibility and audio policy. P5-S2 now defines the validator contract that future candidate packages and future validator code must satisfy. Because no candidate package schema exists yet and no validator code is implemented here, no listening candidate JSON, audio, timing, question, UI, learner-facing output, or learner-state artifact is allowed.
```

---

### 2.2 Validator Scope

The future P5 validator must validate only metadata and candidate-package contracts unless a later implementation task explicitly expands scope.

Allowed validator scope:

```text
read candidate package JSON
read source manifest metadata
check source trace completeness
check authority-role and source-family constraints
check eligibility class
check license/public-distribution flags
check review status
check audio policy references
check TTS permission flags
check voice policy references
check timing policy references if timing metadata exists
check learner-facing approval flags
check no-learner-state boundary
produce deterministic validation report
```

Forbidden validator scope:

```text
generate audio
generate TTS
call TTS provider
create timing metadata
align text to audio
create listening questions
create answers or distractors
render HTML
write site/listening output
update learner state
rank learner weakness
schedule review
promote source/content authority
modify source manifest records
modify candidate packages during validation
```

---

### 2.3 Required Validator Inputs

A future validator implementation must accept these logical inputs:

| Input | Required? | Expected Role |
|---|---:|---|
| `candidate_package_path` | yes | JSON package containing future listening candidates |
| `source_manifest_path` | yes | P0 source manifest metadata reference |
| `validator_policy_version` | yes | versioned validator contract identifier |
| `audio_policy_version` | yes | versioned audio/TTS/storage policy reference |
| `report_output_path` | yes | deterministic validation report path |
| `strict_mode` | optional | fail on warnings when explicitly enabled |

Required path defaults for future implementation may be:

```text
candidate_package_path = ulga/listening/candidates/e4s_listening_candidate_package.json
source_manifest_path = ulga/graph/e4s_source_manifest.json
report_output_path = ulga/listening/reports/e4s_listening_validator_report.json
```

This design scan does not create those paths.

---

### 2.4 Required Candidate Package Top-Level Fields

Future candidate package schema must contain at least:

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
candidates
```

Top-level expected values:

```text
schema_version = E4S_LISTENING_CANDIDATE_PACKAGE_V1
phase_id = E4S-P5_ListeningPracticeSystem
public_distribution_policy.default = blocked
learner_state_policy.learner_state_update = forbidden
learner_state_policy.adaptive_assignment = forbidden
```

---

### 2.5 Required Candidate Fields

Every future candidate record must contain at least:

```text
candidate_id
candidate_type
eligibility_class
source_id
source_family
authority_role
source_unit_id
source_unit_type
source_text_normalized
source_trace_status
license_status
review_status
promotion_rule
allowed_use
blocked_use
public_distribution_status
manual_review_status
level_claim_status
normalized_level_band
situation_domain
situation_context
communicative_function
interaction_mode
skill_fit
text_segmentation_policy
audio_policy_version
tts_permission_status
voice_policy_status
storage_policy_status
timing_policy_status
learner_facing_approval_status
learner_state_policy_status
adaptive_use_policy_status
created_by_task_id
```

Candidate type enum:

```text
sentence_listening_candidate
dialogue_listening_candidate
passage_listening_candidate
```

Eligibility class enum:

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

---

### 2.6 Blocking Error Codes

A future validator must treat these as blocking errors:

| Code | Blocking Condition | Required Handling |
|---|---|---|
| `P5_MISSING_SOURCE_TRACE` | Candidate lacks complete source_id/source_unit_id/source path or stable reference | fail |
| `P5_UNKNOWN_SOURCE_ID` | Candidate source_id is not represented in the source manifest | fail |
| `P5_UNKNOWN_SOURCE_FAMILY` | source_family is unknown or not routable | fail |
| `P5_UNAPPROVED_AUTHORITY_ROLE` | authority_role is not allowed for P5 candidate use | fail |
| `P5_STATUS_ARTIFACT_USED_AS_CONTENT` | status/readback/roadmap/dashboard artifact is used as listening content | fail |
| `P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT` | governance/roadmap document is used as content source | fail |
| `P5_GENERATED_UNREVIEWED_CONTENT` | generated candidate lacks manual review/promotion evidence | fail |
| `P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE` | RAZ word list evidence is used as direct audio/listening source | fail |
| `P5_REFERENCE_ONLY_USED_AS_CONTENT` | vocabulary/grammar/frequency/reference source is used directly as listening content | fail |
| `P5_LICENSE_PUBLIC_DISTRIBUTION_UNKNOWN` | public_distribution_status is missing or unknown | fail |
| `P5_RESTRICTED_SOURCE_MARKED_PUBLIC` | restricted_reference_only source is marked public | fail |
| `P5_MISSING_REVIEW_STATUS` | review_status or manual_review_status is absent | fail |
| `P5_MISSING_TEXT_UNIT_ID` | sentence/dialogue/passage unit ID is missing | fail |
| `P5_MISSING_SOURCE_TEXT_NORMALIZED` | normalized candidate text is missing or empty | fail |
| `P5_BAD_SEGMENTATION_POLICY` | candidate lacks valid segmentation policy for its type | fail |
| `P5_DIALOGUE_MISSING_TURN_MODEL` | dialogue candidate lacks turn/speaker model | fail |
| `P5_PASSAGE_MISSING_SENTENCE_ORDER` | passage candidate lacks sentence_ids or sentence_order | fail |
| `P5_SENTENCE_MISSING_CONTEXT_REF` | sentence candidate lacks sentence_context_ref when required | fail |
| `P5_MISSING_AUDIO_POLICY_VERSION` | candidate lacks versioned audio policy | fail |
| `P5_MISSING_TTS_PERMISSION` | tts_permission_status is missing | fail |
| `P5_TTS_ENABLED_WITHOUT_POLICY` | TTS is enabled without valid TTS policy | fail |
| `P5_MISSING_VOICE_POLICY` | voice_policy_status is missing or invalid | fail |
| `P5_MISSING_STORAGE_POLICY` | storage policy reference is missing | fail |
| `P5_PUBLIC_AUDIO_WITHOUT_LICENSE_CLEARANCE` | public audio is allowed before source/audio license clearance | fail |
| `P5_TIMING_PRESENT_WITHOUT_POLICY` | timing metadata exists without timing policy version | fail |
| `P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL` | learner-facing output flag/path exists without approval | fail |
| `P5_LEARNER_STATE_UPDATE_ATTEMPT` | candidate or package attempts learner-state update | fail |
| `P5_ADAPTIVE_ASSIGNMENT_ATTEMPT` | candidate or package attempts adaptive assignment/scheduling | fail |
| `P5_CONTENT_PROMOTION_ATTEMPT` | validator input tries to promote source/content authority | fail |
| `P5_NON_DETERMINISTIC_ORDER` | candidate order is not deterministic by candidate_id | fail |
| `P5_DUPLICATE_CANDIDATE_ID` | duplicate candidate_id exists | fail |
| `P5_BAD_PACKAGE_PHASE` | package phase_id is not E4S-P5_ListeningPracticeSystem | fail |
| `P5_BAD_SCHEMA_VERSION` | candidate package schema_version is missing/unknown | fail |

---

### 2.7 Warning Codes

A future validator may report these warnings when not blocking:

| Code | Warning Condition | Suggested Handling |
|---|---|---|
| `P5_WARN_INTERNAL_ONLY_SOURCE` | source is internal-only but not public | allow if public_distribution_status is blocked |
| `P5_WARN_TIMING_OPTIONAL_MISSING` | timing metadata is absent for item types where timing is optional | allow |
| `P5_WARN_LEVEL_BAND_UNVERIFIED` | normalized level band is provisional | allow only if item remains candidate-only |
| `P5_WARN_SITUATION_METADATA_COARSE` | situation metadata is coarse but present | allow |
| `P5_WARN_AUDIO_POLICY_PLACEHOLDER` | audio policy is referenced as future placeholder | allow only in design/candidate-only package |
| `P5_WARN_P4_HANDOFF_PENDING` | dialogue candidate depends on future P4 review | allow only as blocked/non-audio candidate |
| `P5_WARN_P1_HANDOFF_PENDING` | passage candidate depends on future P1 review | allow only as blocked/non-audio candidate |
| `P5_WARN_CHILD_SUITABILITY_REVIEW_PENDING` | child suitability review is pending | allow only if not learner-facing |
| `P5_WARN_PUBLIC_ATTRIBUTION_PENDING` | attribution details pending | allow only if public distribution is blocked |
| `P5_WARN_PRONUNCIATION_POLICY_PENDING` | pronunciation override policy not defined | allow unless pronunciation teaching is claimed |

Strict mode may upgrade warnings to failure only if explicitly requested by the operator or CI task.

---

### 2.8 Required Validation Report Schema

Future validator report must contain at least:

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

Report status enum:

```text
PASS
PASS_WITH_WARNINGS
FAIL_BLOCKING_ERRORS
FAIL_SCHEMA_ERRORS
FAIL_FORBIDDEN_TRANSITION
```

Issue object shape:

```text
code
severity
candidate_id
source_id
field
message
required_handling
```

Gate metrics must include:

```text
schema_version_valid
candidate_ids_unique
candidate_order_deterministic
source_trace_complete
source_manifest_cross_refs_valid
authority_roles_allowed
status_artifacts_blocked
generated_unreviewed_blocked
raz_wordlist_audio_blocked
license_public_distribution_checked
audio_policy_checked
tts_policy_checked
voice_policy_checked
storage_policy_checked
timing_policy_checked
learner_facing_output_blocked
learner_state_update_blocked
adaptive_assignment_blocked
content_promotion_blocked
```

---

### 2.9 Pass / Fail Gates

PASS is allowed only when:

```text
blocking_issue_count = 0
schema_version_valid = PASS
candidate_ids_unique = PASS
candidate_order_deterministic = PASS
source_trace_complete = PASS
source_manifest_cross_refs_valid = PASS
authority_roles_allowed = PASS
status_artifacts_blocked = PASS
generated_unreviewed_blocked = PASS
raz_wordlist_audio_blocked = PASS
license_public_distribution_checked = PASS
audio_policy_checked = PASS
tts_policy_checked = PASS
voice_policy_checked = PASS
storage_policy_checked = PASS
learner_facing_output_blocked = PASS
learner_state_update_blocked = PASS
adaptive_assignment_blocked = PASS
content_promotion_blocked = PASS
```

PASS_WITH_WARNINGS is allowed only when:

```text
blocking_issue_count = 0
warning_count > 0
all blocking gates = PASS
warnings do not imply learner-facing output, public distribution, learner-state update, adaptive assignment, or promotion
```

FAIL is required when:

```text
blocking_issue_count > 0
schema is invalid
candidate source trace is missing
status/governance/readback artifact is used as content
generated unreviewed content is used as audio source
RAZ word list is used as audio source
public output is attempted without license clearance
learner-facing output is attempted without approval
learner state update is attempted
adaptive scheduling is attempted
content/source promotion is attempted
```

---

### 2.10 Forbidden Transitions

These transitions must fail:

| Transition | Required Code |
|---|---|
| `status_artifact -> listening_content` | `P5_STATUS_ARTIFACT_USED_AS_CONTENT` |
| `roadmap -> listening_content` | `P5_GOVERNANCE_ARTIFACT_USED_AS_CONTENT` |
| `readback_report -> listening_content` | `P5_STATUS_ARTIFACT_USED_AS_CONTENT` |
| `raz_wordlist -> audio_source` | `P5_RAZ_WORDLIST_USED_AS_AUDIO_SOURCE` |
| `reference_only -> listening_content` | `P5_REFERENCE_ONLY_USED_AS_CONTENT` |
| `generated_unreviewed -> listening_content` | `P5_GENERATED_UNREVIEWED_CONTENT` |
| `restricted_reference_only -> public_audio` | `P5_RESTRICTED_SOURCE_MARKED_PUBLIC` |
| `candidate_package -> learner_facing_output` without approval | `P5_LEARNER_FACING_OUTPUT_WITHOUT_APPROVAL` |
| `candidate_package -> learner_state` | `P5_LEARNER_STATE_UPDATE_ATTEMPT` |
| `candidate_package -> adaptive_assignment` | `P5_ADAPTIVE_ASSIGNMENT_ATTEMPT` |
| `validator_pass -> content_authority_promotion` | `P5_CONTENT_PROMOTION_ATTEMPT` |

---

### 2.11 Determinism Requirements

Future validator implementation must be deterministic:

```text
input candidate order must be sorted by candidate_id
issues must be sorted by candidate_id, code, field
warnings must be sorted by candidate_id, code, field
report key ordering should be stable
counts must be recomputed from candidate records, not manually supplied
validator must not mutate input files
validator must not depend on wall-clock time except optional generated_at fields if explicitly approved
```

---

### 2.12 Compatibility with P5-S1 Policy

This validator contract enforces the P5-S1 policy boundaries:

```text
P5_AUDIO_GENERATION remains forbidden here.
P5_TTS_GENERATION remains forbidden here.
P5_AUDIO_FILE_CREATION remains forbidden here.
P5_TIMING_FILE_CREATION remains forbidden here.
P5_PLAYBACK_UI_CREATION remains forbidden here.
P5_PUBLIC_DISTRIBUTION remains blocked by default.
P5 learner-state update remains forbidden.
P5 adaptive assignment remains forbidden.
```

---

## 3. Gate & Distance Update

### 3.1 Acceptance Gates for P5-S2

| Gate | Result | Evidence |
|---|---:|---|
| P5-S1 policy acknowledged | PASS | P5 source eligibility/audio policy exists |
| P5-S2 deliverable created | PASS | This file |
| Validator scope defined | PASS | Section 2.2 |
| Required validator inputs defined | PASS | Section 2.3 |
| Required package top-level fields defined | PASS | Section 2.4 |
| Required candidate fields defined | PASS | Section 2.5 |
| Blocking error codes defined | PASS | Section 2.6 |
| Warning codes defined | PASS | Section 2.7 |
| Report schema defined | PASS | Section 2.8 |
| Pass/fail gates defined | PASS | Section 2.9 |
| Forbidden transitions defined | PASS | Section 2.10 |
| Determinism requirements defined | PASS | Section 2.11 |
| Runtime impact avoided | PASS | Documentation only |
| Validator implementation avoided | PASS | No Python code |
| Candidate JSON package avoided | PASS | No package created |
| Audio/TTS generation avoided | PASS | No audio/TTS output |
| Timing generation avoided | PASS | No timing files |
| Learner-facing output avoided | PASS | No site/listening output |
| Learner state avoided | PASS | No learner-state files |
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
E4S-P5-S2_ListeningValidatorContract_DesignScan
```

Sub-task Status:

```text
E4S-P5-S2_ListeningValidatorContract_DesignScan -> COMPLETED
```

P5 validator contract state:

```text
E4S-P5_VALIDATOR_CONTRACT -> DEFINED
```

P5 implementation state:

```text
E4S-P5_IMPLEMENTATION -> STILL_BLOCKED
```

Remaining minimum distance before any P5 implementation task:

```text
D_P5_IMPLEMENTATION_OPEN = 1 required design/schema gate left
```

Required gate still left:

```text
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
```

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
issue_id: E4S-P5-S2-DEFER-001
severity: high
affected_file_or_artifact: tools/validate_e4s_listening_candidates.py
classification: FUTURE_WORK
why_deferred: P5-S2 defines the validator contract but does not implement validator code.
recommended_future_task: future P5 validator implementation only after candidate package schema exists
blocks_current_task: no
```

```text
issue_id: E4S-P5-S2-DEFER-002
severity: high
affected_file_or_artifact: ulga/listening/candidates/
classification: FUTURE_WORK
why_deferred: Candidate package schema must be defined before any package is created.
recommended_future_task: E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P5-S2-DEFER-003
severity: high
affected_file_or_artifact: ulga/listening/reports/
classification: FUTURE_WORK
why_deferred: Validator report output is not created because no validator implementation runs in this task.
recommended_future_task: future P5 validator implementation
blocks_current_task: no
```

```text
issue_id: E4S-P5-S2-DEFER-004
severity: high
affected_file_or_artifact: audio / TTS / timing assets
classification: FUTURE_WORK
why_deferred: Audio/TTS/timing generation remains forbidden until validator, package schema, package data, and operator-approved implementation gates exist.
recommended_future_task: future operator-approved P5 audio implementation after validation gates
blocks_current_task: no
```

---

## 5. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P5-S3_ListeningCandidatePackageSchema_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P5_LISTENING_CANDIDATE_PACKAGE_SCHEMA.md to define the future listening candidate package schema, including top-level package fields, candidate record fields, source trace structure, sentence/dialogue/passage variants, enum values, deterministic ordering, and validator handoff requirements.
```

Stop condition:

```text
Stop here. Do not implement the validator, do not create listening candidate JSON packages, and do not generate audio, TTS, timing, playback, listening questions, or listening UI from this design scan.
```
