# E4S P5 I12 Internal Audio Pilot Implementation Readiness Decision

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I12_InternalAudioPilotImplementationReadinessDecision
```

Prerequisite evidence:

```text
E4S-P5-I11_TestEvidenceReadback -> PASS_LOCAL_SYNCED_AND_CLEAN
E4S-P5-I11_MANIFEST_SCHEMA_IMPLEMENTATION -> VALIDATED_LOCAL_PASS
E4S-P5-I11_MANIFEST_VALIDATION_REPORT -> SYNCED_TO_GITHUB
D_P5_I11_LOCAL_VALIDATION = 0
```

Current manifest evidence:

```text
status = PASS
blocking_issue_count = 0
warning_count = 0
selected_candidate_count = 1
audio_asset_count = 0
public_audio_asset_count = 0
learner_facing_audio_count = 0
```

## Decision

```text
E4S-P5-I12_InternalAudioPilotImplementationReadinessDecision -> COMPLETED
E4S-P5_INTERNAL_AUDIO_METADATA_DRY_RUN -> READY_TO_OPEN
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> NOT_READY
E4S-P5_TTS_PROVIDER_CALL -> NOT_ALLOWED
E4S-P5_HUMAN_AUDIO_RECORDING -> NOT_ALLOWED
E4S-P5_PUBLIC_OR_LEARNER_FACING_AUDIO -> NOT_ALLOWED
```

Meaning:

```text
P5 may open a metadata-only internal audio pilot dry-run for the selected sentence candidate.
P5 may not generate an mp3/wav file, call a TTS provider, record a human speaker, create timing files, or expose learner-facing playback.
```

## Rationale

The internal pilot manifest is valid and contains one selected sentence candidate. It also has zero audio assets and no public/learner-facing output.

A metadata-only dry-run is useful because it can test asset identity, naming, source binding, storage path planning, and validator behavior before any media generation.

Actual audio generation is not ready because:

```text
voice provider is not selected
human speaker is not selected
child-suitability review for a concrete voice is not complete
provider credential / local TTS engine boundary is not approved
audio byte generation method is not approved
timing review path is not implemented
```

## Approved I13 Scope

I13 may do:

```text
add one planned_not_generated audio asset metadata record to the internal pilot manifest
bind it to candidate_id = p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002
use voice_policy_id = E4S_P5_INTERNAL_SENTENCE_NEUTRAL_PLACEHOLDER_V1
use storage_policy_id = E4S_P5_INTERNAL_AUDIO_STORAGE_DRY_RUN_V1
set audio_generation_method = tts_or_human_placeholder_only
set audio_generation_status = planned_not_generated
set public_distribution_status = blocked
set learner_facing_status = blocked
update or run the manifest validator
produce a validation report
```

I13 must not do:

```text
create audio files
call TTS providers
record human audio
create timing files
create playback UI
create listening questions
create answer keys
create learner-facing output
write learner state
create adaptive scheduling
create public distribution artifacts
expand Seed Batch 002
```

## Required Metadata Defaults For I13

```text
audio_asset_id = p5_internal_audio_placeholder_001
candidate_id = p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002
source_unit_id = p5_sentence_002
package_id = p5_listening_candidate_package_v1
pilot_id = e4s_p5_seed_batch_001_internal_audio_pilot_v1
voice_policy_id = E4S_P5_INTERNAL_SENTENCE_NEUTRAL_PLACEHOLDER_V1
storage_policy_id = E4S_P5_INTERNAL_AUDIO_STORAGE_DRY_RUN_V1
audio_generation_method = tts_or_human_placeholder_only
audio_generation_status = planned_not_generated
audio_asset_path = ulga/listening/audio_internal/p5_listening_candidate_package_v1/p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002/p5_internal_audio_placeholder_001.mp3
public_distribution_status = blocked
learner_facing_status = blocked
review_status = pending_operator_review
created_by_task_id = E4S-P5-I13_InternalAudioPilotMetadataDryRunImplementation
```

The `audio_asset_path` is a planned metadata path only. It must not correspond to an actual media file in I13.

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I11 synced-clean evidence accepted | PASS |
| Manifest validator blocking issues | 0 |
| Selected candidate count | 1 |
| Audio asset count before I13 | 0 |
| Metadata-only dry-run readiness | PASS |
| Audio-byte generation readiness | NO |
| TTS provider call readiness | NO |
| Human recording readiness | NO |
| Public/learner-facing readiness | NO |

Distance vector:

```text
E4S-P5-I12_IMPLEMENTATION_READINESS_DECISION -> COMPLETED
E4S-P5_INTERNAL_AUDIO_METADATA_DRY_RUN -> READY_TO_OPEN
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> BLOCKED_UNTIL_EXPLICIT_VOICE_OR_PROVIDER_APPROVAL
E4S-P5_CONTENT_EXPANSION -> HOLD
D_P5_I12_READINESS_DECISION = 0
D_P5_I13_METADATA_DRY_RUN_IMPLEMENTATION = 1
```

## Stop Condition

```text
Stop here. I12 creates only this decision readback. It does not modify the pilot manifest, create audio metadata records, create audio files, call TTS, record human audio, create timing files, create playback UI, create questions, write learner state, create public distribution artifacts, or expand Seed Batch 002.
```

## Next Shortest Step

```text
E4S-P5-I13_InternalAudioPilotMetadataDryRunImplementation
```

Purpose:

```text
Add one planned-not-generated placeholder audio asset metadata record to the internal pilot manifest and validate it, without creating any audio file.
```

Suggested approval phrase:

```text
核准執行 E4S-P5-I13_InternalAudioPilotMetadataDryRunImplementation
```
