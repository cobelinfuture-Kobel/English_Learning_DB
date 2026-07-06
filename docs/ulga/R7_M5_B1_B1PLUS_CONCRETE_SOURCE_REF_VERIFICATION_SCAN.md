# R7-M5 B1 / B1_PLUS Concrete Source-ref Verification Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M5 B1 / B1_PLUS concrete source-ref verification scan

Branch:
codex/r7-m5-b1-b1plus-source-ref-verification

Status:
EVIDENCE_VERIFICATION_SCAN_ONLY
```

R7-M5 maps the 10 R7-M4 proposal-level attachment rows to concrete English Grammar Profile row references where possible. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Source Used

```text
source_id = EGP_SOURCE_XLSX
source_file = English Grammar Profile Online.xlsx
source_sheet = Data
sheet_range = Data!A1:H1223
source_role = authority_source
```

Concrete `source_ref` format used in this scan:

```text
EGP_SOURCE_XLSX::Data!A<row>:H<row>::id=<EGP id>
```

## 3. Scope Lock

Allowed in R7-M5:

```text
- map R7-M4 rows to concrete EGP source_ref values where possible
- mark stage match / stage drift
- keep implementation blocked when evidence conflicts with R7-M1 tentative stage
- produce a resumable next task
```

Forbidden in R7-M5:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Current Baseline To Protect

Current static grammar artifact baseline remains unchanged:

```text
status = PASS
node_count = 22
edge_count = 22
order_row_count = 22
coverage_node_count = 22
query_node_count = 22
check_count = 22
fail_count = 0
```

Current authority split remains unchanged:

```text
accepted = 5
candidate = 17
```

## 5. Concrete Source-ref Verification Table

| Proposed grammar_id | R7-M4 tentative stage | EGP row | EGP level | EGP category | EGP guideword | Concrete source_ref | Verification status | Stage alignment |
|---|---:|---:|---:|---|---|---|---|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | B1 | 929 | A2 | PAST / present perfect simple | USE: EXPERIENCES | `EGP_SOURCE_XLSX::Data!A929:H929::id=1741163707347x717687839549253600` | VERIFIED_SOURCE_REF | STAGE_DRIFT_A2_NOT_B1 |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | 930 | B1 | PAST / present perfect simple | USE: RECENT PAST | `EGP_SOURCE_XLSX::Data!A930:H930::id=1741163707348x283773651657878500` | VERIFIED_SOURCE_REF | MATCH |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | B1 | 845 | A2 | PAST / past continuous | FORM: AFFIRMATIVE | `EGP_SOURCE_XLSX::Data!A845:H845::id=1741163707224x376142321385242600` | VERIFIED_SOURCE_REF | STAGE_DRIFT_A2_NOT_B1 |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | 261 | B1 | CLAUSES / conditional | FORM/USE: PRESENT SIMPLE 'IF' CLAUSE + 'WILL', FUTURE, LIKELY OUTCOME (FIRST CONDITIONAL) | `EGP_SOURCE_XLSX::Data!A261:H261::id=1741163706509x541990521561546800` | VERIFIED_SOURCE_REF | MATCH |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | B1 | 219 | A2 | CLAUSES / relative | FORM: DEFINING, SUBJECT, WITH 'WHO' | `EGP_SOURCE_XLSX::Data!A219:H219::id=1741163706470x775143135101681700` | VERIFIED_SOURCE_REF | STAGE_DRIFT_A2_NOT_B1 |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | B1 | 806 / 807 | A2 | PASSIVES / passives: form | FORM: PAST SIMPLE, AFFIRMATIVE / FORM: PRESENT SIMPLE, AFFIRMATIVE | `EGP_SOURCE_XLSX::Data!A806:H806::id=1741163707172x707824579788800600`; `EGP_SOURCE_XLSX::Data!A807:H807::id=1741163707173x530388082789859300` | VERIFIED_SOURCE_REF_PAIR | STAGE_DRIFT_A2_NOT_B1 |
| `GRAMMAR_REPORTED_SPEECH_BASIC` | B1_PLUS | 1149 | B1 | REPORTED SPEECH / reported speech | FORM: REPORTED STATEMENTS, PRONOUN AND TENSE SHIFT | `EGP_SOURCE_XLSX::Data!A1149:H1149::id=1741163707434x421891971227342700` | VERIFIED_SOURCE_REF | STAGE_DRIFT_B1_NOT_B1_PLUS |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1_PLUS | 265 | B1 | CLAUSES / conditional | FORM/USE: 'IF' + PAST SIMPLE + 'WOULD', FUTURE, IMAGINED SITUATION (SECOND CONDITIONAL) | `EGP_SOURCE_XLSX::Data!A265:H265::id=1741163706511x332297971369229300` | VERIFIED_SOURCE_REF | STAGE_DRIFT_B1_NOT_B1_PLUS |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1_PLUS | 590 | B1 | MODALITY / must | USE: DEDUCTIONS AND CONCLUSIONS | `EGP_SOURCE_XLSX::Data!A590:H590::id=1741163707013x161563029785805400` | VERIFIED_SOURCE_REF | STAGE_DRIFT_B1_NOT_B1_PLUS |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1_PLUS | 910 / 911 / 919 | B1 | PAST / present perfect continuous | USE: REPEATED CONTINUING EVENTS / FORM: AFFIRMATIVE / USE: SINGLE CONTINUING EVENT | `EGP_SOURCE_XLSX::Data!A910:H910::id=1741163707338x941026208994934800`; `EGP_SOURCE_XLSX::Data!A911:H911::id=1741163707339x692876332257666700`; `EGP_SOURCE_XLSX::Data!A919:H919::id=1741163707341x355627788613507700` | VERIFIED_SOURCE_REF_SET | STAGE_DRIFT_B1_NOT_B1_PLUS |

## 6. Verification Summary

```text
proposal_count = 10
concrete_source_ref_found = 10
exact_stage_match = 2
stage_drift = 8
implementation_ready_rows = 0
```

The scan found concrete EGP row references for all 10 proposals. However, only 2 rows match the R7-M1 tentative stage exactly:

```text
MATCH:
- GRAMMAR_PRESENT_PERFECT_RESULT_BASIC
- GRAMMAR_FIRST_CONDITIONAL_BASIC
```

The remaining 8 proposals have authority evidence, but their EGP levels do not match the R7-M1 tentative stage. This is not a source failure; it is a stage-alignment issue.

## 7. Implementation Decision

```text
R7-M5_IMPLEMENTATION_DECISION = NOT_READY_STAGE_ALIGNMENT_REQUIRED
```

Reason:

```text
Concrete source_ref values are available for all 10 proposals, but 8 of 10 proposals show stage drift against the R7-M1 tentative stage. Candidate node implementation must remain blocked until a stage-alignment correction proposal is completed.
```

## 8. Required Next Action Before Implementation

A later task must decide how to handle the 8 stage-drift proposals. Allowed correction modes:

```text
MODE-A: adjust tentative stage to match EGP evidence
MODE-B: keep R7-M1 stage but attach a narrower B1/B1_PLUS supporting EGP row
MODE-C: split proposal into basic and expanded variants
MODE-D: defer proposal from implementation batch
```

No correction may directly promote a record to accepted authority.

## 9. Future Candidate Node Batch Boundary

Implementation remains blocked until stage alignment is resolved.

Allowed after stage alignment:

```text
- candidate-only node batch
- authority_status = candidate
- source_ref must remain concrete and non-empty
- confidence = operator_review_required unless normalized evidence is reviewed
- traceability.generated_content=false
- traceability.learner_state_write=false
```

Still forbidden:

```text
- accepted authority promotion
- learner-facing practice generation
- learner state write
- B2 implementation
- edge implementation before candidate nodes exist
```

## 10. Gate & Distance Update

```text
[PASS] R7-M5 remains evidence-verification only.
[PASS] 10 proposal rows checked against EGP.
[PASS] 10 concrete source_ref values found.
[PASS] Stage drift is explicitly recorded.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] Candidate node implementation remains not ready because stage alignment is unresolved.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 11. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M6 B1 / B1_PLUS stage-alignment correction proposal
```

R7-M6 must remain proposal-only. It should decide how to handle the 8 stage-drift records before any candidate node implementation is allowed. It must not modify `grammar_nodes.json` or `grammar_edges.json`.
