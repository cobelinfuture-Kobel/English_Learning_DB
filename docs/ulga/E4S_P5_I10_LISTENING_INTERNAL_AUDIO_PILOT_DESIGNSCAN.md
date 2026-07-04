# E4S P5 I10 Listening Internal Audio Pilot DesignScan

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I10_ListeningInternalAudioPilot_DesignScan
```

Prerequisite state:

```text
E4S-P5-I9_INTERNAL_AUDIO_PILOT_READINESS_DECISION -> COMPLETED
E4S-P5_INTERNAL_AUDIO_PILOT_DESIGN -> READY_TO_OPEN
E4S-P5_INTERNAL_AUDIO_GENERATION -> BLOCKED_UNTIL_PILOT_DESIGN_AND_OPERATOR_APPROVAL
E4S-P5_CONTENT_EXPANSION -> HOLD
```

I10 is a DesignScan only. It defines a strictly internal, non-public pilot design and does not generate audio, call TTS providers, record human audio, create timing files, create playback UI, create listening questions, create answer keys, write learner state, create adaptive scheduling, create public distribution artifacts, or expand Seed Batch 002.

## Decision

```text
E4S-P5-I10_ListeningInternalAudioPilot_DesignScan -> COMPLETED
E4S-P5_INTERNAL_AUDIO_PILOT_DESIGN -> DEFINED_FOR_ONE_SENTENCE_DRY_RUN
E4S-P5_INTERNAL_AUDIO_GENERATION -> STILL_BLOCKED
```

Rationale:

```text
Seed Batch 001 has three validated candidates, but the first pilot should use the lowest-risk candidate only. The owned parent-functional sentence candidate has the cleanest source path and does not require dialogue speaker-role mapping or passage timing review.
```

## Pilot Candidate Selection

Selected first-pilot candidate:

```text
candidate_id = p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002
candidate_type = sentence_listening_candidate
source_id = PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE
source_unit_id = p5_sentence_002
source_text = What time does the next train leave?
situation_domain = public_transport
situation_context = asking_for_schedule
communicative_function = inquiry
pilot_status = SELECTED_FOR_INTERNAL_AUDIO_PILOT_DESIGN_ONLY
```

Excluded from first-pilot audio design:

```text
p5_dialogue_story_dialogue_corpus_reference_p5_dialogue_002
reason = restricted_reference_only source and dialogue speaker-role voice mapping is not reviewed

p5_passage_raz_reading_corpus_a_t_candidate_p5_passage_002
reason = restricted_reference_only source and passage timing/review path is not reviewed
```

These exclusions are not content rejection. They only prevent them from entering the first internal audio pilot.

## Internal Pilot Asset Manifest Schema Draft

Future manifest path:

```text
ulga/listening/audio_manifests/e4s_p5_seed_batch_001_internal_audio_pilot_manifest.json
```

Draft manifest shape:

```json
{
  "schema_version": "E4S_P5_INTERNAL_AUDIO_PILOT_MANIFEST_V1",
  "pilot_id": "e4s_p5_seed_batch_001_internal_audio_pilot_v1",
  "pilot_status": "DESIGN_ONLY_NOT_GENERATED",
  "candidate_package_ref": "ulga/listening/candidates/e4s_listening_candidate_package.json",
  "audio_policy_ref": "ulga/listening/policies/e4s_p5_audio_voice_storage_policy_v1.json",
  "public_distribution_status": "blocked",
  "learner_facing_status": "blocked",
  "audio_assets": []
}
```

No manifest file is created by I10.

## Audio Asset Metadata Contract

Future dry-run audio asset metadata must include:

```text
audio_asset_id
candidate_id
source_unit_id
package_id
pilot_id
voice_policy_id
storage_policy_id
audio_generation_method
audio_generation_status
audio_asset_path
public_distribution_status
learner_facing_status
review_status
created_by_task_id
```

Required first-pilot defaults:

```text
audio_generation_method = tts_or_human_placeholder_only
audio_generation_status = planned_not_generated
public_distribution_status = blocked
learner_facing_status = blocked
review_status = pending_operator_review
```

## Voice Policy Decision Table

I10 does not select a real provider, credential, or human speaker.

Draft decision table:

| Candidate Type | Voice Need | First Pilot Handling |
|---|---|---|
| sentence | one neutral learner-safe voice | allowed as placeholder policy only |
| dialogue | speaker-role mapping | excluded from first pilot |
| passage | stable neutral voice and speed | excluded from first pilot |

Future first-pilot voice policy placeholder:

```text
voice_policy_id = E4S_P5_INTERNAL_SENTENCE_NEUTRAL_PLACEHOLDER_V1
voice_provider = not_selected
voice_name_or_human_speaker_id = not_selected
accent_label = neutral_unspecified
speed_profile = normal_slow_learner_safe_placeholder
child_suitability_review_status = pending_operator_review
speaker_role_mapping_status = not_applicable
```

## Storage Dry-Run Contract

Future local-only dry-run path pattern:

```text
ulga/listening/audio_internal/p5_listening_candidate_package_v1/{candidate_id}/
```

Future deterministic audio filename pattern:

```text
{candidate_id}__{voice_policy_id}__001.mp3
```

I10 does not create the folder or file.

Storage requirements for future implementation:

```text
path must remain under ulga/listening/audio_internal/
site/listening/ remains disallowed
public_distribution_status must remain blocked
learner_facing_status must remain blocked
```

## Timing Placeholder Handoff

Timing is out of scope for first audio dry-run.

Future timing placeholder may record:

```text
timing_policy_status = not_created
timing_required_status = optional_after_audio_review
timing_metadata_path = null
timing_alignment_method = none
```

Timing cannot become evidence for learner progress, mastery, adaptive scheduling, or public playback.

## Future Validator Requirements

A later implementation may add an audio manifest validator. Required checks:

```text
manifest schema/id valid
pilot_id stable
candidate_id exists in package
selected candidate is from approved pilot selection
asset path under ulga/listening/audio_internal/
no asset path under site/listening/
public_distribution_status blocked
learner_facing_status blocked
voice_policy_id present
storage_policy_id present
no timing file required before audio review
```

Expected report fields:

```text
pilot_id
pilot_status
selected_candidate_count
audio_asset_count
internal_audio_asset_count
public_audio_asset_count
learner_facing_audio_count
blocking_issue_count
warning_count
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I9 prerequisite accepted | PASS |
| First-pilot candidate selected | PASS |
| Dialogue/passage excluded from first pilot | PASS |
| Internal asset manifest schema drafted | PASS |
| Voice policy placeholder drafted | PASS |
| Storage dry-run contract drafted | PASS |
| Timing placeholder handoff drafted | PASS |
| Future validator requirements drafted | PASS |
| Audio generated by I10 | NO |
| TTS provider called by I10 | NO |
| Human audio recorded by I10 | NO |
| Timing files created by I10 | NO |
| Playback UI created by I10 | NO |
| Seed Batch 002 created by I10 | NO |

Distance vector:

```text
E4S-P5-I10_INTERNAL_AUDIO_PILOT_DESIGNSCAN -> COMPLETED
E4S-P5_INTERNAL_AUDIO_PILOT_DESIGN -> DEFINED_FOR_ONE_SENTENCE_DRY_RUN
E4S-P5_INTERNAL_AUDIO_GENERATION -> STILL_BLOCKED_UNTIL_OPERATOR_APPROVED_IMPLEMENTATION
E4S-P5_CONTENT_EXPANSION -> HOLD
D_P5_I10_DESIGN = 0
D_P5_I11_INTERNAL_AUDIO_PILOT_MANIFEST_SCHEMA_IMPLEMENTATION = 1
```

## Stop Condition

```text
Stop here. I10 produces only this design document. It does not create audio manifests, audio files, TTS output, timing files, playback UI, questions, answer keys, learner-facing output, learner-state writes, adaptive scheduling, public distribution, or Seed Batch 002.
```

## Next Shortest Step

```text
E4S-P5-I11_InternalAudioPilotManifestSchemaImplementation
```

Purpose:

```text
Create the machine-readable internal audio pilot manifest schema and validator for the selected one-sentence pilot candidate, without generating audio.
```

Suggested approval phrase:

```text
核准執行 E4S-P5-I11_InternalAudioPilotManifestSchemaImplementation
```
