# E4S-P4-S6 Prompt Validator Implementation

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S6_PromptValidator_Implementation`

Status: `COMPLETED`

## 2. Implementation Scope

This task implements validator checks for the E4S P4 S5 sample prompt/package artifact.

Validation basis:

- `E4S-P4-S2_SpeakingPromptContract_DesignScan`
- `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`
- `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`
- `E4S-P4-S5_SamplePromptPackage_Implementation`

This task does not implement:

- full prompt generator
- role-play renderer
- ASR
- recording
- speech scoring
- audio pipeline
- student-facing UI
- learner-state integration
- final Dialogue Authority promotion

## 3. Files Created

### Validator code

```text
ulga/validators/validate_e4s_p4_prompt_package_v1.py
```

Commit:

```text
abed349952c2a721db37fffb2469c5004cf98788
```

## 4. Validator Entry Point

Default command from repository root:

```bash
python ulga/validators/validate_e4s_p4_prompt_package_v1.py --print-report
```

Default input:

```text
ulga/samples/e4s_p4_s5_sample_prompt_package_v1.json
```

Default report output:

```text
ulga/reports/e4s_p4_s6_sample_prompt_package_validation_report.json
```

Exit code behavior:

```text
0 = PASS, no blocking errors
1 = FAIL, one or more blocking errors
```

## 5. Validator Coverage

The validator checks these contract areas:

| Area | Coverage |
|---|---|
| Artifact root | artifact type, status, global scope constraints |
| Global capability boundary | prompt_only true; generator/validator/renderer/ASR/scoring/audio/UI/learner-state/final-authority claims false |
| Source family policy | AUX-S4, AUX-S5, AUX-S7 policy entries present |
| P4-S2 prompt record contract | required fields, allowed source families, prompt types, speaking modes, statuses, source trace, expected response shape |
| P4-S3 package contract | required fields, scenario/roles/turn sequence/prompt refs/package flow/constraints |
| P4-S4 candidate boundary | required boundary fields, applies_to linkage, source family consistency, origin/derivation/source-grounding/promotion states |
| AUX-S4 guard | blocks original-dialogue misuse and unsupported role-play turn use |
| AUX-S5 guard | checks role/context preservation indicators and prompt role presence |
| AUX-S7 guard | requires generated trace, candidate_only, pending review, promotion_blocked, no source-grounded package claim |
| Package prompt refs | checks prompt refs point to existing prompt records and learner-output prompt exists |
| Turn sequence | checks continuous turn indices and speaker_role_id consistency |
| Readback summary | checks prompt/package counts and forbidden claim counters |

## 6. Blocking Error Policy

The validator emits blocking errors for conditions such as:

- missing prompt/package required fields
- invalid source family
- unsupported prompt type / speaking mode / package type / practice mode
- missing source trace
- missing source evidence
- missing candidate boundary
- candidate boundary applies_to mismatch
- AUX-S7 not marked generated
- AUX-S7 not `candidate_only`
- AUX-S7 promotion not blocked
- package requiring recording / ASR / scoring / audio / UI renderer
- learner-output turn missing prompt ref
- prompt ref not found
- role-play package with fewer than two roles
- package turn speaker role not declared
- forbidden claim counters nonzero

## 7. Warning Policy

The validator emits warnings for non-blocking quality issues such as:

- A1 prompt max word count may be high
- AUX-S5 prompt has no speaker roles even though source may contain roles
- package turn count may be high for A1
- missing readback summary

Warnings do not change exit code.

## 8. Report Shape

The validator writes a JSON report with:

```json
{
  "validator_id": "E4S_P4_S6_PROMPT_VALIDATOR_V1",
  "task_id": "E4S-P4-S6_PromptValidator_Implementation",
  "target_artifact_id": "E4S_P4_S5_SAMPLE_PROMPT_PACKAGE_V1",
  "result": "PASS",
  "blocking_error_count": 0,
  "warning_count": 0,
  "blocking_errors": [],
  "warnings": [],
  "coverage": {
    "prompt_records_seen": 3,
    "packages_seen": 3,
    "checks": []
  }
}
```

The actual report is generated when the validator is run locally or in CI.

## 9. Manual Implementation Readback

Static implementation readback:

| Check | Status |
|---|---|
| Validator file created | PASS |
| Standalone Python CLI | PASS |
| Uses only Python standard library | PASS |
| Reads S5 sample artifact by default | PASS |
| Writes JSON report by default | PASS |
| Exit code 0/1 behavior implemented | PASS |
| P4-S2 prompt checks implemented | PASS |
| P4-S3 package checks implemented | PASS |
| P4-S4 boundary checks implemented | PASS |
| AUX-S7 generated/candidate-only guard implemented | PASS |
| No generator implemented | PASS |
| No renderer implemented | PASS |
| No ASR/audio/scoring implemented | PASS |
| No UI implemented | PASS |
| No learner-state integration implemented | PASS |
| No final authority promotion implemented | PASS |

## 10. Gate Metrics

- Prompt validator code created: PASS
- P4-S2 prompt record checks implemented: PASS
- P4-S3 package checks implemented: PASS
- P4-S4 candidate boundary checks implemented: PASS
- S5 sample artifact default path wired: PASS
- JSON report output wired: PASS
- Blocking/warning model implemented: PASS
- CLI exit-code behavior implemented: PASS
- Prompt-only V1 boundary preserved: PASS
- No generator code written: PASS
- No renderer implemented: PASS
- No runtime service modified: PASS
- No UI implemented: PASS
- No ASR/scoring/audio implemented: PASS

## 11. Distance Vector

Current sub-task:

`E4S-P4-S6_PromptValidator_Implementation -> COMPLETED`

Remaining P4 sub-tasks:

1. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 1 sub-task left`

## 12. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S7_ReadbackQA`

Unique execution action:

Run or read back the S6 validator against the S5 sample artifact, inspect the generated report, and close Phase 4 only if the sample artifact passes without blocking errors. Do not implement generator, renderer, ASR, audio, speech scoring, UI, learner-state integration, or final authority promotion.
