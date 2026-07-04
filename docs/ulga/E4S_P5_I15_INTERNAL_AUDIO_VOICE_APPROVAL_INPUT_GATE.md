# E4S P5 I15 Internal Audio Voice Approval Input Gate

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I15_InternalAudioVoiceApprovalInputGate
```

Operator direction:

```text
走TTS
```

Decision:

```text
E4S-P5-I15_InternalAudioVoiceApprovalInputGate -> COMPLETED_INPUT_INCOMPLETE
E4S-P5_AUDIO_APPROVAL_PATH -> TTS_SELECTED
E4S-P5_TTS_APPROVAL_PACKAGE -> MISSING_REQUIRED_FIELDS
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> STILL_BLOCKED
E4S-P5_PUBLIC_OR_LEARNER_FACING_AUDIO -> NOT_ALLOWED
```

## Meaning

The project direction is now TTS, not human-recorded voice.

However, the TTS path is not yet executable because the concrete TTS approval package is incomplete. I15 records the path selection only. It does not approve provider calls or audio file generation.

## Required TTS Approval Fields

Before any TTS dry-run can be opened, the operator must provide:

```text
provider_or_engine_name
local_or_remote_execution_mode
credential_requirement_status
voice_name_or_id
accent_label
speed_profile
child_suitability_review_status
license_or_terms_status
output_format
local_storage_only_confirmation
public_distribution_status = blocked
learner_facing_status = blocked
operator_approval_phrase
```

## Current Filled Fields

```text
approval_path = TTS
public_distribution_status = blocked
learner_facing_status = blocked
```

## Current Missing Fields

```text
provider_or_engine_name = MISSING
local_or_remote_execution_mode = MISSING
credential_requirement_status = MISSING
voice_name_or_id = MISSING
accent_label = MISSING
speed_profile = MISSING
child_suitability_review_status = MISSING
license_or_terms_status = MISSING
output_format = MISSING
local_storage_only_confirmation = MISSING
operator_approval_phrase = MISSING
```

## Not Approved In I15

```text
generate audio files
call TTS providers
record human audio
create timing files
create playback UI
create listening questions
create answer keys
create student-facing output
write learner state
create adaptive scheduling
create public distribution artifacts
expand Seed Batch 002
```

## Recommended TTS Package Template

The next operator input can use this shape:

```text
provider_or_engine_name = <e.g. edge-tts / local Piper / other>
local_or_remote_execution_mode = <local_only / remote_api>
credential_requirement_status = <none_required / required_not_supplied / supplied_locally_not_committed>
voice_name_or_id = <exact voice id>
accent_label = <e.g. en-US / en-GB / neutral>
speed_profile = <e.g. normal_slow_learner_safe>
child_suitability_review_status = operator_approved
license_or_terms_status = internal_only_allowed
output_format = mp3
local_storage_only_confirmation = true
public_distribution_status = blocked
learner_facing_status = blocked
operator_approval_phrase = 核准此 TTS path 只做 local/internal audio-byte dry run，不公開、不學生端使用
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I14 prerequisite accepted | PASS |
| TTS path selected | PASS |
| Human voice path rejected for now | PASS |
| Provider or engine named | NO |
| Voice id supplied | NO |
| License/terms status supplied | NO |
| Child suitability review supplied | NO |
| Audio bytes generation approved | NO |
| Metadata-only hold preserved | PASS |

Distance vector:

```text
E4S-P5-I15_AUDIO_VOICE_APPROVAL_INPUT_GATE -> COMPLETED_INPUT_INCOMPLETE
E4S-P5_AUDIO_APPROVAL_PATH -> TTS_SELECTED
E4S-P5_TTS_APPROVAL_PACKAGE -> MISSING_REQUIRED_FIELDS
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> STILL_BLOCKED
D_P5_I15_INPUT_GATE = 0
D_P5_I16_TTS_APPROVAL_PACKAGE_INTAKE = 1
```

## Stop Condition

```text
Stop here. I15 records TTS as the selected path only. It does not modify the manifest, create audio files, call TTS, create timing/UI/questions, or expand Seed Batch 002.
```

## Next Shortest Step

```text
E4S-P5-I16_TTSApprovalPackageIntake
```

Purpose:

```text
Intake the concrete TTS provider/local engine, voice id, execution mode, license/terms status, output format, and internal-only approval before any local audio-byte dry-run is opened.
```
