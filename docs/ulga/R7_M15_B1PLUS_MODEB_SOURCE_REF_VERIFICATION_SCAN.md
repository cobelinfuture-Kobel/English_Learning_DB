# R7-M15 B1_PLUS Mode-B Concrete Source-ref Verification Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M15 B1_PLUS Mode-B concrete source-ref verification scan

Branch:
codex/r7-m15-b1p-source-ref

Status:
EVIDENCE_VERIFICATION_SCAN_ONLY
```

R7-M15 maps the 8 R7-M14 Mode-B B1_PLUS planning rows to concrete English Grammar Profile source references where possible. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Source Used

```text
source_id = EGP_SOURCE_XLSX
source_file = English Grammar Profile Online.xlsx
source_sheet = Data
sheet_range = Data!A1:H1223
source_role = authority_source
```

Concrete `source_ref` format:

```text
EGP_SOURCE_XLSX::Data!A<row>:H<row>::id=<EGP id>
```

## 3. Verification Table

| Proposed grammar_id | Candidate source_ref | EGP level | Verification status | Mode-B fit |
|---|---|---:|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_B1PLUS` | `EGP_SOURCE_XLSX::Data!A1146:H1146::id=1741163715817x584156896390892800`; `EGP_SOURCE_XLSX::Data!A1148:H1148::id=1741163715817x804980721338935900` | B1 | VERIFIED_SOURCE_REF_SET | BRIDGE_FIT_B1_EXTENSION |
| `GRAMMAR_REPORTED_COMMANDS_REQUESTS_B1PLUS` | `EGP_SOURCE_XLSX::Data!A1151:H1151::id=1741163715818x861894992671141900`; `EGP_SOURCE_XLSX::Data!A1160:H1160::id=1741163715820x737887905214861700` | B1 / B2 | CANDIDATE_SOURCE_REF_SET_REVIEW_REQUIRED | BRIDGE_FIT_REQUIRES_REVIEW |
| `GRAMMAR_CONDITIONAL_MIXED_CONTROL_B1PLUS` | `EGP_SOURCE_XLSX::Data!A273:H273::id=1741163715625x776180432248680300`; `EGP_SOURCE_XLSX::Data!A276:H276::id=1741163715813x104521611350361970` | C1 / C2 | SOURCE_REF_TOO_HIGH_FOR_B1PLUS_DIRECT_IMPLEMENTATION | DEFER_OR_REPLACE |
| `GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS` | `EGP_SOURCE_XLSX::Data!A266:H266::id=1741163715624x362174287337988740` | B1 | VERIFIED_SOURCE_REF | BRIDGE_FIT_PREVIEW_OK |
| `GRAMMAR_PASSIVE_AGENT_BY_PHRASE_B1PLUS` | `EGP_SOURCE_XLSX::Data!A805:H805::id=1741163712047x184306606922612260`; `EGP_SOURCE_XLSX::Data!A808:H808::id=1741163712047x673355343552202160` | B1 / A2 | CANDIDATE_SOURCE_REF_SET_REVIEW_REQUIRED | BRIDGE_FIT_WITH_A2_BACKFILL_CAUTION |
| `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | `EGP_SOURCE_XLSX::Data!A223:H223::id=1741163708563x609059917595893100`; `EGP_SOURCE_XLSX::Data!A225:H225::id=1741163708563x842654366263886400`; `EGP_SOURCE_XLSX::Data!A228:H228::id=1741163708564x509910132136988540` | A2 | SOURCE_REF_STAGE_DRIFT_A2 | DEFER_OR_REPLACE |
| `GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS` | `EGP_SOURCE_XLSX::Data!A552:H552::id=TBD_FROM_EGP_ROW`; `EGP_SOURCE_XLSX::Data!A591:H591::id=1741163710846x395037418398339200`; `EGP_SOURCE_XLSX::Data!A595:H595::id=1741163711029x414511959030775550` | B2 | PARTIAL_SOURCE_REF_VERIFIED_ROW_ID_TBD | BRIDGE_FIT_REQUIRES_ROW_ID_RECHECK |
| `GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS` | `EGP_SOURCE_XLSX::Data!A910:H910::id=1741163712744x249654248066045100`; `EGP_SOURCE_XLSX::Data!A911:H911::id=1741163712744x517808240803915500`; `EGP_SOURCE_XLSX::Data!A919:H919::id=1741163712747x851758421234194700`; `EGP_SOURCE_XLSX::Data!A930:H930::id=1741163713101x869805445646449900`; `EGP_SOURCE_XLSX::Data!A935:H935::id=1741163713111x811420585366934300` | B1 | VERIFIED_SOURCE_REF_SET | BRIDGE_FIT_B1_EXTENSION |

## 4. Verification Summary

```text
proposal_count = 8
verified_or_candidate_source_ref_rows = 8
clean_bridge_fit = 3
review_required = 3
defer_or_replace = 2
implementation_ready_rows = 0
```

Clean bridge-fit rows:

```text
- GRAMMAR_REPORTED_QUESTIONS_B1PLUS
- GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS
- GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS
```

Review-required rows:

```text
- GRAMMAR_REPORTED_COMMANDS_REQUESTS_B1PLUS
- GRAMMAR_PASSIVE_AGENT_BY_PHRASE_B1PLUS
- GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS
```

Defer-or-replace rows:

```text
- GRAMMAR_CONDITIONAL_MIXED_CONTROL_B1PLUS
- GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS
```

## 5. Implementation Decision

```text
R7-M15_IMPLEMENTATION_DECISION = NOT_READY_REVIEW_AND_REPLACEMENT_REQUIRED
```

Reason:

```text
Concrete or candidate source_ref values were found, but only 3 of 8 rows are clean Mode-B bridge fits. Three require source-row review. Two should be deferred or replaced because the evidence is either too high for direct B1_PLUS implementation or stage-drifted down to A2.
```

## 6. Required Next Action

```text
NEXT_SHORT_STEP:
R7-M16 B1_PLUS Mode-B source-ref review and replacement proposal
```

R7-M16 must remain proposal-only. It should keep the clean 3 rows, review or replace the 3 review-required rows, and replace/defer the 2 unsuitable rows. It must not modify `grammar_nodes.json` or `grammar_edges.json`.

## 7. Gate & Distance Update

```text
[PASS] R7-M15 remains evidence-verification only.
[PASS] 8 B1_PLUS candidate rows checked against EGP.
[PASS] Clean bridge-fit rows identified.
[PASS] Review-required rows identified.
[PASS] Defer-or-replace rows identified.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] B1_PLUS implementation remains not ready.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```
