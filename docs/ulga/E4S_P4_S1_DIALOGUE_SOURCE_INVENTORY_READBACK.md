# E4S-P4-S1 Dialogue Source Inventory Readback

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S1_DialogueSourceInventory_Readback`

Status: `COMPLETED`

## 2. Source Basis

This readback uses the approved E4S corpus roadmap and AUX corpus allocation rules.

Key alignment points:

- E4S Phase 4 is Dialogue / Speaking Prompt System.
- Phase 4 source families are AUX-S4, AUX-S5, and AUX-S7.
- V1 boundary is prompt-only.
- Recording, ASR, speaking score, app UI, and learner-state integration are out of scope.

## 3. Phase 4 Source Readback Table

| AUX Line | Source Family | Correct Role | Allowed Use in P4 V1 | Blocked Use in P4 V1 | Authority / Promotion Status | Readback Status |
|---|---|---|---|---|---|---|
| AUX-S4 | Parent Functional Sentence Corpus | Functional sentence / oral prompt source | daily routine prompt, parent-child command prompt, speaking practice prompt, substitution prompt | Treating it as full dialogue authority; assuming speaker turns or narrative context when absent | evidence/candidate source; requires later source manifest and review before promotion | ACCEPTED_FOR_P4_SOURCE_INVENTORY |
| AUX-S5 | Story Dialogue Corpus | Context dialogue / story retelling source | role-play prompt, character-line prompt, story-retell prompt, dialogue comprehension prompt | Flattening into isolated sentence authority; ignoring role/order/context | candidate/authority candidate depending on source trace, license, structure, and review | ACCEPTED_FOR_P4_SOURCE_INVENTORY |
| AUX-S7 | Generated Content Candidates | Generated candidate pool only | fill missing dialogue context, create derived prompt variants, provide controlled prompt candidates | Direct authority promotion; learner-facing output without review; source-grounded claim without evidence | candidate_only; generated=true; review_status=pending | ACCEPTED_WITH_STRICT_GUARD |

## 4. Source-Specific Notes

### AUX-S4 Parent Functional Sentence Corpus

AUX-S4 should remain functional-sentence oriented.

Expected P4 usage:

- daily routine speaking prompts
- parent-child command prompts
- short oral response prompts
- sentence substitution drills
- simple situational oral prompts

Guard:

- Do not label AUX-S4 as Dialogue Corpus.
- Do not infer missing speakers unless a later derivation task explicitly creates speaker roles.
- Do not promote directly into Dialogue Authority without source manifest, license, review, and contract validation.

### AUX-S5 Story Dialogue Corpus

AUX-S5 is the stronger source line for dialogue and speaking authority candidates because it may contain role, narration, line order, character turns, context, and story sequence.

Expected P4 usage:

- role-play prompts
- story retelling prompts
- character-response prompts
- dialogue sequence prompts
- context-based oral response prompts

Guard:

- Preserve speaker/context/story order when available.
- Do not flatten story dialogue into isolated sentence-only records.
- Do not generate learner-facing prompt packages before prompt contract and validator exist.

### AUX-S7 Generated Content Candidates

AUX-S7 must stay candidate-only.

Expected P4 usage:

- controlled prompt variants
- derived role-play expansions
- missing-context fill candidates
- common-error or oral-response candidates

Required fields for any future generated candidate:

- `generated = true`
- `authority_status = candidate_only`
- `review_status = pending`
- `source_traceability` pointing to source material or generation basis

Guard:

- Generated content cannot be treated as authority.
- Generated content cannot be source-grounded unless trace evidence exists.
- Generated content cannot be promoted without explicit review and validator checks.

## 5. P4 V1 Boundary

P4 V1 may produce prompt contracts and reviewed prompt packages.

P4 V1 must not implement:

- recording
- ASR
- speech scoring
- pronunciation scoring
- audio pipeline
- student-facing app
- adaptive learner-state recommendation
- final Dialogue Authority promotion

## 6. Required Future Contract Fields

The next design scan should define a prompt contract with at least:

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
- `expected_response_shape`
- `allowed_variation`
- `blocked_generation_behavior`
- `authority_status`
- `review_status`
- `validator_requirements`

## 7. Gate Metrics

- Phase 4 source families identified: PASS
- AUX-S4 role separated from Dialogue Corpus: PASS
- AUX-S5 role identified as story/context dialogue source: PASS
- AUX-S7 constrained as generated candidate only: PASS
- Prompt-only V1 boundary preserved: PASS
- No generator code written: PASS
- No runtime modified: PASS
- No UI implemented: PASS

## 8. Distance Vector

Current sub-task:

`E4S-P4-S1_DialogueSourceInventory_Readback -> COMPLETED`

Remaining P4 sub-tasks:

1. `E4S-P4-S2_SpeakingPromptContract_DesignScan`
2. `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`
3. `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`
4. `E4S-P4-S5_SamplePromptPackage_Implementation`
5. `E4S-P4-S6_PromptValidator_Implementation`
6. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 6 sub-tasks left`

## 9. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S2_SpeakingPromptContract_DesignScan`

Unique execution action:

Define the speaking prompt contract only. Do not implement prompt generator, role-play renderer, ASR, scoring, audio, UI, or learner-state integration.
