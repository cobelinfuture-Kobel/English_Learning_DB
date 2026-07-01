# RAZ-AW-S3F Source Traceability and Promotion Gate Contract Patch Design Scan Prompt

## Task ID

```text
RAZ-AW-S3F_SourceTraceabilityAndPromotionGateContractPatch_DesignScan
```

## Execution Mode

```text
DesignScan only.
```

This task designs the contract patch required after S3E. It must not implement the patch yet unless the operator explicitly opens a later Implementation task.

---

## Precondition

This task depends on:

```text
RAZ-AW-S3E_AuthorityLinkageReadinessDesignScan
```

Expected S3E final verdict:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

S3E identified that the current RAZ A-W structure is sufficient to support later bridge design, but it is not safe for Authority promotion yet.

Known S3E gaps to address in this task:

```text
promotion_status
generated_content
derived_from_original_text
source_traceability
allowed_authority_targets
blocked_authority_targets
required_review_before_promotion
Assessment question type / answer key / scoring / error diagnosis contract
```

If the S3E design scan file exists locally, inspect it first:

```text
docs/raz/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN.md
```

If it is absent from GitHub or absent locally, record that as a preflight warning and proceed from the known S3E verdict and gap summary above.

---

## Hard Constraints

```text
Do not modify raw corpus files.
Do not modify derived corpus files.
Do not modify RAZ generated full-text artifacts.
Do not modify runtime code.
Do not modify production builders.
Do not modify production validators.
Do not modify existing schema files.
Do not promote any candidate content into formal Authority.
Do not add RAZ raw text, page text, passage text, or full derived corpus dumps to GitHub.
```

This is a design scan. It may recommend future schema / validator / builder changes, but must not apply them.

Allowed outputs:

```text
Markdown design document
sanitized contract tables
field-level schema proposal
promotion gate rules
future task recommendations
```

Forbidden outputs:

```text
full RAZ text dumps
raw book/page content
derived normalized/enriched corpus dumps
runtime patches
validator implementation
builder implementation
Authority promotion files
```

---

## Goal

Create a design scan document that defines the source-traceability and promotion-gate contract patch required before RAZ-derived artifacts can safely link into future Content Authority layers.

Target future layers:

```text
Sentence Authority
Reading Authority
Dialogue Authority
Writing Authority
Exercise Authority
Assessment Authority
Content Query Layer
Learning Opportunity Binding
```

The design scan must answer:

```text
1. Which fields must be added or normalized?
2. Which artifact layers need those fields?
3. Which values are allowed?
4. Which promotion transitions are legal?
5. Which transitions must be blocked?
6. Which future validator should enforce the contract?
7. Which later implementation task should apply the patch?
```

---

## Conceptual Boundary

The S3F contract patch is not an Authority bridge.

It sits between:

```text
RAZ extraction / derived corpus artifacts
```

and:

```text
future Authority bridges
```

It must define a safe gate so later bridge tasks do not accidentally treat candidates as promoted authority.

Correct sequence:

```text
S3E readiness scan
↓
S3F source traceability + promotion gate contract design
↓
S3G contract patch implementation / validator, if approved later
↓
S4/S5 page-passage review / reading bridge design
↓
Authority bridge implementation, only after gates exist
```

Incorrect sequence:

```text
S3E
↓
Direct Authority promotion
```

This is forbidden.

---

## Repository Scope To Inspect

Inspect relevant files, if present:

```text
docs/raz/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN.md
docs/raz/**
docs/ulga/**
ulga/**
raz_output_jsons/** summary / report / manifest files only
scripts / builders / validators related to RAZ, only for contract awareness
```

Do not open or quote full raw corpus text unless already part of a small sanitized report. If a file appears to contain full RAZ text, record its path and role but do not copy long content into the design scan.

---

## Required Output File

Create one markdown design scan document:

```text
docs/raz/RAZ_AW_S3F_SOURCE_TRACEABILITY_AND_PROMOTION_GATE_CONTRACT_PATCH_DESIGN_SCAN.md
```

If `docs/raz` does not exist, use the closest existing RAZ documentation directory and explain the chosen path in Preflight.

---

## Required Sections

The output document must include:

```text
1. Preflight
2. Files inspected
3. S3E gap recap
4. Artifact layer taxonomy
5. Source traceability contract proposal
6. Candidate / authority status contract proposal
7. Promotion gate state machine
8. Allowed and blocked authority targets
9. Generated / derived content boundary
10. Assessment contract dependency note
11. Field-level patch matrix
12. Validator design requirements
13. Builder patch requirements for future implementation
14. Backward compatibility and migration notes
15. Risk analysis
16. Recommended next tasks
17. Final verdict
```

---

## 1. Preflight Requirements

The Preflight section must record:

```text
S3E file status: present / missing / not_pushed / unknown
S3E verdict used
current task type
implementation allowed: false
corpus modification allowed: false
promotion allowed: false
runtime modification allowed: false
GitHub full-text corpus push allowed: false
```

If S3E is missing, include:

```text
WARNING: S3E design scan file was not found in the inspected repository state. This S3F scan proceeds from the operator-provided S3E verdict and known gap list.
```

---

## 2. Files Inspected

List every inspected file or directory.

For each item, record:

```text
path
role
whether it was directly inspected or only expected
whether it is safe to quote
whether it appears to contain full RAZ text
```

Use safe labels:

```text
safe_to_quote
summary_only
full_text_do_not_quote
not_found
```

---

## 3. S3E Gap Recap

Restate the S3E conclusion:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

Summarize the blocker class:

```text
RAZ A-W artifacts may be structurally sufficient for later bridge design, but Authority promotion is unsafe until source traceability and promotion gates are explicit.
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
review_status
assessment schema fields
```

---

## 4. Artifact Layer Taxonomy

Define the artifact layers that the contract must support:

```text
raw_source_reference
sentence_candidate
sentence_normalized
sentence_enriched
sentence_final_candidate
page_unit
passage_unit
reuse_unit_candidate
derived_dialogue_candidate
writing_model_seed
exercise_seed
assessment_seed
summary_report
validation_report
bridge_candidate
formal_authority_record
```

For each layer, define:

```text
purpose
whether it may contain original RAZ text
whether it may contain generated content
whether it can be promoted directly
which review is required before promotion
```

---

## 5. Source Traceability Contract Proposal

Design a canonical `source_traceability` object.

It should include at least:

```json
{
  "source_type": "raz",
  "source_level": "A-W or specific level",
  "source_book_id": "...",
  "source_page_number": null,
  "source_page_unit_id": null,
  "source_passage_unit_id": null,
  "source_sentence_candidate_ids": [],
  "source_sentence_final_ids": [],
  "derived_from_original_text": true,
  "generated_content": false,
  "generation_method": null,
  "generation_prompt_id": null,
  "review_status": "pending",
  "trace_confidence": "high|medium|low|unknown"
}
```

Define allowed values and meaning for each field.

Also define minimum source trace requirements by artifact layer.

Example:

```text
sentence_candidate requires source_level + source_book_id + sentence_candidate_id
page_unit requires source_level + source_book_id + page_number + ordered source_sentence_candidate_ids
reuse_unit_candidate requires source_page_unit_id + source_sentence_candidate_ids + candidate_only status
derived_dialogue_candidate requires generated_content=true + derived_from_original_text=true + generation_method
```

---

## 6. Candidate / Authority Status Contract Proposal

Define canonical status fields.

Required fields:

```text
authority_status
promotion_status
review_status
required_review_before_promotion
```

Allowed `authority_status` values:

```text
raw_reference
candidate_only
validated_candidate
reviewed_candidate
promoted_authority
rejected
deprecated
```

Allowed `promotion_status` values:

```text
not_promoted
promotion_blocked
eligible_after_review
eligible_after_validation
promoted
rejected
```

Allowed `review_status` values:

```text
not_required
pending
in_review
passed
failed
needs_revision
```

Allowed `required_review_before_promotion` values:

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

Define which combinations are valid and invalid.

---

## 7. Promotion Gate State Machine

Define a promotion state machine.

At minimum:

```text
candidate_only
↓ validation_passed
validated_candidate
↓ review_passed
reviewed_candidate
↓ explicit_promotion_task
promoted_authority
```

Blocked transitions:

```text
candidate_only → promoted_authority
reuse_unit_candidate → promoted_authority
derived_dialogue_candidate → formal Dialogue Authority without dialogue_rewrite_review
writing_model_seed → formal Writing Authority without writing_template_review
exercise_seed → Assessment Authority without exercise_schema_review + answer key + scoring rule
assessment_seed → Assessment Authority without assessment_contract_review
```

The design scan must include a table of legal and illegal transitions.

---

## 8. Allowed and Blocked Authority Targets

Design canonical fields:

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

Define defaults by artifact layer.

Example defaults:

```json
{
  "sentence_candidate": {
    "allowed_authority_targets": ["SentenceAuthority", "ContentQueryLayer"],
    "blocked_authority_targets": ["ReadingAuthority", "DialogueAuthority", "WritingAuthority", "AssessmentAuthority", "LearningOpportunityBinding"]
  },
  "page_unit": {
    "allowed_authority_targets": ["ReadingAuthority", "ContentQueryLayer"],
    "blocked_authority_targets": ["DialogueAuthority", "WritingAuthority", "AssessmentAuthority"]
  },
  "reuse_unit_candidate": {
    "allowed_authority_targets": ["ContentQueryLayer"],
    "blocked_authority_targets": ["SentenceAuthority", "ReadingAuthority", "DialogueAuthority", "WritingAuthority", "ExerciseAuthority", "AssessmentAuthority", "LearningOpportunityBinding"]
  }
}
```

The exact defaults may be revised by evidence, but the design must preserve candidate safety.

---

## 9. Generated / Derived Content Boundary

Define explicit rules for:

```text
original RAZ text
normalized RAZ text
enriched RAZ candidate
AI-derived dialogue rewrite
AI-derived writing template
AI-derived exercise item
AI-derived assessment item
```

Required principle:

```text
Original text and generated content must never share the same authority identity.
```

Generated content must include:

```text
generated_content=true
derived_from_original_text=true or false
generation_method
generation_prompt_id or generation_task_id
review_status=pending
promotion_status=not_promoted or promotion_blocked
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

If these fields are absent, the scan must conclude:

```text
Assessment linkage remains PARTIAL or NOT_READY.
```

Assessment Authority requires a separate later task such as:

```text
RAZ-AW-S6_AssessmentSeedContract_DesignScan
```

or:

```text
ULGA-S15_AssessmentAuthorityContract_DesignScan
```

---

## 11. Field-Level Patch Matrix

Create a matrix with rows for required fields and columns:

```text
field name
field type
allowed values
required on artifact layers
optional on artifact layers
default value
blocks promotion if missing: yes/no
blocks query if missing: yes/no
blocks assessment if missing: yes/no
migration difficulty: low/medium/high
```

Fields to include at minimum:

```text
artifact_layer
source_type
source_level
source_book_id
source_page_number
source_page_unit_id
source_passage_unit_id
sentence_candidate_id
sentence_final_id
source_sentence_candidate_ids
source_sentence_final_ids
candidate_order
has_multi_sentence_unit
belongs_to_reuse_unit
reuse_unit_id
clean_text_hash
content_hash
source_traceability
authority_status
promotion_status
review_status
required_review_before_promotion
allowed_authority_targets
blocked_authority_targets
generated_content
derived_from_original_text
generation_method
generation_prompt_id
trace_confidence
```

Prefer hashes / identifiers over copying text into reports.

---

## 12. Validator Design Requirements

Design the future validator, but do not implement it.

Suggested validator name:

```text
validate_raz_authority_linkage_contract.py
```

Suggested future report:

```text
raz_authority_linkage_contract_validation.json
```

Validator should check:

```text
required fields by artifact layer
valid enum values
valid promotion transitions
candidate_only cannot be promoted
reuse_unit_candidate cannot be promoted directly
generated_content requires generation metadata
page_unit preserves ordered sentence IDs
assessment_seed cannot be marked ready without answer/scoring/error contract
allowed/blocked targets are non-conflicting
no full-text corpus files are generated as reports
```

Define expected error codes, such as:

```text
RAZ_LINK_MISSING_SOURCE_TRACEABILITY
RAZ_LINK_MISSING_PROMOTION_STATUS
RAZ_LINK_INVALID_AUTHORITY_STATUS
RAZ_LINK_ILLEGAL_PROMOTION_TRANSITION
RAZ_LINK_CANDIDATE_DIRECT_PROMOTION
RAZ_LINK_REUSE_UNIT_DIRECT_PROMOTION
RAZ_LINK_GENERATED_CONTENT_MISSING_METADATA
RAZ_LINK_TARGET_ALLOW_BLOCK_CONFLICT
RAZ_LINK_ASSESSMENT_MISSING_ANSWER_KEY
RAZ_LINK_ASSESSMENT_MISSING_SCORING_RULE
RAZ_LINK_ASSESSMENT_MISSING_ERROR_DIAGNOSIS
RAZ_LINK_PAGE_UNIT_ORDER_MISSING
RAZ_LINK_FULL_TEXT_REPORT_RISK
```

---

## 13. Builder Patch Requirements For Future Implementation

Design what a later implementation task should patch.

Do not modify builders in this task.

Identify which builder classes or scripts would likely need to emit:

```text
source_traceability
authority_status
promotion_status
review_status
allowed_authority_targets
blocked_authority_targets
generated_content
derived_from_original_text
```

For each builder, record:

```text
path
current role
future patch requirement
risk level
```

If exact builder names cannot be confirmed, mark as:

```text
unknown_pending_repo_inspection
```

---

## 14. Backward Compatibility and Migration Notes

Explain how existing artifacts can be migrated safely.

Include:

```text
no raw text regeneration required if IDs and hashes are sufficient
old artifacts without promotion_status default to not_promoted
old artifacts without generated_content default to unknown, not false, unless evidence proves original-only
old reuse units default to candidate_only
old exercise seeds default to AssessmentAuthority blocked
missing allowed_authority_targets should default to safe minimal allowlist
missing blocked_authority_targets should default to all promotion targets blocked
```

The design should avoid destructive rebuilds unless necessary.

---

## 15. Risk Analysis

Include risks:

```text
incorrect defaulting of generated_content=false
legacy artifacts treated as promotion-ready
reuse units over-promoted into Reading / Writing / Assessment
Assessment bridge built before answer/scoring/error contract
GitHub full-text corpus leakage
source trace too weak for future audit
Content Query Layer returns unsafe candidates as authority
Learning Opportunity Binding binds unreviewed content
```

For each risk, include:

```text
risk level: LOW / MEDIUM / HIGH
impact
mitigation
whether S3F resolves it fully or only designs mitigation
```

---

## 16. Recommended Next Tasks

Recommend 3-6 follow-up tasks.

Expected recommendations may include:

```text
RAZ-AW-S3G_SourceTraceabilityAndPromotionGateContractPatch_Implementation
RAZ-AW-S3H_SourceTraceabilityAndPromotionGateContractPatch_QA
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
RAZ-AW-S5_ReadingAuthorityBridge_DesignScan
RAZ-AW-S6_AssessmentSeedContract_DesignScan
ULGA-S16_ContentQueryLayer_RAZBridge_DesignScan
```

For each, include:

```text
purpose
task type
expected modified files
expected created files
risk level
whether corpus modification is allowed
```

---

## 17. Final Verdict

Final verdict must be exactly one of:

```text
CONTRACT_PATCH_DESIGN_READY
CONTRACT_PATCH_DESIGN_PARTIAL
CONTRACT_PATCH_BLOCKED_BY_MISSING_S3E
CONTRACT_PATCH_BLOCKED_BY_MISSING_ARTIFACT_INVENTORY
```

Expected likely verdict:

```text
CONTRACT_PATCH_DESIGN_READY
```

Use `CONTRACT_PATCH_DESIGN_READY` only if the document clearly defines:

```text
source_traceability object
authority / promotion / review status enums
promotion state machine
allowed / blocked authority targets
generated-content boundary
assessment dependency boundary
future validator requirements
safe migration defaults
```

---

## Completion Criteria

The task is complete only when:

```text
1. The S3F design scan document is created.
2. S3E verdict and gaps are explicitly referenced.
3. No corpus, runtime, builder, validator, or schema files are modified.
4. Source traceability contract is defined.
5. Promotion status contract is defined.
6. Promotion state machine is defined.
7. Generated / derived content boundary is defined.
8. Assessment dependency boundary is defined.
9. Future validator requirements and error codes are proposed.
10. Final verdict uses one approved S3F verdict value.
```

---

## Forbidden Claims

Do not claim:

```text
RAZ artifacts are ready for Authority promotion
Reading Authority bridge is safe to implement
Dialogue Authority bridge is safe to implement
Writing Authority bridge is safe to implement
Assessment Authority bridge is safe to implement
Learning Opportunity Binding is safe to implement
```

unless this task only means the contract design is ready, not the bridge itself.

Correct claim:

```text
The source-traceability and promotion-gate contract design is ready for a later implementation task.
```

Incorrect claim:

```text
RAZ corpus is ready for Authority promotion.
```
