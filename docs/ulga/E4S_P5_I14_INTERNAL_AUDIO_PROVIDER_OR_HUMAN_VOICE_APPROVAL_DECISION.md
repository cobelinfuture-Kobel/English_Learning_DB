# E4S P5 I14 Internal Audio Provider Or Human Voice Approval Decision

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I14_InternalAudioProviderOrHumanVoiceApprovalDecision
```

Prerequisite evidence:

```text
E4S-P5-I13_TestEvidenceReadback -> PASS_LOCAL_SYNCED_AND_CLEAN
E4S-P5-I13_METADATA_DRY_RUN_IMPLEMENTATION -> VALIDATED_LOCAL_PASS
E4S-P5-I13_MANIFEST_VALIDATION_REPORT -> SYNCED_TO_GITHUB
D_P5_I13_LOCAL_VALIDATION = 0
```

Current manifest state:

```text
selected_candidate_count = 1
audio_asset_count = 1
internal_audio_asset_count = 1
public_audio_asset_count = 0
learner_facing_audio_count = 0
audio_generation_status = planned_not_generated
```

## Decision

```text
E4S-P5-I14_InternalAudioProviderOrHumanVoiceApprovalDecision -> COMPLETED
E4S-P5_INTERNAL_AUDIO_PROVIDER_APPROVAL -> NOT_APPROVED_INPUT_MISSING
E4S-P5_HUMAN_VOICE_APPROVAL -> NOT_APPROVED_INPUT_MISSING
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> HOLD_METADATA_ONLY
E4S-P5_PUBLIC_OR_LEARNER_FACING_AUDIO -> NOT_ALLOWED
```

Meaning:

```text
No concrete TTS provider, local engine, or human speaker path was supplied.
Therefore P5 must remain metadata-only and must not create mp3/wav files yet.
```

## Rationale

I13 proves the metadata pipeline:

```text
one selected sentence candidate
one planned-not-generated metadata asset
validator PASS
zero public audio assets
zero learner-facing audio assets
```

But a metadata asset is not permission to generate audio bytes. Audio generation still requires an explicit provider or human voice approval package.

## Required Approval Inputs Before Audio Bytes

Future approval must specify one path only:

```text
path_a = local_or_provider_tts
path_b = human_recorded_voice
```

For a TTS path, required inputs:

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

For a human voice path, required inputs:

```text
speaker_identity_or_label
speaker_permission_status
recording_permission_status
child_suitability_review_status
voice_usage_scope
storage_scope
output_format
local_storage_only_confirmation
public_distribution_status = blocked
learner_facing_status = blocked
operator_approval_phrase
```

## Not Approved In I14

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

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I13 synced-clean evidence accepted | PASS |
| Metadata asset exists | PASS |
| Concrete TTS provider supplied | NO |
| Concrete local TTS engine supplied | NO |
| Concrete human speaker approval supplied | NO |
| Audio bytes generation approved | NO |
| Public/learner-facing output approved | NO |
| Metadata-only hold decision | PASS |

Distance vector:

```text
E4S-P5-I14_PROVIDER_OR_HUMAN_VOICE_APPROVAL_DECISION -> COMPLETED
E4S-P5_INTERNAL_AUDIO_PROVIDER_APPROVAL -> NOT_APPROVED_INPUT_MISSING
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> HOLD_METADATA_ONLY
E4S-P5_CONTENT_EXPANSION -> HOLD
D_P5_I14_APPROVAL_DECISION = 0
D_P5_I15_APPROVAL_INPUT_GATE = 1
```

## Stop Condition

```text
Stop here. I14 creates only this decision readback. It does not modify the manifest, does not create audio files, does not call TTS, does not record human audio, does not create timing/UI/questions, and does not expand Seed Batch 002.
```

## Next Shortest Step

```text
E4S-P5-I15_InternalAudioVoiceApprovalInputGate
```

Purpose:

```text
Collect a concrete operator-approved TTS provider/local engine or human speaker approval package before any audio-byte generation task can be opened.
```

Suggested approval phrase if keeping metadata-only hold:

```text
核准執行 E4S-P5-I15_InternalAudioVoiceApprovalInputGate
```
