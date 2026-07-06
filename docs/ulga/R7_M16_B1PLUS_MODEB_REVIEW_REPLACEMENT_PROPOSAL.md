# R7-M16 B1_PLUS Mode-B Source-ref Review and Replacement Proposal

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M16 B1_PLUS Mode-B source-ref review and replacement proposal

Branch:
codex/r7-m16-b1p-review

Status:
PROPOSAL_ONLY
```

R7-M16 resolves the R7-M15 evidence scan at proposal level. It keeps clean Mode-B bridge rows, replaces unsuitable rows, and preserves implementation blocking until a later readiness checklist.

## 2. Prior Gate From R7-M15

```text
proposal_count = 8
clean_bridge_fit = 3
review_required = 3
defer_or_replace = 2
implementation_ready_rows = 0
R7-M15_IMPLEMENTATION_DECISION = NOT_READY_REVIEW_AND_REPLACEMENT_REQUIRED
```

## 3. Scope Lock

Allowed in R7-M16:

```text
- decide which B1_PLUS planning rows to keep
- replace or defer unsuitable rows
- define corrected B1_PLUS candidate surface
- keep all records planning-only
```

Forbidden in R7-M16:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Review Decisions

| R7-M15 row | Decision | Reason |
|---|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_B1PLUS` | KEEP | B1 reported question rows provide clean bridge extension from B1 reported statements. |
| `GRAMMAR_REPORTED_COMMANDS_REQUESTS_B1PLUS` | KEEP_WITH_REVIEW | B1 positive requests/commands row is usable; B2 negative form remains preview-only evidence, not mastery. |
| `GRAMMAR_CONDITIONAL_MIXED_CONTROL_B1PLUS` | REPLACE | Original evidence was C1/C2 and too high for direct B1_PLUS. |
| `GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS` | KEEP | B1 third conditional row can serve as controlled preview under Mode-B. |
| `GRAMMAR_PASSIVE_AGENT_BY_PHRASE_B1PLUS` | REPLACE_WITH_NARROWER | A2 by-phrase and B1 relative-passive evidence are mixed; replace with narrower B1 passive relative/by-clause bridge. |
| `GRAMMAR_RELATIVE_CLAUSES_NONDEFINING_PREVIEW_B1PLUS` | REPLACE | Earlier non-defining evidence was mostly A2; use B1 object/whose or B2 preposition-stranding bridge instead. |
| `GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS` | REPLACE_WITH_NARROWER | A2 may-possibility is too low; B2 must-question/emphasis is too narrow. Replace with B1/B2 modal possibility/certainty contrast scan target. |
| `GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS` | KEEP | B1 present-perfect and present-perfect-continuous rows support bridge-level contrast. |

## 5. Corrected B1_PLUS Candidate Surface

R7-M16 proposes the following corrected 8-row B1_PLUS surface for the next readiness checklist.

| Corrected grammar_id | Evidence refs | Stage policy status | Implementation proposal status |
|---|---|---|---|
| `GRAMMAR_REPORTED_QUESTIONS_B1PLUS` | `EGP_SOURCE_XLSX::Data!A1146:H1146::id=1741163715817x584156896390892800`; `EGP_SOURCE_XLSX::Data!A1148:H1148::id=1741163715817x804980721338935900` | MODE_B_BRIDGE | READY_FOR_READINESS_CHECK |
| `GRAMMAR_REPORTED_REQUESTS_COMMANDS_B1PLUS` | `EGP_SOURCE_XLSX::Data!A1151:H1151::id=1741163715818x484532724787778900`; optional preview `EGP_SOURCE_XLSX::Data!A1160:H1160::id=1741163715820x722979507342767900` | MODE_B_BRIDGE_WITH_PREVIEW | READY_FOR_READINESS_CHECK |
| `GRAMMAR_CONDITIONAL_VARIATION_B1PLUS` | `EGP_SOURCE_XLSX::Data!A258:H258::id=1741163715620x161645047931569860`; `EGP_SOURCE_XLSX::Data!A264:H264::id=1741163715620x712487586393501200`; `EGP_SOURCE_XLSX::Data!A267:H267::id=1741163715624x704023316934564200` | MODE_B_BRIDGE | READY_FOR_READINESS_CHECK |
| `GRAMMAR_THIRD_CONDITIONAL_PREVIEW_B1PLUS` | `EGP_SOURCE_XLSX::Data!A266:H266::id=1741163715624x362174287337988740` | MODE_B_PREVIEW | READY_FOR_READINESS_CHECK |
| `GRAMMAR_PASSIVE_RELATIVE_BY_PHRASE_B1PLUS` | `EGP_SOURCE_XLSX::Data!A805:H805::id=1741163712047x184306606922612260` | MODE_B_BRIDGE | READY_FOR_READINESS_CHECK |
| `GRAMMAR_RELATIVE_CLAUSES_OBJECT_WHOSE_B1PLUS` | `EGP_SOURCE_XLSX::Data!A232:H232::id=1741163708565x566817072036876350`; `EGP_SOURCE_XLSX::Data!A237:H237::id=1741163708565x901437004568881900`; optional preview `EGP_SOURCE_XLSX::Data!A234:H234::id=1741163708565x846306043223088400` | MODE_B_BRIDGE_WITH_PREVIEW | READY_FOR_READINESS_CHECK |
| `GRAMMAR_MODAL_CERTAINTY_POSSIBILITY_B1PLUS` | `EGP_SOURCE_XLSX::Data!A590:H590::id=1741163710845x798749370290314700`; `EGP_SOURCE_XLSX::Data!A591:H591::id=1741163710846x395037418398339200`; `EGP_SOURCE_XLSX::Data!A595:H595::id=1741163711029x414511959030775550` | MODE_B_BRIDGE_WITH_PREVIEW | READY_FOR_READINESS_CHECK |
| `GRAMMAR_PERFECT_ASPECT_CONTRAST_B1PLUS` | `EGP_SOURCE_XLSX::Data!A910:H910::id=1741163712744x249654248066045100`; `EGP_SOURCE_XLSX::Data!A911:H911::id=1741163712744x517808240803915500`; `EGP_SOURCE_XLSX::Data!A919:H919::id=1741163712747x851758421234194700`; `EGP_SOURCE_XLSX::Data!A930:H930::id=1741163713101x869805445646449900`; `EGP_SOURCE_XLSX::Data!A935:H935::id=1741163713111x811420585366934300` | MODE_B_BRIDGE | READY_FOR_READINESS_CHECK |

## 6. Corrected Count

```text
corrected_b1plus_candidates = 8
ready_for_readiness_check = 8
implementation_ready = 0
```

This is not implementation approval. It only means the corrected surface is coherent enough for a later readiness checklist.

## 7. Required Guardrails For Later Implementation

A future implementation task, if approved, must:

```text
- keep authority_status = candidate
- keep confidence = operator_review_required
- set introduced_stage = B1_PLUS
- treat B2 evidence as preview support only
- avoid accepted authority promotion
- avoid learner-facing generation
- avoid learner state write
```

## 8. Gate & Distance Update

```text
[PASS] R7-M16 remains proposal-only.
[PASS] R7-M15 review rows are resolved at proposal level.
[PASS] Corrected B1_PLUS surface has 8 rows.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M17 B1_PLUS Mode-B implementation readiness checklist
```

R7-M17 must remain checklist-only. It should verify whether the corrected 8-row B1_PLUS surface is ready for an operator-approved candidate-node implementation batch. It must not modify `grammar_nodes.json` or `grammar_edges.json`.
