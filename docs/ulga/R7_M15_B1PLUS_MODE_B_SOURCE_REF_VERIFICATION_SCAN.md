# R7-M15 B1_PLUS Mode-B Concrete Source-ref Verification Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M15 B1_PLUS Mode-B concrete source-ref verification scan

Branch:
codex/r7-m15-b1plus-source-ref-scan

Status:
EVIDENCE_VERIFICATION_SCAN_ONLY
```

R7-M15 maps the 8 R7-M14 Mode-B B1_PLUS planning proposals to concrete English Grammar Profile row references where possible. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

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

Allowed in R7-M15:

```text
- map R7-M14 proposals to concrete EGP source_ref candidates
- mark whether rows support advanced B1 control, B2 preview form, B2 preview use, or clause complexity extension
- keep implementation blocked until operator evidence review
```

Forbidden in R7-M15:

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

## 4. Verification Table

| Proposed grammar_id | Bridge role | Source-ref candidates | Evidence level surface | Verification status |
|---|---|---|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_REQUESTS_B1PLUS` | clause complexity extension | `EGP_SOURCE_XLSX::Data!A1151:H1151::id=1741163715818x484532724787778900`; `EGP_SOURCE_XLSX::Data!A882:H882::id=1741163712335x814539814649439100`; `EGP_SOURCE_XLSX::Data!A1160:H1160::id=1741163715820x722979507342767900` | B1 request/command + B2 reported question/request extension | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_MODAL_DEDUCTION_PAST_B1PLUS` | B2 preview use | `EGP_SOURCE_XLSX::Data!A570:H570::id=1741163710842x255780476758331600`; `EGP_SOURCE_XLSX::Data!A571:H571::id=1741163710842x294632080213531140`; `EGP_SOURCE_XLSX::Data!A715:H715::id=1741163716295x431001332463613700` | B1 `might have` + B2 `could have` speculation | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_PASSIVE_WITH_MODALS_B1PLUS` | B2 preview form | `EGP_SOURCE_XLSX::Data!A812:H812::id=1741163712049x217545267830854720`; `EGP_SOURCE_XLSX::Data!A830:H830::id=1741163712052x892253245373132200`; `EGP_SOURCE_XLSX::Data!A816:H816::id=1741163712049x547897454512315650` | B2 modal/passive extension | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | B2 preview form | `EGP_SOURCE_XLSX::Data!A232:H232::id=1741163708565x566817072036876350`; `EGP_SOURCE_XLSX::Data!A234:H234::id=1741163708565x846306043223088400`; `EGP_SOURCE_XLSX::Data!A238:H238::id=1741163708566x933173646960638000` | B1 non-defining object + B2 preposition/whose extension | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_CONDITIONALS_UNLESS_AS_LONG_AS_B1PLUS` | advanced B1 control | `EGP_SOURCE_XLSX::Data!A269:H269::id=1741163715624x965900869689892700`; `EGP_SOURCE_XLSX::Data!A274:H274::id=1741163715625x825088087099632500` | B1 `unless` + B2 wider conditional conjunctions | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS` | clause complexity extension | `EGP_SOURCE_XLSX::Data!A265:H265::id=1741163715621x282870273772287460`; `EGP_SOURCE_XLSX::Data!A266:H266::id=1741163715624x362174287337988740`; `EGP_SOURCE_XLSX::Data!A268:H268::id=1741163715624x888960790421745800` | B1 second/third/if-I-were-you conditional surface | STAGE_SURFACE_WEAK_FOR_B1PLUS_REVIEW_REQUIRED |
| `GRAMMAR_PRESENT_PERFECT_SIMPLE_CONTINUOUS_CONTRAST_B1PLUS` | advanced B1 control | `EGP_SOURCE_XLSX::Data!A910:H910::id=1741163712744x249654248066045100`; `EGP_SOURCE_XLSX::Data!A911:H911::id=1741163712744x517808240803915500`; `EGP_SOURCE_XLSX::Data!A915:H915::id=1741163712747x163928397652527870`; `EGP_SOURCE_XLSX::Data!A920:H920::id=1741163712747x885210955530291000` | B1 core present perfect continuous + B2 form extension | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_FUTURE_CONTINUOUS_PREVIEW_B1PLUS` | B2 preview form | `EGP_SOURCE_XLSX::Data!A408:H408::id=1741163709234x555675180554027650`; `EGP_SOURCE_XLSX::Data!A411:H411::id=1741163709235x267104607541658750`; `EGP_SOURCE_XLSX::Data!A413:H413::id=1741163709235x737206541062207200` | B1 future continuous core + B2 polite/question preview | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |

## 5. Verification Summary

```text
proposal_count = 8
source_ref_candidate_found = 8
clear_mode_b_bridge_candidate = 7
weak_stage_surface = 1
implementation_ready_rows = 0
```

Seven proposals have plausible Mode-B bridge evidence. One proposal needs special review:

```text
GRAMMAR_SECOND_CONDITIONAL_EXPANDED_B1PLUS
```

Reason:

```text
The available source rows are mostly B1 conditional expansions. They may support advanced B1 control, but they may not be distinct enough for a separate B1_PLUS node without a narrower B2-preview anchor.
```

## 6. Implementation Decision

```text
R7-M15_IMPLEMENTATION_DECISION = NOT_READY_OPERATOR_EVIDENCE_REVIEW_REQUIRED
```

Reason:

```text
Concrete source_ref candidates exist for all 8 proposals, but final evidence selection and stage-role interpretation require operator review before candidate-node implementation can be approved.
```

## 7. Gate & Distance Update

```text
[PASS] R7-M15 remains evidence-verification only.
[PASS] 8 proposal rows checked against EGP.
[PASS] 8 proposals have concrete source_ref candidates.
[PASS] One weak-stage proposal is explicitly flagged.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[BLOCKED] Candidate implementation remains not ready because operator evidence review is required.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 8. Stop / Resume Handoff

```text
STOP_REASON:
HUMAN_EVIDENCE_REVIEW_REQUIRED

NEXT_RESUME_TASK:
R7-M16 B1_PLUS Mode-B source evidence operator review packet
```

R7-M16 may organize these candidate matches into an approval packet, but implementation must not start until the operator confirms which source_ref candidates are accepted, narrowed, or deferred.
