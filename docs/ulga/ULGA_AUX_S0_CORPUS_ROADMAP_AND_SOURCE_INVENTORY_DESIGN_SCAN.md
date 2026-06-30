# ULGA-AUX-S0 Corpus Roadmap And Source Inventory Design Scan

## 1. Scope

This document is a design scan only.

It defines a read-only source inventory and a recommended corpus roadmap for ULGA-adjacent corpus work.

In scope:

- inspect current corpus-like and source-like assets in the workspace
- classify source roles
- separate authority sources from external reference corpora
- define safe intake boundaries
- define a recommended auxiliary roadmap for corpus work that supports ULGA without mutating ULGA authority

Out of scope:

- builder implementation
- OCR implementation
- content import into ULGA
- content import into Reading Authority or Dialogue Authority
- runtime, validator, scheduler, orchestrator, dashboard, or API changes
- production content generation

## 2. Preflight

Files inspected:

- `docs/ulga/ulga_roadmap.md`
- `docs/SOURCE_IMPORT_DESIGN.md`
- `docs/raz/RAZ_A_S1_PDF_SENTENCE_EXTRACTION_SPEC.md`
- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`
- `docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md`
- `grammar_profile/source/English Grammar Profile Online.xlsx`
- `vocabulary/source/English Vocabulary Profile Online.xlsx`
- `vocabulary/source/NGSL+with+SFI+(31K).xlsx`
- `input/manifest/raz_a_books_manifest.xlsx`
- `themes/theme_catalog.json`
- `themes/theme_mapping.json`
- `themes/theme_vocab_mapping.json`

Workspace observations:

- ULGA already has a mature authority-roadmap track.
- Source import rules already exist for grammar and theme normalization.
- RAZ is currently treated as `external_reference_only`, not production authority.
- The current workspace physically exposes `input/pdf/a` with 98 PDFs.
- The current workspace does not expose `input/pdf/b` through `input/pdf/f` as populated source folders, even though the historical smoke-pilot document references cross-level B-F runs.

## 3. Problem Statement

The workspace has multiple source families, but they do not yet sit inside one explicit corpus roadmap.

Today the project has:

- authority-bearing source files
- normalized authority artifacts
- external reference corpus experiments
- pilot outputs and reports

What is missing is a single design-level answer to:

```text
Which source assets are authoritative,
which are benchmarking-only,
which are future candidate corpora,
and in what order should they be expanded without contaminating ULGA authority?
```

Without that separation, four risks appear:

- external reference text may be mistaken for reusable authority content
- future corpus builders may bypass validation or copyright-role boundaries
- roadmap planning may assume source coverage that does not exist in the current workspace
- multiple corpus efforts may diverge in naming, status, and intake policy

## 4. Inventory Principles

Source inventory should follow these principles:

- authority first
- reference corpus second
- validation before ingestion
- static artifacts before adaptive usage
- explicit source-role metadata for every corpus family
- no direct promotion from extracted reference text into learner-facing authority

Recommended source-role classes:

- `authority_source`
- `normalized_authority_artifact`
- `external_reference_corpus`
- `experimental_pilot_output`
- `future_candidate_corpus`
- `blocked_or_missing_source`

## 5. Current Source Inventory

### 5.1 Authority Sources

| Source | Current Role | Status | Notes |
|---|---|---|---|
| `grammar_profile/source/English Grammar Profile Online.xlsx` | `authority_source` | present | Primary grammar authority source. |
| `vocabulary/source/English Vocabulary Profile Online.xlsx` | `authority_source` | present | Vocabulary authority source. |
| `vocabulary/source/NGSL+with+SFI+(31K).xlsx` | `authority_source` | present | Frequency and vocabulary support source. |
| `input/manifest/raz_a_books_manifest.xlsx` | `authority_source` for manifest only | present | Manifest authority for the RAZ reference pipeline, not content authority. |

### 5.2 Normalized Authority Artifacts

| Artifact Family | Current Role | Status | Notes |
|---|---|---|---|
| `grammar_profile/json/grammar_profile.json` | `normalized_authority_artifact` | present | Canonical normalized grammar records. |
| `vocabulary/json/vocabulary.json` | `normalized_authority_artifact` | present | Canonical vocabulary authority. |
| `themes/theme_mapping.json` | `normalized_authority_artifact` | present | Normalized theme mapping artifact. |
| `themes/theme_catalog.json` | `normalized_authority_artifact` | present | Theme authority catalog. |
| `themes/theme_vocab_mapping.json` | `normalized_authority_artifact` | present | Theme-to-vocabulary support artifact. |
| `level_profiles/*.json` | `normalized_authority_artifact` | present | Level constraints and planning support. |
| `chunk_profile/json/*.json` | `normalized_authority_artifact` | present | Chunk safe-layer and support artifacts. |
| `ulga/graph/*.json` | `normalized_authority_artifact` | present | Derived ULGA authority and planning artifacts. |

### 5.3 External Reference Corpus

| Source | Current Role | Status | Notes |
|---|---|---|---|
| `input/pdf/a/*.pdf` | `external_reference_corpus` | present | 98 PDFs currently visible in workspace. |
| `docs/raz/RAZ_A_S1_PDF_SENTENCE_EXTRACTION_SPEC.md` | policy/spec | present | Declares RAZ as `external_reference_only`. |
| `output/excel/raz_a_reference_sentences.xlsx` | `experimental_pilot_output` | present | Reference-only extraction output. |
| `output/json/pages_raw.json` | `experimental_pilot_output` | present | Raw extraction artifact. |
| `output/json/sentences_v01.json` | `experimental_pilot_output` | present | Sentence-level extraction artifact. |
| `output/json/reference_duplicate_groups.json` | `experimental_pilot_output` | present | Reference duplicate grouping output. |
| `output/json/extraction_report.json` | `experimental_pilot_output` | present | Extraction summary artifact. |

### 5.4 Blocked Or Missing Inventory

| Expected Source | Current Role | Status | Risk |
|---|---|---|---|
| `input/pdf/b/*.pdf` | `future_candidate_corpus` | not currently present in workspace | Cross-level roadmap cannot assume local availability. |
| `input/pdf/c/*.pdf` | `future_candidate_corpus` | not currently present in workspace | Level-aware reference testing is blocked locally. |
| `input/pdf/d/*.pdf` | `future_candidate_corpus` | not currently present in workspace | Higher-level benchmark coverage not reproducible from current files. |
| `input/pdf/e/*.pdf` | `future_candidate_corpus` | not currently present in workspace | OCR/no-text-layer planning cannot be rechecked locally. |
| `input/pdf/f/*.pdf` | `future_candidate_corpus` | not currently present in workspace | Same gap as E. |
| dialogue-native corpus | `future_candidate_corpus` | not found | Dialogue Authority lacks an external benchmark corpus. |
| assessment-native corpus | `future_candidate_corpus` | not found | Assessment benchmarking remains future work. |

## 6. Source Role Policy

Recommended corpus policy:

### Authority sources

- may feed normalization pipelines
- may produce canonical authority artifacts
- must retain source trace

### External reference corpora

- may support calibration, benchmarking, difficulty comparison, duplication analysis, and pattern discovery
- must not directly populate learner-facing authority
- must not bypass validation or copyright-role flags

### Experimental pilot outputs

- are audit or benchmark artifacts
- may be deleted, rerun, or replaced
- must never be confused with production authority truth

### Missing or blocked sources

- must be represented explicitly in inventory
- must block roadmap claims that depend on them

## 7. Corpus Families

Recommended corpus families for this workspace:

### Family A: Authority Seed Sources

Purpose:

- define core truth for vocabulary, grammar, themes, chunks, and level structures

Current members:

- EGP workbook
- EVP workbook
- NGSL frequency workbook
- theme source derivatives

Policy:

- first-class
- authority-bearing
- validation-gated

### Family B: ULGA Derived Authority Corpus

Purpose:

- expose graph-addressable teaching units, dependencies, opportunities, and ranking artifacts

Current members:

- `ulga/graph/*.json`
- `ulga/reports/*.json`

Policy:

- derived from authority sources
- read-only for downstream consumers
- not a raw content corpus

### Family C: External Reading Benchmark Corpus

Purpose:

- benchmark sentence length, reading density, duplication patterns, directionality noise, and early-reader structure

Current members:

- RAZ manifest
- RAZ A-level PDF set visible in workspace
- RAZ extraction outputs

Policy:

- `external_reference_only`
- no direct content reuse

### Family D: Future Dialogue Benchmark Corpus

Purpose:

- benchmark turn count, role balance, function tagging, chunk repetition, and naturalness for Dialogue Authority

Current members:

- none found

Policy:

- blocked pending source acquisition and policy definition

### Family E: Future Assessment Benchmark Corpus

Purpose:

- benchmark question forms, distractor structure, answerability, and skill coverage

Current members:

- none found

Policy:

- blocked pending source acquisition and rights-safe intake policy

## 8. Current Gaps

Primary gaps:

- no unified inventory file exists today
- RAZ cross-level availability in documentation does not match the current local workspace inventory
- there is no dialogue-specific external benchmark corpus
- there is no assessment-specific external benchmark corpus
- there is no shared corpus-status enum across authority, benchmark, and pilot artifacts

Secondary gaps:

- no manifest-driven source registry across all corpus families
- no checksum or fingerprint policy is visible for repeated corpus intake
- no explicit restart-safe pipeline contract is documented for corpus extraction jobs

## 9. Integration Risks

System integration risks:

- config drift if corpus roles are encoded differently across builders, reports, and future dashboards
- dashboard confusion if benchmark outputs are shown beside authority outputs without role labels
- scheduler risk if future extraction jobs auto-run and overwrite prior benchmark artifacts
- orchestrator risk if benchmark corpora are treated as approved content candidates
- API risk if source inventory status is inferred from folder names instead of explicit metadata

Real-environment risks:

- source files may disappear or move between runs, making the inventory stale
- repeated extraction may create inconsistent outputs without stable corpus fingerprints
- timeout during PDF extraction may leave partial output sets that appear complete
- process restart may orphan report snapshots or mixed-version outputs
- empty or malformed manifest rows may silently reduce corpus coverage
- image-only or malformed PDFs may skew roadmap assumptions if counted as valid coverage

## 10. Recommended Inventory Contract

Recommended future artifact:

```text
docs/ulga/ULGA_AUX_S0_CORPUS_SOURCE_INVENTORY.json
```

Recommended record shape:

```json
{
  "source_id": "RAZ_A_PDF_SET",
  "source_family": "external_reading_benchmark",
  "source_role": "external_reference_corpus",
  "path": "input/pdf/a",
  "status": "present",
  "format": "pdf",
  "scope": {
    "levels": ["A"],
    "content_modes": ["reading"]
  },
  "direct_use_allowed": false,
  "authority_import_allowed": false,
  "manifest_ref": "input/manifest/raz_a_books_manifest.xlsx",
  "notes": []
}
```

Recommended required fields:

- `source_id`
- `source_family`
- `source_role`
- `path`
- `status`
- `format`
- `direct_use_allowed`
- `authority_import_allowed`

Recommended status enum:

- `present`
- `present_with_warnings`
- `missing`
- `blocked`
- `deprecated`

## 11. Recommended Roadmap

Recommended auxiliary roadmap:

```text
ULGA-AUX-S0_CorpusRoadmapAndSourceInventory_DesignScan
ULGA-AUX-S1_GlobalSourceInventory_Implementation
ULGA-AUX-S2_RAZCorpusRoleAndManifestHardening
ULGA-AUX-S3_RAZLevelAwareReferencePolicy_DesignScan
ULGA-AUX-S4_DialogueBenchmarkCorpusSourceScan
ULGA-AUX-S5_AssessmentBenchmarkCorpusSourceScan
ULGA-AUX-S6_CorpusFingerprintAndIdempotentIntakePolicy
ULGA-AUX-S7_CorpusDashboardStatusContract
```

Recommended execution notes:

1. Build the inventory registry before expanding corpus automation.
2. Harden RAZ manifest and source-role metadata before any wider extraction reruns.
3. Do not start Dialogue or Assessment benchmark design until source availability and rights constraints are explicit.
4. Add fingerprint and idempotency policy before allowing scheduled extraction jobs.

## 12. Minimal-Change Recommendation

The minimal-change path is:

- keep current authority pipelines unchanged
- keep RAZ as `external_reference_only`
- add one inventory design/implementation track outside core ULGA runtime
- use explicit source-role metadata rather than broad refactors

This preserves the current system boundary:

```text
authority truth stays in normalized authority artifacts
benchmark corpora stay outside learner-facing authority
```

## 13. Acceptance Criteria

This design scan is complete when it:

- lists current source families visible in the workspace
- distinguishes authority sources from benchmark corpora
- identifies missing or blocked corpus families
- defines inventory roles and statuses
- defines a safe roadmap for future corpus work
- preserves current static/offline safety boundaries
- does not promote benchmark text into authority content

Recommended next task:

```text
ULGA-AUX-S1_GlobalSourceInventory_Implementation
```
