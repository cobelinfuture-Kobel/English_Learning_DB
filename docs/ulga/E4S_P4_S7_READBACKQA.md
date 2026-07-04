# E4S-P4-S7 ReadbackQA

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S7_ReadbackQA`

Status: `COMPLETED_STATIC_READBACK_EXECUTION_NOT_RUN`

Phase 4 closeout status: `NOT_CLOSED_BY_RUNTIME_QA`

## 2. QA Scope

This task reads back the E4S P4 sample artifact and validator implementation.

Readback basis:

- `docs/ulga/E4S_P4_S5_SAMPLE_PROMPT_PACKAGE_IMPLEMENTATION.md`
- `ulga/samples/e4s_p4_s5_sample_prompt_package_v1.json`
- `docs/ulga/E4S_P4_S6_PROMPT_VALIDATOR_IMPLEMENTATION.md`
- `ulga/validators/validate_e4s_p4_prompt_package_v1.py`

This task does not implement:

- generator
- renderer
- ASR
- recording
- speech scoring
- audio pipeline
- student-facing UI
- learner-state integration
- final Dialogue Authority promotion

## 3. Execution Mode

Execution mode:

```text
github_connector_static_readback
```

Validator execution status:

```text
NOT_RUN_IN_THIS_SESSION
```

Reason:

```text
This ChatGPT/GitHub connector session can read and write repository files but does not provide a local repository checkout or CI runner for executing the Python CLI. Therefore this S7 is a static readback QA, not a runtime execution report.
```

## 4. Files Created

### ReadbackQA report

```text
ulga/reports/e4s_p4_s7_readbackqa_report.json
```

Commit:

```text
ade9eeb74f46e9e6f5198c3df79b5045a7e834fd
```

### ReadbackQA document

```text
docs/ulga/E4S_P4_S7_READBACKQA.md
```

Commit:

```text
<current commit>
```

## 5. S5 Sample Artifact Readback

S5 readback states the sample artifact contains:

- 3 speaking prompt records
- 3 role-play prompt packages
- global prompt-only constraints
- AUX-S4 / AUX-S5 / AUX-S7 source-family policy
- candidate boundary objects on every prompt/package
- no ASR / scoring / audio / UI / learner-state claims

S5 sample records:

| prompt_id | source_family | prompt_type | speaking_mode | status |
|---|---|---|---|---|
| `SPK_AUXS4_SAMPLE_000001` | AUX-S4 | functional_response | guided_response | candidate_only |
| `SPK_AUXS5_SAMPLE_000001` | AUX-S5 | role_play_turn | role_play | candidate_only |
| `SPK_AUXS7_SAMPLE_000001` | AUX-S7 | oral_sentence_builder | sentence_building | candidate_only |

S5 sample packages:

| package_id | source_family | package_type | practice_mode | status |
|---|---|---|---|---|
| `RPP_AUXS5_SAMPLE_000001` | AUX-S5 | role_play_package | guided_role_play | candidate_only |
| `RPP_AUXS4_SAMPLE_000001` | AUX-S4 | substitution_role_play_package | parent_child_role_play | candidate_only |
| `RPP_AUXS7_SAMPLE_000001` | AUX-S7 | role_response_package | one_role_response | candidate_only |

## 6. S6 Validator Readback

S6 validator default command:

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

S6 validator covers:

- artifact root
- global capability boundary
- source family policy
- P4-S2 prompt record contract
- P4-S3 package contract
- P4-S4 candidate boundary
- AUX-S4 guard
- AUX-S5 guard
- AUX-S7 guard
- package prompt refs
- turn sequence
- readback summary

## 7. Static QA Result

Static readback result:

```text
PASS_STATIC_READBACK_EXECUTION_NOT_RUN
```

Blocking findings from static readback:

```text
[]
```

Warning:

```text
validator_not_executed
```

Meaning:

Static readback found no contract mismatch in the documented S5/S6 state, but S6 validator execution was not performed in this connector session.

## 8. Phase 4 Closeout Decision

Phase 4 closeout decision:

```text
NOT_CLOSED_BY_RUNTIME_QA
```

Reason:

P4-S6 defined that the next step should run or read back the validator and close Phase 4 only if the sample artifact passes without blocking errors. This S7 completed the readback side and found no static blocking issue, but it did not produce an actual validator runtime report.

Therefore Phase 4 should not be marked fully closed until one of the following exists:

1. local validator run output showing `result = PASS`, `blocking_error_count = 0`; or
2. CI validator run output showing `result = PASS`, `blocking_error_count = 0`.

## 9. Gate Metrics

- S5 sample artifact read back: PASS
- S6 validator implementation read back: PASS
- S6 validator command identified: PASS
- S6 validator input path identified: PASS
- S6 validator report path identified: PASS
- S6 validator exit-code behavior identified: PASS
- S6 coverage read back: PASS
- Static blocking findings: PASS_NONE_FOUND
- Validator runtime execution: NOT_RUN_IN_THIS_SESSION
- Phase 4 runtime closeout: NOT_CLOSED
- No generator code written: PASS
- No renderer implemented: PASS
- No runtime service modified: PASS
- No UI implemented: PASS
- No ASR/scoring/audio implemented: PASS
- No final authority promotion: PASS

## 10. Distance Vector

Current sub-task:

`E4S-P4-S7_ReadbackQA -> COMPLETED_STATIC_READBACK_EXECUTION_NOT_RUN`

Remaining P4 execution gate:

1. `E4S-P4-S7A_ValidatorRuntimeEvidence_LocalOrCI`

Total Distance: `D_p4_runtime_closeout = 1 evidence step left`

## 11. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S7A_ValidatorRuntimeEvidence_LocalOrCI`

Unique execution action:

Run this command from repository root in local checkout or CI:

```bash
python ulga/validators/validate_e4s_p4_prompt_package_v1.py --print-report
```

Then provide or commit the generated report:

```text
ulga/reports/e4s_p4_s6_sample_prompt_package_validation_report.json
```

Only if the report shows `result = PASS` and `blocking_error_count = 0`, mark Phase 4 as runtime-closeout PASS.
