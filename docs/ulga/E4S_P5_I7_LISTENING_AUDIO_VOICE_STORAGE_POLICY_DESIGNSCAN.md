# E4S P5 I7 Listening Audio Voice Storage Policy DesignScan

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I7_ListeningAudioVoiceStoragePolicy_DesignScan
```

Prerequisite state:

```text
E4S-P5-I6_POST_VALIDATION_POLICY_DECISION -> COMPLETED
E4S-P5_SEED_BATCH_001_STATUS -> ACCEPTED_INTERNAL_ONLY_CANDIDATE_METADATA
E4S-P5_CONTENT_EXPANSION -> HOLD
E4S-P5_AUDIO_VOICE_STORAGE_POLICY -> REQUIRED_NEXT
```

Current evidence:

```text
candidate_count = 3
eligible_candidate_count = 3
validator_status = PASS_WITH_WARNINGS
blocking_issue_count = 0
public_distribution_status = blocked for all candidates
learner_facing_status = not approved for all candidates
```

I7 is documentation only. It does not create audio, TTS, timing, playback UI, listening questions, learner-facing output, learner state, or Seed Batch 002.

## Decision

```text
E4S-P5-I7_ListeningAudioVoiceStoragePolicy_DesignScan -> COMPLETED
E4S-P5_AUDIO_VOICE_STORAGE_POLICY -> DESIGN_DEFINED
E4S-P5_AUDIO_IMPLEMENTATION -> NOT_OPENED_BY_I7
```

Reason:

```text
Seed Batch 001 proves the metadata/package/validator path. The next real blocker is a versioned policy contract for audio permission, voice selection, storage naming, timing placeholders, and validator gates.
```

## Policy Version

```text
policy_id = E4S_P5_AUDIO_VOICE_STORAGE_POLICY_V1
policy_status = DESIGN_DEFINED_NOT_IMPLEMENTED
scope = internal_only_candidate_audio_policy_design
public_distribution_default = blocked
learner_facing_default = blocked
```

## TTS Permission Boundary

TTS is not enabled by I7.

A later task may only consider internal-only TTS when:

```text
candidate package status is PASS or PASS_WITH_WARNINGS
blocking_issue_count = 0
source trace is complete
manual review status is present
public distribution is blocked
learner-facing output is not approved
voice_policy_id is selected
storage_policy_id is selected
```

TTS must not be used for public distribution, source promotion, learner-state update, adaptive assignment, unreviewed generated text, status/readback docs, roadmap docs, RAZ wordlist evidence, or unknown source trace.

## Human Audio Boundary

Human-recorded audio is separate from TTS and also remains disabled by I7.

Future human audio metadata must include:

```text
speaker_permission_status
recording_permission_status
voice_identity_policy
child_safety_review
storage_policy_id
source_unit_id binding
```

Human audio is only a rendering of validated text. It is not source authority.

## Voice Policy Contract

Future voice policy records should include:

```text
voice_policy_id
voice_provider
voice_name_or_human_speaker_id
voice_type
accent_label
speed_profile
child_suitability_review_status
speaker_role_mapping_status
pronunciation_override_policy_status
policy_version
review_status
created_by_task_id
```

Defaults:

```text
sentence candidate = one learner-safe neutral voice
dialogue candidate = explicit speaker-role mapping required
passage candidate = stable neutral voice and speed profile
pronunciation teaching = separate future policy
```

## Storage And Naming Policy

I7 defines logical future paths only:

```text
ulga/listening/audio_internal/{package_id}/{candidate_id}/
ulga/listening/timing_internal/{package_id}/{candidate_id}/
ulga/listening/audio_manifests/
ulga/listening/reports/
```

Blocked until later learner-facing approval:

```text
site/listening/
```

Future deterministic names:

```text
audio: {candidate_id}__{voice_policy_id}__{asset_sequence}.mp3
timing: {candidate_id}__{audio_asset_id}__timing_v1.json
```

Asset metadata must bind:

```text
audio_asset_id
candidate_id
source_unit_id
package_id
voice_policy_id
storage_policy_id
audio_generation_method
public_distribution_status
learner_facing_status
review_status
```

## Timing Placeholder Policy

Timing remains disabled by I7.

Future timing metadata should include:

```text
audio_asset_id
candidate_id
source_unit_id
segment_id
segment_type
segment_text
start_ms
end_ms
alignment_method
alignment_confidence
manual_review_status
timing_policy_version
```

Timing cannot be used as learner-progress evidence, adaptive scheduling evidence, mastery evidence, or public playback proof.

## Future Validator Gate Extensions

I8 should create policy schema and validator checks for:

```text
missing audio policy
missing policy version
missing voice policy
missing dialogue speaker-role mapping
missing storage policy
audio asset path outside internal layer
public audio attempt
learner-facing audio attempt
timing without audio asset
invalid timing segment order
missing human-audio permission metadata
```

Expected report additions:

```text
audio_policy_status
voice_policy_status
storage_policy_status
timing_policy_status
audio_asset_count
internal_audio_asset_count
public_audio_asset_count
learner_facing_audio_count
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I6 prerequisite accepted | PASS |
| Audio policy version named | PASS |
| TTS boundary defined | PASS |
| Human-audio boundary defined | PASS |
| Voice policy contract defined | PASS |
| Storage naming policy defined | PASS |
| Timing placeholder policy defined | PASS |
| Future validator extensions listed | PASS |
| Audio created by I7 | NO |
| Timing created by I7 | NO |
| Playback UI created by I7 | NO |
| Seed Batch 002 created by I7 | NO |

Distance vector:

```text
E4S-P5-I7_AUDIO_VOICE_STORAGE_POLICY_DESIGNSCAN -> COMPLETED
E4S-P5_AUDIO_VOICE_STORAGE_POLICY -> DESIGN_DEFINED
E4S-P5_AUDIO_IMPLEMENTATION -> BLOCKED_UNTIL_POLICY_SCHEMA_AND_VALIDATOR
E4S-P5_CONTENT_EXPANSION -> HOLD
D_P5_I7_POLICY_DESIGN = 0
D_P5_I8_POLICY_SCHEMA_AND_VALIDATOR = 1
```

## Next Shortest Step

```text
E4S-P5-I8_ListeningAudioVoiceStoragePolicySchemaAndValidatorImplementation
```

Purpose:

```text
Create machine-readable policy schema/manifest and add validator checks for audio, voice, storage, and timing policy metadata without generating audio or creating learner-facing output.
```

Suggested approval phrase:

```text
核准執行 E4S-P5-I8_ListeningAudioVoiceStoragePolicySchemaAndValidatorImplementation
```
