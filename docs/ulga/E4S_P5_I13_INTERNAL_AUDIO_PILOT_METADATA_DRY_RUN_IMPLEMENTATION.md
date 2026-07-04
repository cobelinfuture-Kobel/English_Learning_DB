# E4S P5 I13 Internal Audio Pilot Metadata Dry Run Implementation

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I13_InternalAudioPilotMetadataDryRunImplementation
```

Decision:

```text
E4S-P5-I13_InternalAudioPilotMetadataDryRunImplementation -> IMPLEMENTED_PENDING_LOCAL_VALIDATION
```

## Files Updated

```text
ulga/listening/audio_manifests/e4s_p5_seed_batch_001_internal_audio_pilot_manifest.json
tests/test_validate_e4s_internal_audio_pilot_manifest.py
```

Commits:

```text
8226578169de5f4c43df46200d08db360431ad63  add planned metadata asset
d1838b11a2b88619d913e00df01cacf6b75d141f  update manifest test expectations
```

## Metadata Dry Run

One placeholder metadata asset was added:

```text
audio_asset_id = p5_internal_audio_placeholder_001
candidate_id = p5_sentence_parent_functional_sentence_corpus_reference_p5_sentence_002
audio_generation_status = planned_not_generated
public_distribution_status = blocked
learner_facing_status = blocked
review_status = pending_operator_review
```

The recorded asset path is metadata only. I13 does not create a media file.

## Expected Validation

```text
status = PASS
blocking_issue_count = 0
warning_count = 0
selected_candidate_count = 1
audio_asset_count = 1
internal_audio_asset_count = 1
public_audio_asset_count = 0
learner_facing_audio_count = 0
```

Expected tests:

```text
tests.test_validate_e4s_internal_audio_pilot_manifest -> 6 tests OK
```

## Boundary

I13 does not open media generation, provider calls, human recording, timing generation, playback UI, questions, learner-state writes, adaptive scheduling, public distribution, or Seed Batch 002.

## Gate And Distance Update

```text
E4S-P5-I13_METADATA_DRY_RUN_IMPLEMENTATION -> IMPLEMENTED_PENDING_LOCAL_VALIDATION
E4S-P5_INTERNAL_AUDIO_BYTES_GENERATION -> STILL_BLOCKED
D_P5_I13_LOCAL_VALIDATION = 1
```

## Required Local Commands

```text
git pull origin main
python tools/validate_e4s_internal_audio_pilot_manifest.py --manifest ulga/listening/audio_manifests/e4s_p5_seed_batch_001_internal_audio_pilot_manifest.json --candidate-package ulga/listening/candidates/e4s_listening_candidate_package.json --report-output ulga/listening/reports/e4s_internal_audio_pilot_manifest_validator_report.json
python -m unittest tests.test_validate_e4s_internal_audio_pilot_manifest
python -m unittest tests.test_validate_e4s_listening_audio_policy
python -m unittest tests.test_validate_e4s_listening_candidates
python -m unittest tests.test_build_e4s_listening_candidate_package
git status
```

If the report changes:

```text
git add ulga/listening/reports/e4s_internal_audio_pilot_manifest_validator_report.json
git commit -m "reports: refresh E4S P5 internal audio pilot manifest validation report"
git push origin main
git status
```

## Next Shortest Step

```text
E4S-P5-I13_TestEvidenceReadback
```
