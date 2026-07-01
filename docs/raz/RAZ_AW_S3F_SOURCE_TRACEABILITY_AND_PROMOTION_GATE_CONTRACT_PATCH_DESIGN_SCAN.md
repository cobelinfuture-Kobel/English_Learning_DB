# RAZ-AW-S3F Source Traceability and Promotion Gate Contract Patch Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S3F_SourceTraceabilityAndPromotionGateContractPatch_DesignScan
```

Execution mode:

```text
DesignScan only
```

S3E dependency:

```text
RAZ-AW-S3E_AuthorityLinkageReadinessDesignScan
```

S3E file status:

```text
present_in_github
```

S3E verdict used:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

Control flags:

| Control | Status |
| --- | --- |
| implementation allowed | false |
| corpus modification allowed | false |
| promotion allowed | false |
| runtime modification allowed | false |
| schema modification allowed | false |
| builder modification allowed | false |
| validator modification allowed | false |
| GitHub full-text corpus push allowed | false |

Risk level:

```text
Low
```

Reason:

```text
This task creates one documentation file only. It does not modify raw corpus, derived corpus, schemas, builders, validators, runtime, tests, or authority records.
```

Repository-safe conclusion:

```text
The S3F contract design can be committed safely because it contains only sanitized contract guidance, field matrices, and validator requirements. It does not contain RAZ raw text or full derived corpus content.
```

---

## 2. Files Inspected

| Path | Role | Inspection status | Quote safety | Full-text risk |
| --- | --- | --- | --- | --- |
| `docs/raz/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN.md` | S3E readiness source and gap list | directly inspected | safe_to_quote | no |
| `schemas/raz/raz_normalized_sentences.schema.json` | normalized sentence contract | directly inspected | safe_to_quote | no |
| `schemas/raz/raz_normalized_page_units.schema.json` | normalized page-unit contract | directly inspected | safe_to_quote | no |
| `schemas/raz/raz_normalized_reuse_units.schema.json` | normalized reuse-unit contract | directly inspected | safe_to_quote | no |
| `schemas/raz/raz_enriched_units.schema.json` | enriched page/reuse unit candidate contract | directly inspected | safe_to_quote | no |
| `docs/raz/prompts/RAZ_AW_S3F_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_DESIGN_SCAN_PROMPT.md` | operator prompt contract | expected / previously created | safe_to_quote | no |
| `raz_output_jsons/derived/Level_*/...` | text-bearing local derived artifacts | not opened in GitHub scan | full_text_do_not_quote | yes |

Observed schema evidence:

```text
normalized sentences already carry sentence_uid, book_uid, level, book_id, page_number, sentence_index_in_book, text, source_ref, authority_status, normalization_status, content_authority_status, and review_status.

normalized page units already carry page_unit_uid, book_uid, level, book_id, page_number, sentence_uids, source_ref, authority_status, normalization_status, content_authority_status, and review_status.

normalized reuse units already carry reuse_unit_uid, book_uid, level, book_id, page_range, sentence_uids, reuse_candidate_type, source_ref, authority_status, normalization_status, content_authority_status, and review_status.

enriched units already carry unit_uid, unit_type, book_uid, level, sentence_uids, unit_sentence_count, unit_token_count, candidate_use_cases, candidate_reuse_tags, usefulness scores, authority_linkage_status, enrichment_status, review_status, and validation_status.
```

Important current safety evidence:

```text
authority_status is currently candidate_only in normalized sentence/page/reuse schemas.
content_authority_status is currently not_promoted in normalized sentence/page/reuse schemas.
authority_linkage_status is currently candidate_only or not_evaluated in enriched unit schema.
review_status currently supports pending / needs_review / rejected.
```

---

## 3. S3E Gap Recap

S3E conclusion:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

S3E controlled final statement:

```text
The current RAZ A-W candidate corpus is ready for bridge design continuation, but not ready for content authority promotion.
```

S3E blocker class:

```text
RAZ A-W artifacts are structurally sufficient for later bridge design, but Authority promotion is unsafe until source traceability and promotion gates are explicit.
```

Known missing or incomplete fields:

```text
promotion_status
generated_content
derived_from_original_text
source_traceability
allowed_authority_targets
blocked_authority_targets
required_review_before_promotion
page/passage lineage normalization
assessment seed structure
```

S3F design objective:

```text
Define the contract patch required before any S3G implementation or later S4/S5/S6 bridge design is safe.
```

---

## 4. Artifact Layer Taxonomy

| Artifact layer | Purpose | May contain original RAZ text | May contain generated content | Direct promotion allowed | Required review before promotion |
| --- | --- | --- | --- | --- | --- |
| `raw_source_reference` | identify source file/page/candidate without copying full text | yes, outside GitHub summaries | no | no | none; source reference only |
| `sentence_candidate` | one extracted sentence candidate | yes | no | no | sentence_validation |
| `sentence_normalized` | normalized sentence candidate | yes | no | no | sentence_validation |
| `sentence_enriched` | enriched sentence candidate with candidate refs/tags | yes | no | no | sentence_validation + enrichment QA |
| `sentence_final_candidate` | future reviewed sentence candidate | yes | no | no, unless explicit promotion task | sentence_validation + human/contract review |
| `page_unit` | ordered sentence group from one source page | yes | no | no | page_unit_review |
| `passage_unit` | future multi-page or passage-level group | yes | no | no | page/passage review |
| `reuse_unit_candidate` | reusable multi-sentence candidate | yes | no by default | no | human_review_required and target-specific review |
| `derived_dialogue_candidate` | dialogue rewritten from source material | may quote source-derived fragments | yes | no | dialogue_rewrite_review |
| `writing_model_seed` | template or writing model candidate | may quote source-derived fragments | possible | no | writing_template_review |
| `exercise_seed` | exercise item candidate | possible | possible | no | exercise_schema_review |
| `assessment_seed` | assessment item candidate | possible | possible | no | assessment_contract_review |
| `summary_report` | aggregate report, no full corpus dump | no | no | no | none |
| `validation_report` | validator result report | no | no | no | none |
| `bridge_candidate` | future join record between RAZ candidate and authority layer | no or minimal text | possible metadata only | no | bridge-specific review |
| `formal_authority_record` | future approved content authority item | controlled | controlled | yes, only by explicit promotion task | target authority approval |

Key boundary:

```text
S3F does not authorize any transition into formal_authority_record. It only defines fields and gates required before a later implementation can validate such transitions.
```

---

## 5. Source Traceability Contract Proposal

### 5.1 Canonical object

Future RAZ-derived artifacts should expose a normalized object:

```json
{
  "source_traceability": {
    "source_type": "raz",
    "source_level": "A",
    "source_book_id": "1234",
    "source_book_uid": "raz_A_1234",
    "source_page_number": 3,
    "source_page_unit_id": "raz_A_1234_p0003",
    "source_passage_unit_id": null,
    "source_sentence_candidate_ids": ["raz_A_1234_s0001"],
    "source_sentence_final_ids": [],
    "source_reuse_unit_id": null,
    "raw_file_relative_path": "raz_output_jsons/Level_A/raz_A_1234_audio_timeline_extract.json",
    "raw_candidate_ref": "...",
    "raw_page_ref": "...",
    "deterministic_index_ref": "...",
    "derived_from_original_text": true,
    "generated_content": false,
    "generation_method": null,
    "generation_prompt_id": null,
    "generation_task_id": null,
    "trace_confidence": "high"
  }
}
```

### 5.2 Allowed values

| Field | Type | Allowed / expected values | Notes |
| --- | --- | --- | --- |
| `source_type` | string | `raz` | Required for all RAZ-origin artifacts |
| `source_level` | string | `A` through `W` | Equivalent to current `level`; must be materialized in trace object |
| `source_book_id` | string | numeric string | Equivalent to current `book_id` |
| `source_book_uid` | string | `raz_[A-W]_[0-9]+` | Equivalent to current `book_uid` |
| `source_page_number` | integer/null | `>= 0` or null | Required for page/passage/reading candidates |
| `source_page_unit_id` | string/null | `raz_[A-W]_[0-9]+_p[0-9]{4}` | Required for page-unit derived records |
| `source_passage_unit_id` | string/null | future stable id | Required after passage-unit layer exists |
| `source_sentence_candidate_ids` | array | stable sentence ids | Required for derived candidates and units |
| `source_sentence_final_ids` | array | future final sentence ids | Empty until sentence promotion exists |
| `source_reuse_unit_id` | string/null | stable reuse id | Required for reuse-derived candidates |
| `raw_file_relative_path` | string | local raw source path | Must not imply GitHub commit of full raw data |
| `derived_from_original_text` | boolean/unknown | `true`, `false`, or `unknown` in migration | `unknown` is safer than false for legacy data |
| `generated_content` | boolean/unknown | `true`, `false`, or `unknown` in migration | never default legacy records to false without evidence |
| `generation_method` | string/null | e.g. `llm_rewrite`, `template_extraction`, `rule_based` | Required when generated_content=true |
| `generation_prompt_id` | string/null | prompt or task id | Required when generated_content=true and prompt-based |
| `generation_task_id` | string/null | task id | Recommended for auditability |
| `trace_confidence` | string | `high`, `medium`, `low`, `unknown` | Legacy records default to unknown or medium depending evidence |

### 5.3 Minimum trace requirements by layer

| Artifact layer | Minimum trace requirements |
| --- | --- |
| `sentence_candidate` | `source_type`, `source_level`, `source_book_id`, `source_book_uid`, `source_sentence_candidate_ids`, raw source refs |
| `sentence_normalized` | all sentence candidate requirements plus normalized id and `derived_from_original_text=true`, `generated_content=false` if builder proves no generation |
| `sentence_enriched` | normalized sentence trace plus enrichment status and candidate refs |
| `page_unit` | `source_page_number`, `source_page_unit_id`, ordered `source_sentence_candidate_ids`, raw page ref |
| `passage_unit` | `source_passage_unit_id`, page-unit ids, ordered sentence ids, passage derivation rule |
| `reuse_unit_candidate` | `source_reuse_unit_id`, page range, sentence ids, reuse candidate type |
| `derived_dialogue_candidate` | source ids, `generated_content=true`, `derived_from_original_text=true`, generation metadata, `review_status=pending` |
| `writing_model_seed` | source ids, generated/derived fields, template extraction method, `review_status=pending` |
| `exercise_seed` | source ids, generated/derived fields, question schema reference if available |
| `assessment_seed` | source ids, generated/derived fields, assessment contract fields, answer/scoring/error metadata |

---

## 6. Candidate / Authority Status Contract Proposal

### 6.1 Required status fields

```text
authority_status
promotion_status
review_status
required_review_before_promotion
```

Current schemas already have `authority_status`, `content_authority_status`, and `review_status`. S3F recommends normalizing the future contract around explicit `promotion_status` while keeping `content_authority_status` as a legacy-compatible alias if needed.

### 6.2 `authority_status` allowed values

```text
raw_reference
candidate_only
validated_candidate
reviewed_candidate
promoted_authority
rejected
deprecated
```

Meaning:

| Value | Meaning |
| --- | --- |
| `raw_reference` | source reference only; not a content candidate |
| `candidate_only` | candidate exists but cannot be used as authority |
| `validated_candidate` | structural validator passed; still not authority |
| `reviewed_candidate` | human or contract review passed; still needs explicit promotion task |
| `promoted_authority` | formally promoted by dedicated authority task |
| `rejected` | failed review or validation |
| `deprecated` | retired after prior use |

### 6.3 `promotion_status` allowed values

```text
not_promoted
promotion_blocked
eligible_after_review
eligible_after_validation
eligible_after_contract_patch
promoted
rejected
```

Default rule:

```text
Any legacy artifact without explicit promotion_status must default to promotion_blocked, not eligible.
```

### 6.4 `review_status` allowed values

```text
not_required
pending
in_review
passed
failed
needs_revision
needs_review
rejected
```

Compatibility note:

```text
Current schemas use pending / needs_review / rejected. A future implementation may either extend the enum or map legacy values into a bridge-layer review vocabulary.
```

### 6.5 `required_review_before_promotion` allowed values

```text
none
sentence_validation
page_unit_review
reading_authority_review
dialogue_rewrite_review
writing_template_review
exercise_schema_review
assessment_contract_review
human_review_required
```

### 6.6 Valid and invalid combinations

| authority_status | promotion_status | review_status | Valid? | Notes |
| --- | --- | --- | --- | --- |
| `candidate_only` | `not_promoted` | `pending` | yes | normal current candidate state |
| `candidate_only` | `promotion_blocked` | `needs_review` | yes | safest default for legacy ambiguous records |
| `validated_candidate` | `eligible_after_review` | `pending` | yes | validation passed, review pending |
| `reviewed_candidate` | `eligible_after_contract_patch` | `passed` | yes | bridge may consume only if target allows reviewed candidates |
| `promoted_authority` | `promoted` | `passed` | yes | only after explicit future promotion task |
| `candidate_only` | `promoted` | any | no | illegal direct promotion |
| `reuse_unit_candidate` via layer | `promoted` | any | no | reuse units cannot be direct authority |
| generated content | `promoted` | `pending` | no | generated content requires review passed |

---

## 7. Promotion Gate State Machine

### 7.1 Legal flow

```text
candidate_only
↓ validation_passed
validated_candidate
↓ review_passed
reviewed_candidate
↓ explicit_promotion_task
promoted_authority
```

### 7.2 Legal transition table

| From | Event | To | Allowed? | Required evidence |
| --- | --- | --- | --- | --- |
| `candidate_only` | structural validation passed | `validated_candidate` | yes | validator pass report |
| `validated_candidate` | target-specific review passed | `reviewed_candidate` | yes | review status passed |
| `reviewed_candidate` | explicit authority promotion task | `promoted_authority` | yes | promotion task id + target authority id |
| `candidate_only` | explicit promotion task | `promoted_authority` | no | must pass validation and review first |
| `reuse_unit_candidate` | direct promotion | `promoted_authority` | no | must derive reviewed target-specific record first |
| `derived_dialogue_candidate` | dialogue review passed | `reviewed_candidate` | yes | generated metadata + dialogue review |
| `exercise_seed` | answer/scoring absent | `reviewed_candidate` | no | question/answer/scoring contract required |
| `assessment_seed` | assessment contract passed | `reviewed_candidate` | yes | answer key, scoring, error/remediation policy |

### 7.3 Blocked transitions

```text
candidate_only -> promoted_authority
reuse_unit_candidate -> promoted_authority
derived_dialogue_candidate -> formal Dialogue Authority without dialogue_rewrite_review
writing_model_seed -> formal Writing Authority without writing_template_review
exercise_seed -> Assessment Authority without exercise_schema_review + answer key + scoring rule
assessment_seed -> Assessment Authority without assessment_contract_review
any generated_content=true record -> promoted_authority with review_status pending
any artifact with missing source_traceability -> promoted_authority
any artifact with target in blocked_authority_targets -> promoted_authority for that target
```

---

## 8. Allowed and Blocked Authority Targets

### 8.1 Canonical fields

```text
allowed_authority_targets
blocked_authority_targets
```

Allowed target values:

```text
SentenceAuthority
ReadingAuthority
DialogueAuthority
WritingAuthority
ExerciseAuthority
AssessmentAuthority
ContentQueryLayer
LearningOpportunityBinding
None
```

### 8.2 Default target policy by artifact layer

| Artifact layer | allowed_authority_targets | blocked_authority_targets |
| --- | --- | --- |
| `raw_source_reference` | `None` | all authority targets |
| `sentence_candidate` | `SentenceAuthority`, `ContentQueryLayer` | `ReadingAuthority`, `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `sentence_normalized` | `SentenceAuthority`, `ContentQueryLayer` | `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `sentence_enriched` | `SentenceAuthority`, `ContentQueryLayer` | `DialogueAuthority`, `WritingAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `page_unit` | `ReadingAuthority`, `ContentQueryLayer` | `DialogueAuthority`, `WritingAuthority`, `AssessmentAuthority` |
| `passage_unit` | `ReadingAuthority`, `ContentQueryLayer` | `DialogueAuthority`, `WritingAuthority`, `AssessmentAuthority` |
| `reuse_unit_candidate` | `ContentQueryLayer` | `SentenceAuthority`, `ReadingAuthority`, `DialogueAuthority`, `WritingAuthority`, `ExerciseAuthority`, `AssessmentAuthority`, `LearningOpportunityBinding` |
| `derived_dialogue_candidate` | `DialogueAuthority`, `ContentQueryLayer` after review | `SentenceAuthority`, `ReadingAuthority`, `AssessmentAuthority` |
| `writing_model_seed` | `WritingAuthority`, `ContentQueryLayer` after review | `SentenceAuthority`, `ReadingAuthority`, `AssessmentAuthority` |
| `exercise_seed` | `ExerciseAuthority`, `ContentQueryLayer` after schema review | `AssessmentAuthority` until answer/scoring/error contract exists |
| `assessment_seed` | `AssessmentAuthority`, `ContentQueryLayer` after assessment review | all other authority targets unless explicitly derived |
| `summary_report` | `None` | all authority targets |
| `validation_report` | `None` | all authority targets |
| `bridge_candidate` | target-specific | all non-target authorities |
| `formal_authority_record` | assigned authority only | all non-assigned authorities |

Fail-closed rule:

```text
If allowed_authority_targets is missing, default to ContentQueryLayer only for candidate discovery and block all promotion targets.
If blocked_authority_targets is missing, default to all authority targets blocked until the validator can compute a safe allow/block policy.
```

---

## 9. Generated / Derived Content Boundary

### 9.1 Identity rule

```text
Original text and generated content must never share the same authority identity.
```

A generated or rewritten item may point back to an original RAZ source through `source_traceability`, but it must have a distinct id and distinct artifact layer.

### 9.2 Content classes

| Class | generated_content | derived_from_original_text | Required metadata |
| --- | --- | --- | --- |
| original RAZ sentence | false, if builder proven | true | source trace only |
| normalized RAZ sentence | false, if deterministic cleanup only | true | source trace + normalization status |
| enriched RAZ candidate | false, if enrichment is tagging only | true | source trace + enrichment status |
| AI-derived dialogue rewrite | true | true | generation method, prompt/task id, review status |
| AI-derived writing template | true or rule_based | true | extraction/generation method, review status |
| AI-derived exercise item | true or rule_based | true | question schema, answer key if present |
| AI-derived assessment item | true or rule_based | true | question schema, answer key, scoring, error/remediation policy |

### 9.3 Generated-content requirements

Any `generated_content=true` record must include:

```text
generation_method
generation_prompt_id or generation_task_id
source_traceability
review_status=pending by default
promotion_status=promotion_blocked by default
allowed_authority_targets limited to ContentQueryLayer until review
```

Legacy migration warning:

```text
Do not default missing generated_content to false. Use unknown unless the builder guarantees deterministic non-generative transformation.
```

---

## 10. Assessment Contract Dependency Note

Assessment cannot be marked READY unless the following exist:

```text
question_type
skill_area
concept_tags
cognitive_skill
correct_answer
answer_key
scoring_rule
error_type
error_detail
remediation_tag
learner_state_update_policy
```

Current status:

```text
Assessment linkage remains NOT_READY.
```

Reason:

```text
The current enriched unit schema has candidate_use_cases including assessment, but the inspected contracts do not expose question schema, answer key, scoring rule, or error-diagnosis fields. A candidate-use-case hint is not an assessment contract.
```

Required future task:

```text
RAZ-AW-S6_AssessmentSeedContract_DesignScan
```

or:

```text
ULGA-S15_AssessmentAuthorityContract_DesignScan
```

Until that task exists, all RAZ assessment targets must remain blocked.

---

## 11. Field-Level Patch Matrix

| Field name | Field type | Allowed values / shape | Required on artifact layers | Optional on artifact layers | Default value | Blocks promotion if missing | Blocks query if missing | Blocks assessment if missing | Migration difficulty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `artifact_layer` | enum | taxonomy in §4 | all records | none | infer if safe, else unknown | yes | yes | yes | low |
| `source_type` | enum | `raz` | all source-derived records | reports | `raz` where proven | yes | no | yes | low |
| `source_level` | string | A-W | all RAZ records | reports | map from `level` | yes | yes | yes | low |
| `source_book_id` | string | numeric string | all RAZ records | reports | map from `book_id` | yes | yes | yes | low |
| `source_book_uid` | string | `raz_[A-W]_[0-9]+` | all RAZ records | reports | map from `book_uid` | yes | yes | yes | low |
| `source_page_number` | integer/null | >=0 | page/passage/reading candidates | sentence-only records | map from `page_number` | yes for Reading | yes | yes if assessment source page needed | low |
| `source_page_unit_id` | string/null | stable page unit id | page/passage/reuse/reading candidates | sentence-only records | map from `page_unit_uid` where present | yes for Reading | yes | possible | medium |
| `source_passage_unit_id` | string/null | future stable id | passage records | page/sentence records | null until passage layer exists | no until S4 | no | no | medium |
| `sentence_candidate_id` | string | stable sentence id | sentence records | units | map from `sentence_uid` | yes | yes | yes | low |
| `sentence_final_id` | string/null | future final id | promoted sentence records | candidates | null | yes for promotion | no | yes for assessment promotion | medium |
| `source_sentence_candidate_ids` | array | sentence ids | units, derived records | single sentence records | map from `sentence_uids` | yes | yes | yes | low |
| `source_sentence_final_ids` | array | final sentence ids | promoted bridge records | candidates | [] | yes for final authority | no | yes | medium |
| `candidate_order` | integer/array | deterministic order | page/passage/dialogue candidates | reports | map from sentence index/order | yes for Reading/Dialogue | yes | possible | medium |
| `has_multi_sentence_unit` | boolean | true/false | units | sentence-only records | computed | no | yes for unit filters | possible | low |
| `belongs_to_reuse_unit` | boolean | true/false | sentence/unit joins | reports | computed | no | yes | possible | medium |
| `reuse_unit_id` | string/null | stable reuse id | reuse records | non-reuse records | map from `reuse_unit_uid` | yes for reuse-derived promotion | yes | possible | low |
| `clean_text_hash` | string/null | deterministic hash | text-bearing records | reports | compute later | no | yes for dedupe | yes | medium |
| `content_hash` | string/null | deterministic hash | text-bearing records | reports | compute later | no | yes for dedupe | yes | medium |
| `source_traceability` | object | §5 object | all source-derived records | none | construct from existing fields | yes | yes | yes | medium |
| `authority_status` | enum | §6 | all records | reports | current value if present | yes | yes | yes | low |
| `promotion_status` | enum | §6 | all records | reports | `promotion_blocked` | yes | yes | yes | low |
| `review_status` | enum | §6 | all records | reports | current value or `pending` | yes | yes | yes | low |
| `required_review_before_promotion` | enum | §6 | all candidates | reports | target/layer-specific | yes | no | yes | low |
| `allowed_authority_targets` | array | §8 values | all candidates | reports | fail-closed minimal allowlist | yes | yes | yes | medium |
| `blocked_authority_targets` | array | §8 values | all candidates | reports | all promotion targets blocked | yes | yes | yes | medium |
| `generated_content` | boolean/unknown | true/false/unknown | all derived records | deterministic originals | `unknown` unless proven | yes | yes | yes | medium |
| `derived_from_original_text` | boolean/unknown | true/false/unknown | all source-derived records | reports | `unknown` unless proven | yes | yes | yes | medium |
| `generation_method` | string/null | `llm_rewrite`, `template_extraction`, `rule_based`, etc. | generated records | original records | null | yes if generated | no | yes if generated assessment | medium |
| `generation_prompt_id` | string/null | stable prompt id | prompt-generated records | original records | null | yes if prompt-generated | no | possible | medium |
| `trace_confidence` | enum | high/medium/low/unknown | all trace objects | reports | unknown for legacy | yes for promotion if low/unknown | yes for audit | yes | low |

---

## 12. Validator Design Requirements

Future validator name:

```text
validate_raz_authority_linkage_contract.py
```

Suggested future report:

```text
reports/raz/raz_authority_linkage_contract_validation.json
```

Validator responsibilities:

```text
1. Validate required fields by artifact_layer.
2. Validate enum values for authority_status, promotion_status, review_status, required_review_before_promotion, allowed_authority_targets, and blocked_authority_targets.
3. Reject illegal promotion transitions.
4. Reject candidate_only records marked promoted.
5. Reject direct reuse_unit_candidate promotion.
6. Require generation metadata when generated_content=true.
7. Require source_traceability for all source-derived records.
8. Require page_unit sentence order and source_sentence_candidate_ids.
9. Require allowed/blocked targets to be non-conflicting.
10. Reject AssessmentAuthority readiness without answer key, scoring rule, and error diagnosis fields.
11. Detect full-text report risk in outputs that should be aggregate-only.
12. Fail closed for missing promotion_status or target policy fields.
```

Proposed error codes:

| Error code | Meaning | Severity |
| --- | --- | --- |
| `RAZ_LINK_MISSING_SOURCE_TRACEABILITY` | required trace object missing | blocking |
| `RAZ_LINK_MISSING_PROMOTION_STATUS` | promotion_status missing | blocking |
| `RAZ_LINK_INVALID_AUTHORITY_STATUS` | unsupported authority_status | blocking |
| `RAZ_LINK_INVALID_PROMOTION_STATUS` | unsupported promotion_status | blocking |
| `RAZ_LINK_INVALID_REVIEW_STATUS` | unsupported review_status | blocking |
| `RAZ_LINK_ILLEGAL_PROMOTION_TRANSITION` | transition violates state machine | blocking |
| `RAZ_LINK_CANDIDATE_DIRECT_PROMOTION` | candidate_only moved directly to promoted | blocking |
| `RAZ_LINK_REUSE_UNIT_DIRECT_PROMOTION` | reuse unit direct promotion attempted | blocking |
| `RAZ_LINK_GENERATED_CONTENT_MISSING_METADATA` | generated content lacks generation method/task/prompt | blocking |
| `RAZ_LINK_TARGET_ALLOW_BLOCK_CONFLICT` | same target in allow and block lists | blocking |
| `RAZ_LINK_ASSESSMENT_MISSING_ANSWER_KEY` | assessment target lacks answer key | blocking |
| `RAZ_LINK_ASSESSMENT_MISSING_SCORING_RULE` | assessment target lacks scoring rule | blocking |
| `RAZ_LINK_ASSESSMENT_MISSING_ERROR_DIAGNOSIS` | assessment target lacks error/remediation metadata | blocking |
| `RAZ_LINK_PAGE_UNIT_ORDER_MISSING` | ordered sentence ids missing for page/passage unit | blocking |
| `RAZ_LINK_FULL_TEXT_REPORT_RISK` | aggregate report appears to contain full text dump | blocking |
| `RAZ_LINK_TRACE_CONFIDENCE_TOO_LOW` | trace_confidence too low for promotion | blocking for promotion, warning for query |

---

## 13. Builder Patch Requirements For Future Implementation

This task does not modify builders. A later S3G implementation should inspect and patch the builders or generation scripts that emit normalized and enriched RAZ artifacts.

Likely future patch points:

| Path | Current role | Future patch requirement | Risk |
| --- | --- | --- | --- |
| `tools/raz_aw_validate_normalized.py` | normalized layer validator, named in S3E next-task list | validate source_traceability and status defaults after implementation | medium |
| `tools/raz_aw_validate_enriched.py` | enriched layer validator, named in S3E next-task list | validate authority linkage contract and fail-closed target policy | medium |
| normalized sentence builder | emits sentence-level records | emit `source_traceability`, `promotion_status`, target policy, generated/derived boundary | medium |
| normalized page-unit builder | emits page-unit records | emit `source_page_unit_id`, ordered sentence ids, target policy | medium |
| normalized reuse-unit builder | emits reuse-unit records | force `candidate_only`, block direct promotion targets | medium |
| enriched sentence builder | emits enriched candidate records | preserve trace object, emit content hashes, authority target policy | medium |
| enriched unit builder | emits candidate use cases and reuse tags | map use cases into allowed/blocked authority targets without widening promotion eligibility | high |

If exact script names differ in the local repository, S3G must record actual paths during preflight before patching.

---

## 14. Backward Compatibility and Migration Notes

Migration principles:

```text
1. No raw text regeneration should be required if existing IDs and source_ref data are sufficient.
2. Existing authority_status=candidate_only remains valid.
3. Existing content_authority_status=not_promoted may be mapped to promotion_status=not_promoted or promotion_blocked depending artifact layer.
4. Old artifacts without promotion_status default to promotion_blocked.
5. Old artifacts without generated_content default to unknown, not false, unless deterministic builder evidence proves original-only.
6. Old artifacts without derived_from_original_text default to unknown, not true, unless source_ref proves RAZ-origin derivation.
7. Old reuse units default to candidate_only and direct promotion blocked.
8. Old exercise or assessment hints default to AssessmentAuthority blocked.
9. Missing allowed_authority_targets defaults to ContentQueryLayer only or None depending layer.
10. Missing blocked_authority_targets defaults to all promotion targets blocked.
11. Missing trace_confidence defaults to unknown.
12. Full text-bearing derived files remain local and must not be introduced as GitHub reports.
```

Recommended migration shape:

```text
existing flat fields
↓
construct source_traceability object
↓
add fail-closed promotion_status and target policy
↓
run linkage validator
↓
only then design bridge consumers
```

---

## 15. Risk Analysis

| Risk | Level | Impact | Mitigation | S3F resolution status |
| --- | --- | --- | --- | --- |
| incorrectly defaulting `generated_content=false` | HIGH | generated or rewritten content may be treated as original | default to `unknown` unless builder proof exists | designs mitigation only |
| legacy artifacts treated as promotion-ready | HIGH | candidate corpus could leak into authority | default missing promotion fields to blocked | designs mitigation only |
| reuse units over-promoted into Reading/Writing/Assessment | HIGH | multi-use candidates could corrupt target authorities | block direct promotion; require target-specific derived record | designs mitigation only |
| Assessment bridge built before answer/scoring/error contract | HIGH | learner-state evidence becomes unsafe | keep AssessmentAuthority blocked until S6 or ULGA-S15 | designs mitigation only |
| GitHub full-text corpus leakage | HIGH | repository hygiene and content risk | keep text-bearing derived files local; docs/reports only | partially resolved by doc constraint |
| source trace too weak for future audit | HIGH | future authority review cannot verify provenance | canonical source_traceability object + validator | designs mitigation only |
| Content Query Layer returns unsafe candidates as authority | MEDIUM | UI/planner may show unreviewed content | target policy + candidate filters | designs mitigation only |
| Learning Opportunity Binding binds unreviewed content | HIGH | learner plan may depend on unapproved content | block LearningOpportunityBinding unless promoted or bridge-approved | designs mitigation only |
| target allow/block conflict | MEDIUM | bridge behavior becomes ambiguous | validator error `RAZ_LINK_TARGET_ALLOW_BLOCK_CONFLICT` | designs mitigation only |
| low trace confidence used for promotion | MEDIUM | weak auditability | block promotion when trace_confidence is low/unknown | designs mitigation only |

---

## 16. Recommended Next Tasks

### 1. `RAZ-AW-S3G_SourceTraceabilityAndPromotionGateContractPatch_Implementation`

Purpose:

```text
Apply the S3F contract to schemas/builders/validators using fail-closed defaults.
```

Task type:

```text
Implementation
```

Expected modified files:

```text
schemas/raz/raz_normalized_sentences.schema.json
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_normalized_reuse_units.schema.json
schemas/raz/raz_enriched_sentences.schema.json
schemas/raz/raz_enriched_units.schema.json
RAZ builders that emit normalized/enriched artifacts
RAZ validators that validate normalized/enriched artifacts
```

Expected created files:

```text
reports/raz/raz_authority_linkage_contract_validation.json
```

Risk:

```text
Medium
```

Corpus modification allowed:

```text
Only regenerated sanitized reports and contract-compliant derived outputs if explicitly approved. No GitHub full-text corpus push.
```

### 2. `RAZ-AW-S3H_SourceTraceabilityAndPromotionGateContractPatch_QA`

Purpose:

```text
Validate S3G implementation, fail-closed status defaults, target allow/block rules, and no full-text report leakage.
```

Task type:

```text
QA
```

Expected inspected files:

```text
schemas/raz/*.schema.json
RAZ validators
reports/raz/raz_authority_linkage_contract_validation.json
sanitized aggregate reports
```

Risk:

```text
Low to Medium
```

Corpus modification allowed:

```text
No, unless QA regenerates sanitized reports only.
```

### 3. `RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan`

Purpose:

```text
Define how page_unit and future passage_unit records become reviewable Reading candidates without losing order or lineage.
```

Task type:

```text
DesignScan
```

Expected created file:

```text
docs/raz/RAZ_AW_S4_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_DESIGN_SCAN.md
```

Risk:

```text
Low
```

Corpus modification allowed:

```text
No
```

### 4. `RAZ-AW-S5_ReadingAuthorityBridge_DesignScan`

Purpose:

```text
Design a safe bridge from reviewed RAZ page/passage candidates into Reading Authority or Reading Stub intake after S3G/S3H gates exist.
```

Task type:

```text
DesignScan
```

Expected created file:

```text
docs/raz/RAZ_AW_S5_READING_AUTHORITY_BRIDGE_DESIGN_SCAN.md
```

Risk:

```text
Medium
```

Corpus modification allowed:

```text
No
```

### 5. `RAZ-AW-S6_AssessmentSeedContract_DesignScan`

Purpose:

```text
Define first safe Exercise/Assessment seed schema, answer key, scoring rule, error diagnosis, remediation tags, and learner-state update boundary.
```

Task type:

```text
DesignScan
```

Expected created file:

```text
docs/raz/RAZ_AW_S6_ASSESSMENT_SEED_CONTRACT_DESIGN_SCAN.md
```

Risk:

```text
Medium
```

Corpus modification allowed:

```text
No
```

### 6. `ULGA-S16_ContentQueryLayer_RAZBridge_DesignScan`

Purpose:

```text
Define how contract-compliant RAZ bridge outputs are exposed to static query consumers without treating candidates as promoted authority.
```

Task type:

```text
DesignScan
```

Expected created file:

```text
docs/ulga/ULGA_S16_CONTENT_QUERY_LAYER_RAZ_BRIDGE_DESIGN_SCAN.md
```

Risk:

```text
Medium
```

Corpus modification allowed:

```text
No
```

---

## 17. Final Verdict

Verdict:

```text
CONTRACT_PATCH_DESIGN_READY
```

Reason:

```text
This S3F scan defines the contract patch required after S3E:

1. canonical source_traceability object
2. authority / promotion / review status enums
3. promotion state machine
4. allowed / blocked authority target policy
5. generated / derived content boundary
6. assessment dependency boundary
7. future validator requirements and error codes
8. backward-compatible fail-closed migration defaults

The design is ready for a later S3G implementation task, but it does not make RAZ artifacts ready for Authority promotion.
```

Controlled final statement:

```text
The source-traceability and promotion-gate contract design is ready for implementation planning. The RAZ corpus remains candidate-only and is not ready for Authority promotion.
```
