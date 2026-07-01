# RAZ-AW-S3I Source Traceability Backfill Emitter Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S3I_SourceTraceabilityBackfillEmitter_DesignScan
```

Execution mode:

```text
DesignScan only
```

Predecessors:

```text
RAZ-AW-S3F_SourceTraceabilityAndPromotionGateContractPatch_DesignScan
RAZ-AW-S3G_SourceTraceabilityAndPromotionGateContractPatch_Implementation
RAZ-AW-S3G1_AuthorityLinkageContractValidator_LocalImplementation
```

Current status entering S3I:

```text
normalized validator: PASS
enriched validator: PASS
S3G1 authority-linkage validator: IMPLEMENTED_WITH_BLOCKED_LEGACY_GAPS
```

Control flags:

| Control | Status |
| --- | --- |
| implementation allowed | false |
| corpus mutation allowed | false |
| raw corpus modification allowed | false |
| derived corpus modification allowed | false |
| authority promotion allowed | false |
| runtime modification allowed | false |
| builder modification allowed | false |
| validator modification allowed | false |
| GitHub full-text corpus push allowed | false |

Risk level:

```text
Low
```

Reason:

```text
This task adds a design document only. It does not modify code, validators, schemas, runtime, raw corpus, derived corpus, or authority records.
```

Repository-safe conclusion:

```text
S3I is safe to commit because it designs an external authority-linkage view/emitter layer and does not contain RAZ text or full derived corpus content.
```

---

## 2. Files Inspected

| Path | Role | Inspection status | Quote safety | Full-text risk |
| --- | --- | --- | --- | --- |
| `docs/raz/RAZ_AW_S3F_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_DESIGN_SCAN.md` | source traceability and promotion gate contract design | directly inspected | safe_to_quote | no |
| `docs/raz/RAZ_AW_S3G_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_IMPLEMENTATION.md` | S3G1 implementation and local validator result | directly inspected | safe_to_quote | no |
| `reports/raz/raz_authority_linkage_contract_validation.json` | sanitized S3G1 validator report | directly inspected | summary_only | no text values |
| `schemas/raz/raz_authority_linkage_contract.schema.json` | supplemental S3G contract schema | assumed present from S3G | safe_to_quote | no |
| `tools/raz_aw_validate_authority_linkage_contract.py` | S3G1 local validator | assumed present from S3G1 push | safe_to_quote for behavior, not copied | no |
| `raz_output_jsons/derived/Level_*/normalized/*.json` | local text-bearing legacy artifacts | referenced by report only | full_text_do_not_quote | yes |
| `raz_output_jsons/derived/Level_*/enriched/*.json` | local text-bearing legacy artifacts | referenced by report only | full_text_do_not_quote | yes |

Observed S3G1 evidence:

```text
files_scanned_count: 161
normalized_books: 1959
normalized_sentences: 201993
normalized_page_units: 22632
normalized_reuse_units: 19332
enriched_books: 1959
enriched_sentences: 201993
enriched_units: 41964
```

Observed blocker class:

```text
authority_linkage_contract_violations
```

Observed full-record gap count:

```text
491832 records are missing S3G contract fields such as source_traceability, promotion_status, generated_content, derived_from_original_text, allowed_authority_targets, blocked_authority_targets, and required_review_before_promotion.
```

---

## 3. Problem Statement

The RAZ A-W legacy derived corpus has already passed the normalized and enriched validators. Those validators confirm that the current candidate corpus is structurally stable for existing S3C/S3D purposes.

However, the S3G1 authority-linkage validator correctly fails closed because the legacy artifacts do not yet expose the S3F/S3G contract fields required for future authority bridge safety.

The core design question for S3I:

```text
Should S3G fields be backfilled directly into existing normalized/enriched corpus files, or should a separate authority-linkage view/emitter layer be introduced?
```

S3I recommendation:

```text
Introduce a separate authority-linkage backfill emitter and output a contract-compliant linkage view. Do not directly rewrite existing normalized/enriched corpus files in the first implementation.
```

---

## 4. Decision: Bridge-Layer Emitter Over Direct Corpus Rewrite

### 4.1 Recommended architecture

```text
legacy normalized/enriched artifacts
        ↓ read-only input
S3I/S3J authority-linkage backfill emitter
        ↓ generated linkage view, no raw text dump
authority-linkage contract validation
        ↓
future Reading / Content Query / Authority bridge design
```

### 4.2 Why not directly patch existing derived corpus now

Directly adding S3G fields into all normalized/enriched artifacts would touch approximately:

```text
491832 derived records
```

That creates avoidable risk:

```text
1. It would mutate an already passing S3C/S3D corpus.
2. It could break current normalized/enriched schemas or downstream tools.
3. It would create large text-bearing derived diffs that must not be pushed to GitHub.
4. It would hide the distinction between legacy extraction artifacts and bridge-ready authority-linkage records.
5. It would make rollback harder if S3G field defaults need adjustment.
```

### 4.3 Why a separate emitter is safer

A separate linkage view can:

```text
1. Keep normalized/enriched artifacts read-only.
2. Generate deterministic S3G contract fields without altering source artifacts.
3. Keep text-bearing content local only.
4. Emit sanitized reports to GitHub.
5. Allow future bridge tasks to consume only contract-compliant view records.
6. Preserve auditability from source_ref / ids / hashes.
```

---

## 5. Proposed Output Artifacts

### 5.1 Local text-bearing linkage view

Local-only output:

```text
raz_output_jsons/linkage/Level_<LEVEL>/raz_<LEVEL>_authority_linkage_view.json
```

Commit policy:

```text
Do not push these files to GitHub if they include text-bearing content or full record payloads.
```

Purpose:

```text
Provide a contract-compliant view over current normalized/enriched records for local validation and future bridge preparation.
```

### 5.2 Sanitized aggregate report

GitHub-safe output:

```text
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
```

Contents allowed:

```text
record counts
level counts
artifact layer counts
field completion counts
status distribution counts
hash-only coverage metrics
sample issue ids only
no sentence text
no page text
no raw_text
no full derived records
```

### 5.3 Sanitized validation report

GitHub-safe output from existing S3G1 validator after emitter output is generated:

```text
reports/raz/raz_authority_linkage_contract_validation.json
```

Expected later status after S3J implementation:

```text
IMPLEMENTED_PASS_FOR_LINKAGE_VIEW
```

or:

```text
IMPLEMENTED_WITH_RESIDUAL_GAPS
```

S3I does not require changing the current S3G1 status yet.

---

## 6. Proposed Emitter Name and CLI

Future implementation file:

```text
tools/build_raz_authority_linkage_view.py
```

Suggested CLI:

```powershell
python tools/build_raz_authority_linkage_view.py `
  --derived-root raz_output_jsons/derived `
  --linkage-root raz_output_jsons/linkage `
  --reports-dir reports/raz
```

Optional validation sequence:

```powershell
python tools/build_raz_authority_linkage_view.py `
  --derived-root raz_output_jsons/derived `
  --linkage-root raz_output_jsons/linkage `
  --reports-dir reports/raz

python tools/raz_aw_validate_authority_linkage_contract.py `
  --derived-root raz_output_jsons/linkage `
  --reports-dir reports/raz
```

Implementation note:

```text
S3J may need to extend the validator with a --mode or --input-root flag if linkage view file names differ from legacy normalized/enriched file names.
```

---

## 7. Input Mapping Design

### 7.1 Input artifacts

Read-only inputs:

```text
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_books.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_sentences.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_page_units.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_reuse_units.json
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_books.json
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_sentences.json
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_units.json
```

### 7.2 Join keys

| Source artifact | Primary key | Join target |
| --- | --- | --- |
| normalized books | `book_uid` | enriched books, source trace root |
| normalized sentences | `sentence_uid` | enriched sentences, page/reuse units |
| normalized page units | `page_unit_uid` | enriched units where `unit_uid == page_unit_uid` |
| normalized reuse units | `reuse_unit_uid` | enriched units where `unit_uid == reuse_unit_uid` |
| enriched books | `book_uid` | normalized books |
| enriched sentences | `sentence_uid` | normalized sentences |
| enriched units | `unit_uid` | normalized page/reuse units |

### 7.3 Record identity policy

Use stable linkage IDs:

```text
linkage_uid = original_uid + "::authority_linkage_v1"
```

Examples:

```text
raz_A_100_s0001::authority_linkage_v1
raz_A_100_p0003::authority_linkage_v1
raz_A_100_r0001::authority_linkage_v1
```

No generated linkage UID should include source text.

---

## 8. Field Backfill Rules

### 8.1 `source_traceability`

Build from existing legacy fields:

| Source | Target source_traceability field |
| --- | --- |
| `level` | `source_level` |
| `book_id` | `source_book_id` |
| `book_uid` | `source_book_uid` |
| `page_number` | `source_page_number` |
| `page_unit_uid` / `unit_uid` for page unit | `source_page_unit_id` |
| `reuse_unit_uid` / `unit_uid` for reuse unit | `source_reuse_unit_id` |
| `sentence_uid` | `source_sentence_candidate_ids` |
| `sentence_uids` | `source_sentence_candidate_ids` |
| `source_ref.raw_file_relative_path` | `raw_file_relative_path` |
| `source_ref.raw_candidate_ref` | `raw_candidate_ref` |
| `source_ref.raw_page_ref` | `raw_page_ref` |
| `source_ref.deterministic_index_ref` | `deterministic_index_ref` |

Default values:

```text
source_type = raz
source_passage_unit_id = null
source_sentence_final_ids = []
trace_confidence = high if required id and source_ref fields are present; otherwise medium or unknown
```

### 8.2 `promotion_status`

Fail-closed default:

```text
promotion_status = promotion_blocked
```

Exception:

```text
If artifact layer is a summary_report or validation_report, use not_promoted or not_applicable-equivalent policy outside authority promotion paths.
```

S3I recommends not using `eligible_after_review` yet because no target review has happened.

### 8.3 `generated_content`

For current legacy normalized/enriched artifacts:

```text
generated_content = false
```

Condition:

```text
Only if the artifact is derived by deterministic normalization/enrichment from RAZ source and not by LLM generation.
```

If a future artifact comes from LLM rewriting, template generation, exercise generation, or assessment generation:

```text
generated_content = true
generation_method required
generation_prompt_id or generation_task_id required
```

### 8.4 `derived_from_original_text`

For current RAZ normalized/enriched artifacts:

```text
derived_from_original_text = true
```

Reason:

```text
They are source-derived candidate artifacts, not newly authored authority content.
```

### 8.5 `authority_status`

Current normalized records already expose:

```text
authority_status = candidate_only
```

Current enriched records expose:

```text
authority_linkage_status = candidate_only / not_evaluated
```

Emitter rule:

```text
If authority_status exists, preserve it.
If authority_linkage_status == candidate_only, map authority_status = candidate_only.
If authority_linkage_status == not_evaluated, map authority_status = candidate_only and promotion_status = promotion_blocked.
```

### 8.6 `required_review_before_promotion`

Default by artifact layer:

| Artifact layer | required_review_before_promotion |
| --- | --- |
| `raw_source_reference` | `none` |
| `sentence_normalized` | `sentence_validation` |
| `sentence_enriched` | `sentence_validation` |
| `page_unit` | `page_unit_review` |
| `reuse_unit_candidate` | `human_review_required` |
| `derived_dialogue_candidate` | `dialogue_rewrite_review` |
| `writing_model_seed` | `writing_template_review` |
| `exercise_seed` | `exercise_schema_review` |
| `assessment_seed` | `assessment_contract_review` |

### 8.7 Authority target allow/block policy

Default fail-closed policy:

| Artifact layer | allowed_authority_targets | blocked_authority_targets |
| --- | --- | --- |
| `raw_source_reference` | `None` | all real authority targets |
| `sentence_normalized` | `SentenceAuthority`, `ContentQueryLayer` | `ReadingAuthority`, `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `sentence_enriched` | `SentenceAuthority`, `ContentQueryLayer` | `ReadingAuthority`, `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `page_unit` | `ReadingAuthority`, `ContentQueryLayer` | `DialogueAuthority`, `WritingAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `reuse_unit_candidate` | `ContentQueryLayer` | `SentenceAuthority`, `ReadingAuthority`, `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |

Important rule:

```text
allowed_authority_targets allows candidate discovery only. It does not authorize promotion.
```

Promotion remains blocked until explicit target review and promotion task.

---

## 9. Linkage View Record Shape

Recommended record shape:

```json
{
  "record_uid": "raz_A_100_s0001::authority_linkage_v1",
  "source_record_uid": "raz_A_100_s0001",
  "artifact_layer": "sentence_normalized",
  "source_traceability": {
    "source_type": "raz",
    "source_level": "A",
    "source_book_id": "100",
    "source_book_uid": "raz_A_100",
    "source_page_number": 1,
    "source_page_unit_id": null,
    "source_passage_unit_id": null,
    "source_sentence_candidate_ids": ["raz_A_100_s0001"],
    "source_sentence_final_ids": [],
    "source_reuse_unit_id": null,
    "raw_file_relative_path": "...",
    "raw_candidate_ref": "...",
    "raw_page_ref": null,
    "deterministic_index_ref": "...",
    "derived_from_original_text": true,
    "generated_content": false,
    "generation_method": "none",
    "generation_prompt_id": null,
    "generation_task_id": null,
    "trace_confidence": "high"
  },
  "authority_status": "candidate_only",
  "promotion_status": "promotion_blocked",
  "review_status": "pending",
  "required_review_before_promotion": "sentence_validation",
  "allowed_authority_targets": ["SentenceAuthority", "ContentQueryLayer"],
  "blocked_authority_targets": ["ReadingAuthority", "DialogueAuthority", "WritingAuthority", "ExerciseAuthority", "AssessmentAuthority", "LearningOpportunityBinding"],
  "generated_content": false,
  "derived_from_original_text": true,
  "trace_confidence": "high",
  "content_hash": "hash-only-if-implemented",
  "clean_text_hash": "hash-only-if-implemented"
}
```

Text policy:

```text
The linkage view may include hashes and IDs. It should avoid copying text unless a later local-only consumer explicitly needs text. GitHub reports must remain text-free.
```

---

## 10. Output Schema Strategy

Use existing supplemental schema:

```text
schemas/raz/raz_authority_linkage_contract.schema.json
```

Recommended linkage view package shape:

```json
{
  "schema_version": "raz_authority_linkage_contract.v1",
  "records": []
}
```

The emitter should make every emitted record validate against the supplemental schema.

If the current supplemental schema needs patching, that should happen in S3J implementation with explicit preflight and schema compatibility notes.

---

## 11. Validator Integration Strategy

Current S3G1 validator scans legacy derived normalized/enriched file shapes. For S3J, two options exist:

### Option A: Extend existing validator

Add CLI:

```powershell
python tools/raz_aw_validate_authority_linkage_contract.py `
  --input-root raz_output_jsons/linkage `
  --input-mode linkage_view `
  --reports-dir reports/raz
```

Advantages:

```text
single validation tool
same report path
same error codes
```

Risk:

```text
Existing legacy validation logic may become harder to read if two modes diverge.
```

### Option B: Add dedicated validator for linkage view

New file:

```text
tools/validate_raz_authority_linkage_view.py
```

Advantages:

```text
clean separation between legacy gap scanner and linkage-view contract validator
```

Risk:

```text
more validator files to maintain
```

S3I recommendation:

```text
Use Option A only if code remains simple. Otherwise use Option B.
```

---

## 12. Sanitized Report Requirements

Emitter summary report:

```text
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
```

Required fields:

```text
task_id
report_type
status
sanitized
contains_text_values
raw_mutation
derived_mutation
authority_promotion
input_derived_root
output_linkage_root
levels_processed
files_read_count
records_emitted_count
artifact_layer_counts
promotion_status_counts
authority_status_counts
review_status_counts
required_review_counts
allowed_target_counts
blocked_target_counts
trace_confidence_counts
missing_source_ref_counts
hash_coverage_counts
sample_issue_ids
warnings
blockers
```

Forbidden keys in report:

```text
text
raw_text
page_text
full_raw_json
full_derived_record
sentence_candidates
page_units raw payload
reuse_unit_candidates raw payload
```

---

## 13. Backfill Validation Expectations

Current S3G1 result:

```text
IMPLEMENTED_WITH_BLOCKED_LEGACY_GAPS
```

Expected after S3J emitter implementation:

```text
legacy corpus remains unchanged
linkage view passes contract validation
S3G1 legacy scan may still show legacy gaps if pointed at derived root
S3J linkage validation should pass or show only residual trace issues
```

Expected status vocabulary:

```text
BACKFILL_EMITTER_DESIGN_READY
BACKFILL_EMITTER_DESIGN_PARTIAL
BACKFILL_EMITTER_BLOCKED_BY_SCHEMA_GAP
BACKFILL_EMITTER_BLOCKED_BY_INPUT_GAP
```

---

## 14. Migration and Compatibility Notes

S3I migration policy:

```text
Do not rewrite normalized/enriched artifacts in-place.
Treat S3I/S3J linkage view as derived bridge metadata.
Keep existing normalized/enriched validators unchanged.
Keep S3G1 validator fail-closed.
Add separate validation path for linkage view.
```

Compatibility benefits:

```text
1. S3C normalized PASS remains meaningful.
2. S3D enriched PASS remains meaningful.
3. S3G1 legacy gap report remains audit evidence.
4. S3J can be rerun deterministically without changing source artifacts.
5. Future bridge tasks can consume only linkage view records.
```

---

## 15. Risk Analysis

| Risk | Level | Impact | Mitigation |
| --- | --- | --- | --- |
| Direct rewrite of 491832 legacy records | HIGH | could break existing pipeline and create large text-bearing local diffs | use separate linkage view instead |
| Wrong default `generated_content=false` | MEDIUM | generated records could be misclassified if future sources are mixed | only apply false to deterministic normalized/enriched RAZ artifacts; future generated artifacts require true + metadata |
| Target allowlist too broad | HIGH | candidates may appear eligible for authority too early | keep promotion_status=promotion_blocked and block LearningOpportunityBinding |
| Reuse units over-promoted | HIGH | reusable candidates may be mistaken for formal Reading/Writing/Assessment authority | allow only ContentQueryLayer discovery by default |
| S3G validator hidden by emitter | MEDIUM | legacy gap signal may be lost | keep legacy scan and linkage-view validation separate |
| Text leakage into GitHub reports | HIGH | repository hygiene and content risk | report-only aggregate counts, ids, hashes; no text values |
| Assessment accidentally marked ready | HIGH | learner-state evidence becomes unsafe | block AssessmentAuthority unless assessment contract fields exist |
| Source trace confidence overestimated | MEDIUM | future audit may trust weak trace | compute high only when source_ref and ids are complete; otherwise medium/unknown |

---

## 16. Recommended Next Tasks

### 1. `RAZ-AW-S3J_SourceTraceabilityBackfillEmitter_Implementation`

Purpose:

```text
Implement tools/build_raz_authority_linkage_view.py and generate local linkage view files plus sanitized emitter summary.
```

Expected files to create:

```text
tools/build_raz_authority_linkage_view.py
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
```

Expected local-only files:

```text
raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json
```

Risk:

```text
Medium
```

Corpus modification allowed:

```text
No. Read legacy derived corpus only; write linkage view only.
```

### 2. `RAZ-AW-S3K_AuthorityLinkageViewValidator_QA`

Purpose:

```text
Validate that generated linkage view records comply with schemas/raz/raz_authority_linkage_contract.schema.json and remain promotion-blocked.
```

Expected files to inspect:

```text
tools/build_raz_authority_linkage_view.py
tools/raz_aw_validate_authority_linkage_contract.py or dedicated linkage view validator
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
reports/raz/raz_authority_linkage_contract_validation.json
```

Risk:

```text
Low to Medium
```

### 3. `RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan`

Purpose:

```text
Design the review path for page_unit and future passage_unit records after the linkage view exists.
```

Prerequisite:

```text
S3J/S3K should pass or have only non-blocking residual gaps.
```

### 4. `RAZ-AW-S5_ReadingAuthorityBridge_DesignScan`

Purpose:

```text
Design Reading Authority bridge intake using the linkage view rather than legacy normalized/enriched records directly.
```

Prerequisite:

```text
S3J/S3K + S4 page/passage review contract.
```

---

## 17. Final Verdict

Verdict:

```text
BACKFILL_EMITTER_DESIGN_READY
```

Reason:

```text
S3G1 proved that the validator works and that the legacy normalized/enriched corpus lacks S3G contract fields. S3I defines a safer bridge-layer emitter strategy that keeps existing passing corpus artifacts unchanged while generating a separate contract-compliant authority-linkage view for future bridge tasks.
```

Controlled final statement:

```text
Proceed to S3J emitter implementation. Do not directly rewrite normalized/enriched corpus files and do not proceed to S4/S5 bridge tasks until the linkage view is generated and validated.
```
