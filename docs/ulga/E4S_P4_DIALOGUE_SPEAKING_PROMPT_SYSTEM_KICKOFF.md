# E4S-P4 Dialogue / Speaking Prompt System Kickoff

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S0_DialogueSpeakingPromptSystem_KickoffPreflight`

Status: `KICKOFF_RECORDED`

## 2. Authorized Connectors

- GitHub: authorized for project read and API write.
- Google Drive: authorized for reference/spec/dataset read.

## 3. Data Sources

Primary source alignment:

- `重點任務排程.txt` — cloud-agent handshake protocol.
- `RAZ-AW-V1 Status Snapshot.txt` — E4S roadmap and Phase 4 definition.

## 4. Phase 4 Scope

Phase 4 is defined as Dialogue / Speaking Prompt System.

Goal:

- Convert parent functional sentences, story dialogue corpus, and generated dialogue candidates into speaking prompts, role-play prompts, and oral-response prompts.

Source families:

- `AUX-S4 Parent Functional Sentence Corpus`
- `AUX-S5 Story Dialogue Corpus`
- `AUX-S7 Generated Dialogue Candidates`

V1 boundary:

- Prompt only.
- No recording.
- No ASR.
- No speaking score.
- No student-facing app implementation.

## 5. Anti-Scope-Creep Lock

This kickoff only records Phase 4 activation and boundary.

It does not implement:

- dialogue generator
- role-play renderer
- ASR
- audio pipeline
- scoring engine
- UI
- learner-state integration

## 6. Gate Metrics

- GitHub write target defined: PASS
- Phase 4 source families identified: PASS
- Prompt-only boundary recorded: PASS
- Runtime/code/schema modification avoided: PASS
- Google Drive content mutation avoided: PASS

## 7. Distance Vector

Current phase: `E4S-P4_DialogueSpeakingPromptSystem`

Current sub-task: `E4S-P4-S0_DialogueSpeakingPromptSystem_KickoffPreflight -> COMPLETED`

Estimated P4 remaining sub-tasks:

1. `E4S-P4-S1_DialogueSourceInventory_Readback`
2. `E4S-P4-S2_SpeakingPromptContract_DesignScan`
3. `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`
4. `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`
5. `E4S-P4-S5_SamplePromptPackage_Implementation`
6. `E4S-P4-S6_PromptValidator_Implementation`
7. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 7 sub-tasks left`

## 8. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S1_DialogueSourceInventory_Readback`

Unique execution action:

Read the approved source inventory / Drive references for AUX-S4, AUX-S5, and AUX-S7, then produce a Phase 4 source-readback table. Do not write generator code yet.
