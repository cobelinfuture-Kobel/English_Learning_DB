# RAZ-AW-S3E Authority Linkage Readiness Design Scan Prompt

## Task ID

```text
RAZ-AW-S3E_AuthorityLinkageReadinessDesignScan
```

## Execution Mode

```text
DesignScan only.
```

## Hard Constraints

```text
Do not implement runtime code.
Do not modify generated corpus data.
Do not modify raw or derived RAZ corpus artifacts.
Do not promote any RAZ sentence, page unit, passage unit, reuse unit, derived dialogue, writing seed, exercise seed, or assessment seed into formal Authority.
Do not create production validators unless the design scan explicitly recommends them as future work.
Do not delete or rewrite existing RAZ-derived artifacts.
Do not push raw / full-text-bearing derived corpus files to GitHub.
```

This task is GitHub-safe only if it creates or updates documentation, schemas, validator plans, sanitized summaries, aggregate QA reports, or prompt/design files. It must not add full RAZ raw text, enriched corpus dumps, or local `raz_output_jsons/derived/Level_*` data.

---

## Goal

Create a design scan document that evaluates whether the current RAZ A-W / available RAZ multi-level extracted corpus structure is ready to link into future Content Authority layers:

```text
Reading Authority
Dialogue Authority
Writing Authority
Exercise / Assessment Authority
Content Query Layer
Learning Opportunity Binding
```

The purpose is not to build the bridge yet. The purpose is to determine whether the existing artifacts have enough source traceability, candidate-state separation, promotion boundaries, and linkage fields to support later bridge design.

---

## Important Context

The RAZ extraction pipeline must preserve both:

```text
1. sentence-level authority candidates
2. multi-sentence page / passage / reuse units
```

Current design principle:

```text
Sentence layer
= one sentence per record, used for grammar / vocabulary / pattern / theme tagging.

Page / passage unit layer
= preserves multi-sentence context, book/page sequence, and reading continuity.

Reuse unit layer
= marks future reusable content potential.

Derived dialogue / writing / exercise / assessment content
= candidate_only until a later dedicated promotion task.
```

The scan must explicitly distinguish:

```text
original RAZ text
normalized text
enriched candidates
multi-sentence page units
reuse candidates
derived/generated candidates
formal Authority records
```

Generated or rewritten content must never be mixed with original RAZ authority candidates without explicit `generated_content`, `derived_from_original_text`, `review_status`, and `promotion_status` fields.

---

## Repository Scope To Inspect

Inspect current repository artifacts related to:

```text
RAZ A-W or currently available RAZ levels
sentence candidates
normalized / enriched sentence outputs
page units
passage units
reuse unit candidates
derived candidate artifacts
clean summaries
RAZ reports
ULGA / Content Authority roadmap docs
Reading / Dialogue / Writing / Assessment authority design docs
validation summaries, if present
```

Use the repository state as source of truth. Do not assume local-only corpus files are present on GitHub.

---

## Required Analysis

### 1. Current Artifact Inventory

List current RAZ-derived artifacts relevant to authority linkage.

Group them by:

```text
sentence-level artifacts
page / passage unit artifacts
reuse unit artifacts
derived candidate artifacts
summary / validation reports
design / roadmap docs
```

For each artifact, identify:

```text
path
role
source level coverage
raw / normalized / enriched / candidate / final / report status
whether it is safe for authority linkage
whether it is safe for GitHub storage
```

If an expected artifact is not in GitHub, mark it as:

```text
not_present_in_github
```

Do not infer that local full corpus data exists unless a checked-in summary or manifest proves it.

---

### 2. Linkage Readiness Matrix

Create a matrix with these rows:

```text
Reading Authority
Dialogue Authority
Writing Authority
Exercise Authority
Assessment Authority
Content Query Layer
Learning Opportunity Binding
```

For each row, evaluate:

```text
required fields
currently available fields
missing fields
promotion risk
readiness status
```

Use only these readiness statuses:

```text
READY
PARTIAL
NOT_READY
BLOCKED
UNKNOWN
```

Definitions:

```text
READY
= required source trace, candidate boundary, and linkage fields are already present.

PARTIAL
= enough structure exists for design continuation, but contract patch is required.

NOT_READY
= required artifacts or fields are missing.

BLOCKED
= bridge design would be unsafe or misleading until a prerequisite task is completed.

UNKNOWN
= repository state does not provide enough evidence.
```

---

### 3. Required Linkage Field Contract

Evaluate whether current artifacts contain, or should contain, the following minimum fields:

```text
source_type
source_level
book_id
page_number
page_unit_id
passage_unit_id
sentence_candidate_id
sentence_final_id
source_sentence_candidate_ids
clean_text
sentence_count
candidate_order
has_multi_sentence_unit
belongs_to_reuse_unit
reuse_unit_id
reusability_tags
derivation_potential
authority_status
promotion_status
review_status
generated_content
derived_from_original_text
source_traceability
allowed_authority_targets
blocked_authority_targets
required_review_before_promotion
```

For each field, classify:

```text
present
missing
partially_present
not_applicable
unknown
```

Also identify which future Authority layer depends on each field.

---

### 4. Authority Boundary Rules

Define strict future rules for what may and may not happen.

Required boundary rules:

```text
RAZ original sentence can become sentence authority only after sentence-level validation.
RAZ original page / passage unit may become Reading / Passage Authority only after page-unit review.
RAZ reuse_unit_candidates must remain candidate_only.
RAZ-derived dialogue rewrites must be marked generated or derived and cannot be mixed with original RAZ sentence authority.
Writing model seeds are not Writing Authority until template extraction and review are completed.
Exercise / Assessment seeds are not Assessment Authority until question schema, answer key, scoring rule, and error tagging contract exist.
Generated content must remain candidate_only with review_status=pending unless explicitly promoted by a later authority promotion task.
Any bridge implementation must reject candidate_only records unless the target layer explicitly accepts candidates.
```

---

### 5. Risk Analysis

Identify risks including:

```text
accidental promotion of candidate_only units
mixing original RAZ text with generated/rewritten content
losing page order or sentence order
losing source traceability
over-linking RAZ units to Dialogue / Writing / Assessment too early
missing fields that would block ULGA-S16 Content Query
missing fields that would block ULGA-S17 Learning Opportunity Binding
assessment linkage without question / answer / error / remediation tagging
GitHub storage risk from accidentally adding full-text-bearing corpus dumps
```

For each risk, provide:

```text
risk level: LOW / MEDIUM / HIGH
impact
recommended mitigation
```

---

### 6. Assessment / Error Diagnosis Linkage Note

Because future Assessment Authority must feed Learner State, inspect whether RAZ-derived exercise candidates have enough structure to support:

```text
question_type
skill_area
concept_tags
cognitive_skill
correct_answer
answer_key
student_answer, if applicable later
is_correct, if applicable later
error_type
error_detail
remediation_tag
scoring_rule
```

If these are missing, mark Assessment linkage as:

```text
PARTIAL
```

or:

```text
NOT_READY
```

Do not mark Assessment linkage as READY unless question schema, answer key, scoring rule, and error-diagnosis contract are already present.

---

### 7. Recommended Next Tasks

Recommend the next 3-6 tasks after this design scan.

Candidate task names:

```text
RAZ-AW-S3F_SourceTraceabilityContractPatch_DesignScan
RAZ-AW-S3G_ReuseUnitPromotionGateValidator_Implementation
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
RAZ-AW-S5_ReadingAuthorityBridge_DesignScan
RAZ-AW-S6_AssessmentSeedContract_DesignScan
ULGA-S16_ContentQueryLayer_RAZBridge_DesignScan
```

For each recommended task, include:

```text
purpose
expected files to inspect
expected files to create or modify
whether it is DesignScan, Implementation, QA, or Closeout
risk level
```

---

## Required Output

Create one markdown document:

```text
docs/raz/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN.md
```

If `docs/raz` does not exist, use the closest existing RAZ documentation directory and explain the chosen path in the Preflight section.

The document must include:

```text
Preflight
Files inspected
Current artifact inventory
Linkage readiness matrix
Required linkage field contract
Authority boundary rules
Risk analysis
Assessment linkage note
Recommended next tasks
Final readiness verdict
```

---

## Final Readiness Verdict

The final verdict must be exactly one of:

```text
READY_FOR_BRIDGE_DESIGN
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
NOT_READY_REQUIRES_STRUCTURE_PATCH
BLOCKED_BY_MISSING_ARTIFACTS
```

Expected likely verdict, unless repository evidence proves otherwise:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

Reason:

```text
The multi-sentence / reuse-unit direction is structurally correct, but authority linkage usually requires explicit source trace, promotion gates, generated-content flags, target allow/block fields, and review-status fields before bridge implementation is safe.
```

---

## Completion Criteria

The task is complete only when:

```text
1. The design scan document is created.
2. The scan lists inspected files and missing expected artifacts.
3. The readiness matrix covers all target Authority layers.
4. Candidate-only and promotion boundary rules are explicit.
5. Assessment linkage is not over-claimed.
6. No raw / derived full corpus files are added or modified.
7. Final verdict uses one of the approved verdict values.
```

---

## Forbidden Claims

Do not claim:

```text
RAZ corpus is ready for Authority promotion
Assessment Authority is ready
Dialogue Authority is ready
Writing Authority is ready
Learning Opportunity Binding is ready
```

unless the inspected repository artifacts prove the required contracts are present.

Do not use optimistic language to hide missing source-trace or promotion-gate fields.
