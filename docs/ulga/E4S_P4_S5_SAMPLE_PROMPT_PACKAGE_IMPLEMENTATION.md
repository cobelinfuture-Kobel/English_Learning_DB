# E4S-P4-S5 Sample Prompt Package Implementation

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S5_SamplePromptPackage_Implementation`

Status: `COMPLETED`

## 2. Implementation Scope

This task creates a small sample prompt/package artifact following:

- `E4S-P4-S2_SpeakingPromptContract_DesignScan`
- `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`
- `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`

This task does not implement:

- full prompt generator
- validator code
- role-play renderer
- ASR
- recording
- speech scoring
- audio pipeline
- student-facing UI
- learner-state integration
- final Dialogue Authority promotion

## 3. File Created

Created sample artifact:

```text
ulga/samples/e4s_p4_s5_sample_prompt_package_v1.json
```

Commit:

```text
f168f3c5c9ece54bc26a701e7075b23331910b7d
```

## 4. Artifact Contents

The sample artifact contains:

- 3 speaking prompt records
- 3 role-play prompt packages
- global prompt-only constraints
- AUX-S4 / AUX-S5 / AUX-S7 source-family policy
- candidate boundary objects on every prompt/package
- no ASR / scoring / audio / UI / learner-state claims

### 4.1 Speaking prompt records

| prompt_id | source_family | prompt_type | speaking_mode | status |
|---|---|---|---|---|
| `SPK_AUXS4_SAMPLE_000001` | AUX-S4 | functional_response | guided_response | candidate_only |
| `SPK_AUXS5_SAMPLE_000001` | AUX-S5 | role_play_turn | role_play | candidate_only |
| `SPK_AUXS7_SAMPLE_000001` | AUX-S7 | oral_sentence_builder | sentence_building | candidate_only |

### 4.2 Role-play prompt packages

| package_id | source_family | package_type | practice_mode | status |
|---|---|---|---|---|
| `RPP_AUXS5_SAMPLE_000001` | AUX-S5 | role_play_package | guided_role_play | candidate_only |
| `RPP_AUXS4_SAMPLE_000001` | AUX-S4 | substitution_role_play_package | parent_child_role_play | candidate_only |
| `RPP_AUXS7_SAMPLE_000001` | AUX-S7 | role_response_package | one_role_response | candidate_only |

## 5. Source Family Coverage

### AUX-S4

Sample coverage:

- functional sentence source
- derived parent/child role-play package
- explicit `no_original_dialogue_claim`
- candidate boundary allows review but blocks final authority / learner-facing / production-ready states

### AUX-S5

Sample coverage:

- story/context dialogue source
- role-play turn prompt
- structured shop scenario
- two roles: Shopkeeper and Customer
- ordered turn sequence
- prompt ref from package to speaking prompt record
- candidate boundary allows review but blocks final authority / learner-facing / production-ready states

### AUX-S7

Sample coverage:

- generated candidate source
- generated trace metadata
- `generated = true`
- `source_grounded = false` at package scenario level
- candidate boundary blocks review promotion by default
- blocked reasons preserve `aux_s7_not_candidate_only` and generated-authority guard

## 6. Contract Alignment

### P4-S2 alignment

Each speaking prompt record includes:

- `prompt_id`
- `source_family`
- `source_id`
- `source_trace`
- `prompt_type`
- `speaking_mode`
- `speaker_roles`
- `theme`
- `level_estimate`
- `input_text`
- `prompt_text`
- `expected_response_shape`
- `allowed_variation`
- `blocked_generation_behavior`
- `authority_status`
- `review_status`
- `validator_requirements`
- `candidate_boundary`

### P4-S3 alignment

Each package includes:

- `package_id`
- `package_type`
- `source_family`
- `source_ids`
- `source_trace`
- `scenario`
- `roles`
- `turn_sequence`
- `prompt_refs`
- `package_flow`
- `constraints`
- `authority_status`
- `review_status`
- `validator_requirements`
- `candidate_boundary`

### P4-S4 alignment

Every prompt/package includes:

- `candidate_boundary`
- `candidate_origin`
- `derivation_type`
- `generated`
- `source_grounding_status`
- `promotion_status`
- `allowed_next_statuses`
- `blocked_next_statuses`
- `promotion_gate_results`
- `blocked_reasons`

## 7. Non-Implementation Boundary

No code was added for:

- generation
- validation
- rendering
- audio
- ASR
- scoring
- UI
- learner-state integration

The artifact is data-only.

## 8. Manual Contract Readback

Manual readback status:

| Check | Status |
|---|---|
| JSON artifact created | PASS |
| Includes AUX-S4 sample | PASS |
| Includes AUX-S5 sample | PASS |
| Includes AUX-S7 sample | PASS |
| Includes speaking prompt records | PASS |
| Includes role-play prompt packages | PASS |
| Includes candidate boundaries | PASS |
| Preserves prompt-only boundary | PASS |
| No ASR claim | PASS |
| No scoring claim | PASS |
| No audio claim | PASS |
| No UI renderer claim | PASS |
| No final authority claim | PASS |
| No production-ready claim | PASS |
| No learner-facing-final claim | PASS |

## 9. Gate Metrics

- Sample JSON artifact created: PASS
- P4-S2 prompt record contract represented: PASS
- P4-S3 package contract represented: PASS
- P4-S4 boundary contract represented: PASS
- AUX-S4 sample represented: PASS
- AUX-S5 sample represented: PASS
- AUX-S7 sample represented: PASS
- AUX-S7 generated/candidate-only guard preserved: PASS
- Prompt-only V1 boundary preserved: PASS
- No generator code written: PASS
- No validator code written: PASS
- No renderer implemented: PASS
- No runtime modified: PASS
- No UI implemented: PASS
- No ASR/scoring/audio implemented: PASS

## 10. Distance Vector

Current sub-task:

`E4S-P4-S5_SamplePromptPackage_Implementation -> COMPLETED`

Remaining P4 sub-tasks:

1. `E4S-P4-S6_PromptValidator_Implementation`
2. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 2 sub-tasks left`

## 11. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S6_PromptValidator_Implementation`

Unique execution action:

Implement validator checks for P4-S2 prompt records, P4-S3 role-play packages, and P4-S4 candidate boundary rules against the S5 sample artifact. Do not implement full generator, renderer, ASR, audio, speech scoring, UI, learner-state integration, or final authority promotion.
