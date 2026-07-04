# E4S P5 I16A TTS Deferred For Future Readback

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I16A_TTSDeferredForFutureReadback
```

Operator decision:

```text
I16 沒有批准, TTS這個先跳過記錄起來,以後再來用
```

## Decision

```text
E4S-P5-I16A_TTSDeferredForFutureReadback -> COMPLETED
E4S-P5_AUDIO_APPROVAL_PATH -> TTS_SELECTED_BUT_DEFERRED
E4S-P5_TTS_APPROVAL_PACKAGE -> NOT_REQUIRED_NOW_DEFERRED
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> STILL_BLOCKED
E4S-P5_P5_NEXT_WORK -> RETURN_TO_NON_AUDIO_OR_OPERATOR_SELECTED_TRACK
```

## Meaning

TTS remains the preferred future route if P5 later resumes audio-byte generation.

For now, TTS is skipped. No provider, engine, voice id, license/terms status, or child-suitability review is required in this immediate step.

## Deferred Future TTS Requirements

When TTS is resumed later, the required approval package remains:

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

## Not Approved Now

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
| I16 blocker accepted | PASS |
| TTS selected as future path | PASS |
| TTS skipped for current phase | PASS |
| Audio bytes generation approved | NO |
| Metadata-only hold preserved | PASS |

Distance vector:

```text
E4S-P5-I16A_TTS_DEFERRED_FOR_FUTURE -> COMPLETED
E4S-P5_TTS_APPROVAL_PACKAGE -> DEFERRED_FUTURE_WORK
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> STILL_BLOCKED
E4S-P5_AUDIO_TRACK -> HOLD
D_P5_I16A_DEFER_TTS = 0
```

## Stop Condition

```text
Stop here. I16A records the defer decision only. It does not modify the manifest, create audio files, call TTS, create timing/UI/questions, or expand Seed Batch 002.
```

## Next Shortest Step

```text
E4S-P5-I17_P5NonAudioNextTrackDecision
```

Purpose:

```text
Choose the next non-audio P5 track or explicitly pause P5 after the audio/TTS line is deferred.
```
