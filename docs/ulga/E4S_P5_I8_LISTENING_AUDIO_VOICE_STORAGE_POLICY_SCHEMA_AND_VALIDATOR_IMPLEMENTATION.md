# E4S P5 I8 Listening Audio Voice Storage Policy Schema And Validator Implementation

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I8_ListeningAudioVoiceStoragePolicySchemaAndValidatorImplementation
```

Decision:

```text
E4S-P5-I8_ListeningAudioVoiceStoragePolicySchemaAndValidatorImplementation -> IMPLEMENTED_PENDING_LOCAL_VALIDATION
```

Scope:

```text
machine-readable policy schema/manifest
compact dedicated audio-policy validator
unit test coverage
```

No audio, TTS, timing files, playback UI, learner-facing output, learner state, public distribution, or Seed Batch 002 was created.

## Files Created Or Updated

Created:

```text
ulga/listening/policies/e4s_p5_audio_voice_storage_policy_v1.json
tools/validate_e4s_listening_audio_policy.py
tests/test_validate_e4s_listening_audio_policy.py
```

Implementation commits:

```text
83794e9fb819e42060d09515c09adf6ce9998063  policy schema manifest
087d9633a4476779ab3722e444253e6a036df7d1  compact audio policy validator
ae44b7877312b9424fdd1c98370c61dcd49f2b0a  unit tests added
a9cf1dcd0436b8ecaad5e66c7376522423ee5631  unit test alignment patch
```

## Validator Coverage

The new validator checks:

```text
policy schema/id
internal audio path policy
internal timing path policy
candidate audio policy version
voice policy presence
storage policy presence
audio asset path internal-only
public audio attempt
learner-facing audio attempt
dialogue audio speaker-role mapping
human-audio permission ref
TTS internal-only scope
timing without audio asset
timing path internal-only
```

The report adds:

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

## Expected Current Result

For the current Seed Batch 001 package, expected validator result is:

```text
status = PASS_WITH_WARNINGS
blocking_issue_count = 0
candidate_count = 3
audio_asset_count = 0
```

Expected warnings are allowed because current candidates still have no timing files, placeholder voice policy, and restricted/internal source constraints.

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I8 policy schema manifest created | PASS |
| I8 validator script created | PASS |
| I8 unit test file created | PASS |
| Audio/TTS/timing output avoided | PASS |
| Learner-facing output avoided | PASS |
| Local validator run | PENDING_OPERATOR |
| Local unittest run | PENDING_OPERATOR |
| Working tree clean after pull/test | PENDING_OPERATOR |

Distance vector:

```text
E4S-P5-I8_SCHEMA_AND_VALIDATOR_IMPLEMENTATION -> IMPLEMENTED_PENDING_LOCAL_VALIDATION
D_P5_I8_LOCAL_VALIDATION = 1 required evidence gate left
```

## Required Local Commands

```text
git pull origin main
python tools/validate_e4s_listening_audio_policy.py --policy ulga/listening/policies/e4s_p5_audio_voice_storage_policy_v1.json --candidate-package ulga/listening/candidates/e4s_listening_candidate_package.json --report-output ulga/listening/reports/e4s_listening_audio_policy_validator_report.json
python -m unittest tests.test_validate_e4s_listening_audio_policy
python -m unittest tests.test_validate_e4s_listening_candidates
python -m unittest tests.test_build_e4s_listening_candidate_package
git status
```

If the new report is generated locally, commit it after successful validation:

```text
git add ulga/listening/reports/e4s_listening_audio_policy_validator_report.json
git commit -m "reports: add E4S P5 audio policy validation report"
git push origin main
git status
```

## Next Shortest Step

```text
E4S-P5-I8_TestEvidenceReadback
```
