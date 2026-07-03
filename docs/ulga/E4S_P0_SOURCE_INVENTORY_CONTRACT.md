# E4S P0 Source Inventory Contract Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
```

This task defines the source inventory contract only. It does not create a source manifest, builder, validator, generated JSON artifact, Reading HTML, learner-facing content, or authority promotion.

---

## 2. Task Boundary

Task:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan
```

Scope:

```text
Define the schema, enum values, status policy, allowed_use / blocked_use policy, promotion controls, and validation expectations for E4S source inventory records.
```

Allowed files:

```text
docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
tests/test_build_e4s_source_manifest.py
tests/test_validate_e4s_source_manifest.py
runtime files
generators
validators
site HTML
large generated artifacts
source corpus payloads
learner state files
promotion artifacts
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This contract defines promotion rules but performs no promotion.
```

Generated artifact policy:

```text
No generated artifacts are allowed in this task.
```

Stop condition:

```text
Stop after the contract defines record fields, enum values, invalid combinations, P0-S2 builder expectations, P0-S3 validator expectations, gates, distance vector, and next shortest step.
```

---

## 3. Contract Purpose

The Source Inventory Contract prevents source materials from being used before their role is explicit.

Every source must answer:

```text
What is this source?
Where is it?
Does it exist?
What can it be used for?
What is blocked?
Can it ever be promoted?
Which phase owns it?
Which ULGA / content authority lane receives it?
```

The future manifest target is:

```text
ulga/graph/e4s_source_manifest.json
```

The future builder task is:

```text
E4S-P0-S2_SourceManifestBuilder_Implementation
```

The future validator task is:

```text
E4S-P0-S3_SourceManifestValidator_Implementation
```

---

## 4. Source Record Schema V1

Each source record must contain these required fields:

| Field | Type | Meaning |
|---|---|---|
| `source_id` | string | Stable unique source identifier. |
| `source_family` | enum | High-level source family. |
| `source_type` | enum | Concrete source kind. |
| `authority_role` | enum | How this source may relate to authority layers. |
| `path` | string | Repo path, Drive reference label, or controlled external label. |
| `format` | enum | Physical or logical format. |
| `exists` | boolean | Whether the source exists when the manifest is built. |
| `license_status` | enum | Usage status. |
| `review_status` | enum | Review state. |
| `allowed_use` | array | Explicit allowed uses. |
| `blocked_use` | array | Explicit blocked uses. |
| `promotion_rule` | enum | Whether and how promotion can happen. |
| `target_phase` | enum | E4S phase target. |
| `target_ulga_stage` | string | ULGA / Content Authority target lane. |
| `risk_flags` | array | Known risks. |
| `notes` | array | Human-readable notes. |

Optional fields:

```text
display_name
source_owner
source_version
source_url
checksum
row_count
record_count
level_scope
theme_scope
skill_scope
source_trace_policy
promotion_blockers
deferred_to_task
last_reviewed_at
```

---

## 5. Enum Values

### 5.1 source_family

```text
governance
roadmap
grammar_profile
vocabulary_profile
frequency_profile
chunk_authority
morphology_authority
theme_authority
pattern_authority
cambridge_vocabulary
raz_wordlist
raz_reading_corpus
writing_template_corpus
parent_functional_sentence_corpus
story_dialogue_corpus
assessment_pattern_corpus
generated_content_candidate
status_artifact
google_drive_reference
github_repository
unknown
```

### 5.2 source_type

```text
policy_doc
roadmap_doc
design_scan
source_excel
source_pdf
source_text
source_json
source_jsonl
source_markdown
source_folder
source_archive
derived_json
derived_report
status_html
status_snapshot
external_reference
generated_candidate_set
unknown
```

### 5.3 authority_role

```text
primary_authority
secondary_authority
evidence_only
candidate_only
template_corpus
functional_sentence_corpus
dialogue_corpus_candidate
reading_corpus_candidate
assessment_pattern_candidate
generated_candidate
status_only
governance_only
reference_only
unknown_pending_review
```

### 5.4 format

```text
markdown
txt
xlsx
csv
json
jsonl
pdf
html
folder
archive
url_reference
repo_reference
unknown
```

### 5.5 license_status

```text
owned
licensed_for_internal_use
public_reference_only
restricted_reference_only
unknown_pending_review
not_redistributable
```

### 5.6 review_status

```text
not_reviewed
metadata_reviewed
content_sample_reviewed
schema_reviewed
validator_reviewed
promotion_reviewed
rejected
```

### 5.7 allowed_use

```text
register_in_manifest
summarize_metadata
source_trace_only
internal_reference
schema_design
validator_design
query_index_design
candidate_query
candidate_generation
reading_candidate_selection
reading_practice_candidate
writing_template_candidate
dialogue_candidate
speaking_prompt_candidate
listening_candidate
assessment_pattern_design
assessment_candidate
manual_review
promotion_review
```

### 5.8 blocked_use

```text
learner_facing_output
public_distribution
final_authority_promotion
automatic_promotion
direct_vocab_authority
direct_grammar_authority
direct_reading_authority
direct_dialogue_authority
direct_writing_authority
direct_assessment_authority
adaptive_recommendation
learner_state_update
large_scale_generation
audio_generation
image_generation
app_runtime_use
```

### 5.9 promotion_rule

```text
never_promote
candidate_only_until_review
evidence_only_never_authority
template_only_until_derivation_review
requires_manual_review
requires_validator_review
requires_promotion_task
already_governance_not_content
status_artifact_never_content
unknown_blocked
```

### 5.10 target_phase

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
E4S-P1_ReadingV1SourceGroundedPractice
E4S-P2_AssessmentPatternExpansion
E4S-P3_WritingPracticeSystem
E4S-P4_DialogueSpeakingPromptSystem
E4S-P5_ListeningPracticeSystem
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
E4S-P7_AdaptiveLearningPathIntegration
E4S-P8_FourSkillBridgeAndProductLayer
DEFERRED
UNKNOWN
```

### 5.11 risk_flags

```text
license_unknown
source_trace_required
not_for_public_distribution
candidate_not_authority
status_not_content
large_file
drive_only
github_safe
duplicate_risk
schema_unknown
level_mapping_risk
promotion_risk
learner_facing_blocked
requires_manual_review
```

---

## 6. Required Contract Rules

The future validator must enforce these rules.

### 6.1 General Rules

```text
source_id must be unique.
source_id must be stable.
allowed_use must not be empty.
blocked_use wins over allowed_use.
A value must not appear in both allowed_use and blocked_use.
No source may become final authority by implication.
```

### 6.2 License Rules

```text
license_status=unknown_pending_review must include risk_flags: license_unknown.
license_status=not_redistributable must block public_distribution and learner_facing_output.
license_status=restricted_reference_only must block public_distribution.
```

### 6.3 Generated Content Rules

```text
source_family=generated_content_candidate must use authority_role=generated_candidate.
source_family=generated_content_candidate must include risk_flags: candidate_not_authority.
source_family=generated_content_candidate must block automatic_promotion and final_authority_promotion.
```

### 6.4 Status Artifact Rules

```text
source_family=status_artifact must use authority_role=status_only.
source_family=status_artifact must use promotion_rule=status_artifact_never_content.
source_family=status_artifact must block learner_facing_output and direct_reading_authority.
```

### 6.5 RAZ WordList Rules

```text
source_family=raz_wordlist must use authority_role=evidence_only unless a later approved task changes the contract.
source_family=raz_wordlist must block direct_vocab_authority.
source_family=raz_wordlist may support reading_candidate_selection only as exposure evidence.
```

### 6.6 RAZ Reading Corpus Rules

```text
source_family=raz_reading_corpus may use authority_role=reading_corpus_candidate.
source_family=raz_reading_corpus must preserve source trace.
source_family=raz_reading_corpus must not be learner-facing during P0.
```

### 6.7 Writing / Dialogue Rules

```text
source_family=writing_template_corpus must not use direct_reading_authority.
source_family=parent_functional_sentence_corpus must not use direct_dialogue_authority.
source_family=story_dialogue_corpus must remain dialogue_corpus_candidate until reviewed.
```

---

## 7. Source Lane Mapping

| Lane | Source Families | P0 Use | Default Promotion |
|---|---|---|---|
| Governance Lane | governance, roadmap | register / guide | not content |
| Core Authority Lane | grammar_profile, vocabulary_profile, frequency_profile, chunk_authority, morphology_authority, theme_authority, pattern_authority | metadata / reference | explicit task only |
| Cambridge Lane | cambridge_vocabulary, assessment_pattern_corpus | register / design | review required |
| RAZ Evidence Lane | raz_wordlist | exposure evidence only | never direct authority |
| RAZ Reading Lane | raz_reading_corpus | register / query design | candidate only |
| Writing Lane | writing_template_corpus | register / template design | derivation review required |
| Dialogue Lane | parent_functional_sentence_corpus, story_dialogue_corpus | register / candidate design | dialogue review required |
| Generated Candidate Lane | generated_content_candidate | candidate only | strict review required |
| Status Lane | status_artifact | progress tracking only | never content |

---

## 8. Example Record Shapes

These are schema examples only. They are not the manifest.

### 8.1 RAZ WordList Evidence

```json
{
  "source_id": "RAZ_WORDLIST_A_T_001",
  "source_family": "raz_wordlist",
  "source_type": "source_text",
  "authority_role": "evidence_only",
  "path": "<to_be_resolved_by_P0_S2>",
  "format": "txt",
  "exists": true,
  "license_status": "restricted_reference_only",
  "review_status": "metadata_reviewed",
  "allowed_use": ["register_in_manifest", "summarize_metadata", "source_trace_only", "reading_candidate_selection"],
  "blocked_use": ["direct_vocab_authority", "final_authority_promotion", "automatic_promotion", "public_distribution", "learner_facing_output"],
  "promotion_rule": "evidence_only_never_authority",
  "target_phase": "E4S-P1_ReadingV1SourceGroundedPractice",
  "target_ulga_stage": "RAZ_WORDLIST_EVIDENCE",
  "risk_flags": ["source_trace_required", "candidate_not_authority", "not_for_public_distribution"],
  "notes": ["Word list supports exposure evidence only."]
}
```

### 8.2 Generated Candidate

```json
{
  "source_id": "GEN_CANDIDATE_READING_A1_001",
  "source_family": "generated_content_candidate",
  "source_type": "generated_candidate_set",
  "authority_role": "generated_candidate",
  "path": "<to_be_resolved_by_P0_S2>",
  "format": "json",
  "exists": true,
  "license_status": "owned",
  "review_status": "not_reviewed",
  "allowed_use": ["register_in_manifest", "manual_review"],
  "blocked_use": ["learner_facing_output", "final_authority_promotion", "automatic_promotion", "direct_reading_authority", "large_scale_generation"],
  "promotion_rule": "candidate_only_until_review",
  "target_phase": "DEFERRED",
  "target_ulga_stage": "GENERATED_CONTENT_CANDIDATE_REVIEW",
  "risk_flags": ["candidate_not_authority", "requires_manual_review", "promotion_risk"],
  "notes": ["Generated content is not authority."]
}
```

### 8.3 Status Artifact

```json
{
  "source_id": "STATUS_RAZ_AW_V1_001",
  "source_family": "status_artifact",
  "source_type": "status_snapshot",
  "authority_role": "status_only",
  "path": "<to_be_resolved_by_P0_S2>",
  "format": "html",
  "exists": true,
  "license_status": "owned",
  "review_status": "metadata_reviewed",
  "allowed_use": ["register_in_manifest", "summarize_metadata"],
  "blocked_use": ["learner_facing_output", "direct_reading_authority", "final_authority_promotion", "automatic_promotion", "app_runtime_use"],
  "promotion_rule": "status_artifact_never_content",
  "target_phase": "E4S-P0_SourceAuthorityAndCorpusRoadmap",
  "target_ulga_stage": "STATUS_TRACKING_ONLY",
  "risk_flags": ["status_not_content", "learner_facing_blocked"],
  "notes": ["Status artifact is not Reading practice content."]
}
```

---

## 9. P0-S2 Builder Expectations

The future builder must:

```text
1. Emit ulga/graph/e4s_source_manifest.json.
2. Emit ulga/reports/e4s_source_manifest_summary.json.
3. Preserve all required fields.
4. Use deterministic ordering by source_id.
5. Avoid learner-facing output.
6. Avoid source promotion.
```

The future builder must not:

```text
create Reading questions
create HTML
create audio
create images
create learner state
promote sources
commit large source payloads
```

---

## 10. P0-S3 Validator Expectations

The future validator must fail on:

```text
missing required field
unknown enum value
duplicate source_id
allowed_use and blocked_use conflict
status artifact marked as content authority
RAZ word list marked as direct vocabulary authority
license_status=unknown_pending_review without license_unknown risk flag
not_redistributable source without public_distribution blocked
empty allowed_use
```

The future validator may warn on:

```text
missing optional source_version
missing row_count or record_count
unknown theme_scope
unknown level_scope
unresolved path with exists=false
short notes
```

Warnings must not expand the current task.

---

## 11. Acceptance Gates for P0-S1

| Gate | Result | Evidence |
|---|---:|---|
| Required source record fields defined | PASS | Section 4 |
| Optional fields defined | PASS | Section 4 |
| Enum values defined | PASS | Section 5 |
| Required contract rules defined | PASS | Section 6 |
| Source lane mapping defined | PASS | Section 7 |
| Example record shapes included | PASS | Section 8 |
| P0-S2 builder expectations defined | PASS | Section 9 |
| P0-S3 validator expectations defined | PASS | Section 10 |
| Runtime impact avoided | PASS | Documentation only |
| Generated artifact avoided | PASS | No manifest generated |
| Promotion avoided | PASS | Contract only |

---

## 12. Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan
```

Sub-task Status:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 6 sub-tasks left
```

Remaining P0 tasks:

```text
E4S-P0-S2_SourceManifestBuilder_Implementation
E4S-P0-S3_SourceManifestValidator_Implementation
E4S-P0-S4_AuthorityMappingMatrix_DesignScan
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

---

## 13. Deferred Issues Register

```text
issue_id: E4S-P0-S1-DEFER-001
severity: high
affected_file_or_artifact: ulga/graph/e4s_source_manifest.json
classification: FUTURE_WORK
why_deferred: P0-S1 defines the contract only and may not generate the manifest.
recommended_future_task: E4S-P0-S2_SourceManifestBuilder_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P0-S1-DEFER-002
severity: high
affected_file_or_artifact: tools/validate_e4s_source_manifest.py
classification: FUTURE_WORK
why_deferred: P0-S1 defines validator expectations only and may not implement validators.
recommended_future_task: E4S-P0-S3_SourceManifestValidator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P0-S1-DEFER-003
severity: medium
affected_file_or_artifact: real source registry
classification: FUTURE_WORK
why_deferred: P0-S1 defines schema and examples but does not enumerate all real source files.
recommended_future_task: E4S-P0-S2_SourceManifestBuilder_Implementation
blocks_current_task: no
```

---

## 14. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-S2_SourceManifestBuilder_Implementation
```

Only next allowed action:

```text
Create the source manifest builder and initial deterministic manifest/report artifacts according to this contract.
```

Expected files for next task:

```text
tools/build_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
tests/test_build_e4s_source_manifest.py
```

Stop here until the operator explicitly starts E4S-P0-S2.
