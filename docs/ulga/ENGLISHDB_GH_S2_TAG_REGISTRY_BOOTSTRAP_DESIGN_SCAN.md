# EnglishDB-GH-S2 Tag Registry Bootstrap Design Scan

## 1. Preflight

Task:

```text
EnglishDB-GH-S2_TagRegistryBootstrap_DesignScan
```

Scope:

```text
DESIGN SCAN + BOOTSTRAP DRAFT ARTIFACTS
NO RAW RAZ JSON MUTATION
NO RAZ OUTPUT INGESTION
NO AUTHORITY PROMOTION
NO VALIDATOR / BUILDER / TEST MUTATION
NO GENERATED READING / DIALOGUE / EXERCISE CONTENT
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Files inspected conceptually before this design scan:

```text
.gitignore
README.md
docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md
docs/raz/RAZ_S6C_SEED_QUERY_AUTHORITY_LINKAGE_DESIGN_SCAN.md
docs/ulga/ULGA_AUX_S0_CORPUS_ROADMAP_AND_SOURCE_INVENTORY_DESIGN_SCAN.md
docs/ulga/ULGA_AUX_S1_GLOBAL_SOURCE_INVENTORY_IMPLEMENTATION.md
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
ulga/reports/corpus_source_inventory_summary.json
tag_registry/.gitkeep
schemas/tags/.gitkeep
```

Files created by this bootstrap design task:

```text
docs/ulga/ENGLISHDB_GH_S2_TAG_REGISTRY_BOOTSTRAP_DESIGN_SCAN.md
tag_registry/tag_registry.bootstrap_draft.json
tag_registry/content_unit_type_registry.bootstrap_draft.json
tag_registry/reusability_tags_registry.bootstrap_draft.json
tag_registry/tag_alias_candidates.bootstrap_draft.json
```

Risk level:

```text
Low
```

Reason:

```text
The task creates draft registry artifacts only. It does not modify raw data, authority graphs, builders, validators, tests, or generated corpus outputs.
```

---

## 2. Current State

### 2.1 Repository and safety state

The repository has moved beyond an empty shell and now contains authority docs, source inventory docs, profile tools, validators, and reports.

Current local/generated/raw folders remain intentionally excluded from Git:

```text
input/
output/
scratch/
raz_output_jsons/
```

Large generated graph artifacts are also excluded.

### 2.2 Tag registry gap

The repository already contains these paths:

```text
tag_registry/
schemas/tags/
```

But both are bootstrap placeholders only. There is not yet a machine-readable tag registry with canonical tag domains, lifecycle status, alias rules, or authority-boundary rules.

Therefore, RAZ tag audit cannot safely classify tags as formal authority tags yet.

Current status:

```text
formal tag registry: ABSENT
bootstrap draft registry: CREATED_BY_THIS_TASK
RAZ tag usage: PRESENT
RAZ formal authority linkage: NOT YET
```

---

## 3. Evidence Summary

### 3.1 RAZ seed layer already exposes tag-like fields

RAZ S6 defines queryable fields across these domains:

```text
source_tags
content_unit_tags
theme_tags
linguistic_tags
pedagogical_tags
reuse_tags
```

Current queryable RAZ A-F universe is already available as enriched candidate units:

```text
total_queryable_units: 14422
sentence_enriched: 7487
page_unit_enriched: 4925
reuse_unit_enriched: 2010
```

However, all records remain candidate seeds, not promoted content authority.

### 3.2 RAZ tag authority linkage is explicitly incomplete

Known limitations:

```text
RAZ grammar tags are rule-based.
RAZ vocabulary tags are not EVP-linked.
RAZ grammar tags are not EGP-linked.
RAZ CEFR is not authority-linked.
RAZ theme is mapped but not explicitly linked to Theme Authority nodes.
RAZ pattern tags are rule-based and not linked to Sentence Pattern Authority nodes.
```

Therefore, S2 must separate:

```text
queryable tag-like metadata
from
formal authority tag evidence
```

### 3.3 Content Authority design already needs shared lifecycle and linkage metadata

S11 defines a future shared content-item contract for Reading / Dialogue. Relevant common fields include:

```text
content_type
level
theme_refs
linked_opportunity
focus_vocabulary_refs
grammar_refs
pattern_refs
chunk_refs
source_type
validation_status
validator_notes
```

This implies the tag registry must support lifecycle and linkage distinctions, not just flat labels.

---

## 4. Bootstrap Registry Design Goals

S2 should create a draft registry that can support later RAZ-AW tag alignment without pretending to be final authority.

Required design goals:

```text
1. Define tag domains.
2. Define tag classification types.
3. Separate raw extraction fields from authority tags.
4. Separate candidate tags from formal authority tags.
5. Preserve alias candidates without auto-merging them.
6. Define review status for every draft tag.
7. Block RAZ candidate tags from being promoted directly into Content Authority.
```

---

## 5. Tag Classification Model

Every tag-like entry should eventually carry these fields:

```json
{
  "tag_id": "string",
  "canonical_label": "string",
  "domain": "string",
  "classification": "formal_authority_tag | candidate_tag | alias_candidate | raw_extraction_field | query_hint | reuse_hint | lifecycle_status | source_role",
  "authority_status": "formal | candidate_only | not_authority",
  "review_status": "accepted | pending | blocked | deprecated",
  "source_refs": [],
  "validator_required": true
}
```

### 5.1 Classification meanings

| Classification | Meaning | May be treated as authority? |
|---|---|---:|
| `formal_authority_tag` | Canonical tag backed by an authority source or validated authority node | Yes |
| `candidate_tag` | Useful proposed tag that still needs review or linkage | No |
| `alias_candidate` | Proposed synonym or spelling variant of another tag | No |
| `raw_extraction_field` | Source trace or extraction metadata | No |
| `query_hint` | Soft filter for retrieval | No |
| `reuse_hint` | Candidate reuse/generation hint | No |
| `lifecycle_status` | Candidate/approved/blocked/deprecated state | Contextual |
| `source_role` | Source inventory role such as authority_source or external_reference_corpus | Contextual |

---

## 6. Bootstrap Tag Domains

S2 should begin with these domains.

### 6.1 `source_role`

Purpose:

```text
Classifies source families and prevents source-role contamination.
```

Initial values come from AUX source inventory policy:

```text
authority_source
normalized_authority_artifact
external_reference_corpus
experimental_pilot_output
future_candidate_corpus
blocked_or_missing_source
```

### 6.2 `content_unit_type`

Purpose:

```text
Classifies the unit shape of reading/content evidence.
```

Initial draft values:

```text
sentence
page_unit
reuse_unit
multi_sentence_unit
heading
section_heading
page_passage
paragraph_unit
phrase_fragment
caption_unit
diagram_label
fact_box
table_cell
timeline_marker
procedure_step
quote_unit
glossary_entry
activity_prompt
review_question
direct_speech
question_sentence
imperative_sentence
```

### 6.3 `reusability_tag`

Purpose:

```text
Classifies future reusable seed potential without generating content.
```

Initial draft values:

```text
future_unknown_use
exercise_seed
grammar_pattern_seed
vocabulary_exposure_seed
listening_audio_seed
assessment_seed
comprehension_question_seed
retelling_seed
sequencing_seed
short_reading_seed
writing_model_seed
picture_prompt_seed
dialogue_rewrite_seed
```

### 6.4 `pedagogical_tag`

Purpose:

```text
Classifies skill and question-type hints for future generator/query layers.
```

Initial draft values:

```text
reading
vocabulary
grammar
listening
comprehension
retelling
speaking
reading_comprehension
fill_blank
word_ordering
dictation
listening_choice
retelling_prompt
sentence_ordering
short_answer
speaking_response
```

### 6.5 `authority_linkage_status`

Purpose:

```text
Makes explicit whether a tag is formally linked to ULGA authority.
```

Initial draft values:

```text
linked_to_authority
candidate_unlinked
rule_based_unlinked
mapped_but_unverified
blocked_from_authority
not_applicable
```

### 6.6 `content_lifecycle_status`

Purpose:

```text
Controls content readiness and prevents candidate text from being treated as approved authority.
```

Initial values:

```text
candidate
approved
blocked
deprecated
```

---

## 7. RAZ Boundary Rules

RAZ tag audit must obey these rules:

```text
1. RAZ raw extraction fields are source evidence, not authority tags.
2. RAZ S6 tags are candidate/query metadata unless linked to authority refs.
3. RAZ grammar/vocabulary/pattern tags remain soft filters until EGP/EVP/Pattern linkage exists.
4. RAZ reusability tags are reuse hints, not generation approval.
5. RAZ page/reuse units may become candidate content units, but not approved Content Authority without validation.
6. RAZ raw_A-W should not be imported until raw inventory and copyright-role boundaries are explicit.
```

---

## 8. Draft Artifacts Created

This task creates four bootstrap draft JSON files:

```text
tag_registry/tag_registry.bootstrap_draft.json
tag_registry/content_unit_type_registry.bootstrap_draft.json
tag_registry/reusability_tags_registry.bootstrap_draft.json
tag_registry/tag_alias_candidates.bootstrap_draft.json
```

They are intentionally marked:

```text
registry_status: bootstrap_draft
authority_status: candidate_only
promotion_status: not_promoted
```

---

## 9. Readiness Result

```text
EnglishDB-GH-S2 verdict: PASS_WITH_WARNINGS
```

Warnings:

```text
1. Bootstrap drafts are not formal authority.
2. RAZ A-W raw JSON is still not in GitHub.
3. Formal EGP/EVP/Pattern linkage for RAZ tags is not implemented.
4. Some future content-unit types are anticipated from higher-level RAZ patterns but not validated against A-W raw yet.
```

---

## 10. Recommended Next Task

```text
RAZ-AW-S0_TagAuthorityAlignmentAudit_DesignScan
```

Scope for the next task:

```text
READ ONLY
NO RAW MUTATION
NO AUTHORITY PROMOTION
USE tag_registry bootstrap draft as candidate registry
SCAN raw_A-W only if explicitly provided or mounted
OUTPUT alignment categories:
  matched_existing_tag
  matched_existing_tag_by_alias
  candidate_new_tag
  no_tag_needed_context_only
```

Acceptance criteria for the next task:

```text
1. Distinguish existing bootstrap tags from new candidates.
2. Preserve RAZ source fields as source evidence, not formal tags.
3. Report missing formal authority links separately from raw tag coverage.
4. Produce candidate_new_tags.json with review_status=pending.
5. Do not promote any RAZ record into Reading / Dialogue Content Authority.
```
