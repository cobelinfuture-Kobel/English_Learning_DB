# R7-M25 B2 Concrete Source-ref Verification Scan

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M25 B2 concrete source-ref verification scan

Branch:
codex/r7-m25-b2-source-ref

Status:
EVIDENCE_VERIFICATION_SCAN_ONLY
```

R7-M25 maps the 8 R7-M24 B2 planning proposals to concrete English Grammar Profile row references where possible. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

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

Allowed in R7-M25:

```text
- map R7-M24 proposals to concrete EGP source_ref candidates
- flag weak or indirect B2 surfaces
- keep implementation blocked until operator evidence review
```

Forbidden in R7-M25:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
```

## 4. Verification Table

| Proposed grammar_id | Source-ref candidates | Evidence level surface | Verification status |
|---|---|---|---|
| `GRAMMAR_MIXED_CONDITIONALS_B2` | `EGP_SOURCE_XLSX::Data!A249:H249::id=1741163708569x385656258064060800`; `EGP_SOURCE_XLSX::Data!A274:H274::id=1741163715625x825088087099632500` | B2 conditions / conditional conjunctions, but not an explicit mixed-conditional row | WEAK_OR_INDIRECT_MATCH_REVIEW_REQUIRED |
| `GRAMMAR_PASSIVE_REPORTING_STRUCTURES_B2` | `EGP_SOURCE_XLSX::Data!A813:H813::id=1741163712049x217545267830854720`; `EGP_SOURCE_XLSX::Data!A826:H826::id=1741163712052x291725965796862700`; `EGP_SOURCE_XLSX::Data!A832:H832::id=1741163712052x960121852033115700` | B2 passive infinitive / present perfect passive in reporting contexts | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_ADVANCED_MODAL_SPECULATION_B2` | `EGP_SOURCE_XLSX::Data!A711:H711::id=1741163716295x105998126908799500`; `EGP_SOURCE_XLSX::Data!A713:H713::id=1741163716295x333431392231873200`; `EGP_SOURCE_XLSX::Data!A715:H715::id=1741163716295x431001332463613700`; `EGP_SOURCE_XLSX::Data!A816:H816::id=1741163712049x547897454512315650` | B2 could have / past possibility / past speculation / modal perfect | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_RELATIVE_CLAUSES_PREPOSITION_WHOSE_B2` | `EGP_SOURCE_XLSX::Data!A234:H234::id=1741163708565x846306043223088400`; `EGP_SOURCE_XLSX::Data!A238:H238::id=1741163708566x933173646960638000`; `EGP_SOURCE_XLSX::Data!A239:H239::id=1741163708567x103888477209590050`; `EGP_SOURCE_XLSX::Data!A951:H951::id=1741163713116x878693855125900300` | B2 relative clauses with preposition / whose / formal preposition + relative pronoun | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_FUTURE_PERFECT_B2` | `EGP_SOURCE_XLSX::Data!A429:H429::id=1741163709242x337416434344128840`; `EGP_SOURCE_XLSX::Data!A430:H430::id=1741163709242x695590620556235600`; `EGP_SOURCE_XLSX::Data!A431:H431::id=1741163709452x228579889474654900` | B2 future perfect simple form and completed-future use | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_REPORTED_SPEECH_ADVANCED_B2` | `EGP_SOURCE_XLSX::Data!A1155:H1155::id=1741163715819x177565244544510180`; `EGP_SOURCE_XLSX::Data!A1156:H1156::id=1741163715819x186805151899247300`; `EGP_SOURCE_XLSX::Data!A1157:H1157::id=1741163715819x225500036872228400`; `EGP_SOURCE_XLSX::Data!A1158:H1158::id=1741163715820x279868282649035070`; `EGP_SOURCE_XLSX::Data!A1159:H1159::id=1741163715820x680259612514314400`; `EGP_SOURCE_XLSX::Data!A1160:H1160::id=1741163715820x722979507342767900` | B2 advanced reported speech forms and reporting-clause controls | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_PERFECT_CONTINUOUS_ADVANCED_CONTRAST_B2` | `EGP_SOURCE_XLSX::Data!A857:H857::id=1741163712328x422695616724010100`; `EGP_SOURCE_XLSX::Data!A859:H859::id=1741163712328x663782601864534800`; `EGP_SOURCE_XLSX::Data!A861:H861::id=1741163712328x669982657855112700`; `EGP_SOURCE_XLSX::Data!A863:H863::id=1741163712332x322280679825253100`; `EGP_SOURCE_XLSX::Data!A867:H867::id=1741163712332x793082629536507400`; `EGP_SOURCE_XLSX::Data!A915:H915::id=1741163712747x163928397652527870`; `EGP_SOURCE_XLSX::Data!A920:H920::id=1741163712747x885210955530291000` | B2 past perfect continuous and present perfect continuous advanced forms / uses | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |
| `GRAMMAR_INVERSION_NEGATIVE_ADVERBIALS_B2` | `EGP_SOURCE_XLSX::Data!A141:H141::id=1741163708146x347057405549150660`; `EGP_SOURCE_XLSX::Data!A874:H874::id=1741163712334x353325929078093700`; `EGP_SOURCE_XLSX::Data!A876:H876::id=1741163712334x897130264998052400`; `EGP_SOURCE_XLSX::Data!A984:H984::id=1741163713636x160593634066971800` | B2 inversion with never / no sooner / not only patterns | CANDIDATE_MATCH_REQUIRES_OPERATOR_REVIEW |

## 5. Verification Summary

```text
proposal_count = 8
source_ref_candidate_found = 8
clear_b2_candidate = 7
weak_or_indirect_match = 1
implementation_ready_rows = 0
```

Seven proposals have plausible B2 evidence. One proposal needs special review:

```text
GRAMMAR_MIXED_CONDITIONALS_B2
```

Reason:

```text
The available B2 rows support conditions and conditional conjunctions, but this scan did not find an explicit mixed-conditional row. The proposal may need to be narrowed to B2 conditional conjunctions or deferred.
```

## 6. Implementation Decision

```text
R7-M25_IMPLEMENTATION_DECISION = NOT_READY_OPERATOR_EVIDENCE_REVIEW_REQUIRED
```

Reason:

```text
Concrete source_ref candidates exist for all 8 proposals, but final evidence selection and stage-role interpretation require operator review before candidate-node implementation can be approved.
```

## 7. Gate & Distance Update

```text
[PASS] R7-M25 remains evidence-verification only.
[PASS] 8 B2 proposal groups checked against EGP.
[PASS] 8 proposals have concrete source_ref candidates.
[PASS] One weak/indirect proposal is explicitly flagged.
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
R7-M26 B2 source evidence operator review packet
```

R7-M26 may organize these candidate matches into an approval packet, but implementation must not start until the operator confirms which source_ref candidates are accepted, narrowed, or deferred.
