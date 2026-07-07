# R7-M44 Grammar Node EGP Mapping Data Readiness and Policy Scan

## Task

```text
R7-M44_GrammarNodeEGPMappingDataReadinessAndPolicyScan
```

## Predecessor

```text
R7-M35_TO_R7-M43 = PASS_CI_SYNCED_AND_MERGED
```

## Purpose

Prepare the grammar node to EGP mapping stage without making unsupported authority claims.

This scan checks whether existing grammar nodes already carry deterministic EGP evidence references and defines how those references may be normalized into `egp_refs` for the pipeline.

## Findings

### 1. Canonical Grammar Node Source

The static GrammarSkillTree validator reads nodes from:

```text
ulga/grammar/grammar_nodes.json
```

The R7-M36 alignment builder originally read:

```text
ulga/graph/grammar_nodes.json
```

That graph path is not the canonical static GrammarSkillTree node source. R7-M44 therefore requires the alignment builder to use `ulga/grammar/grammar_nodes.json` as the canonical source and treat `ulga/graph/grammar_nodes.json` only as a fallback.

### 2. Existing Evidence Field

Some grammar nodes already contain deterministic evidence references under:

```text
egp_evidence_refs
```

Those references use a stable source format such as:

```text
EGP_SOURCE_XLSX::Data!A1151:H1151::id=<egp_row_id>
```

R7-M44 allows deterministic extraction of `<egp_row_id>` from existing `egp_evidence_refs`.

This is not new AI mapping and does not select new evidence.

### 3. Allowed Normalization

Allowed:

```text
egp_evidence_refs -> extracted egp_row_id -> resolved normalized EGP row
```

Not allowed in this task:

```text
AI chooses a new EGP row for an unmapped grammar node
operator-unreviewed fuzzy matching becomes MATCH
generated candidate mapping becomes authority
```

## Mapping Status Policy

| Condition | Status |
|---|---|
| All extracted IDs resolve to EGP rows | `EGP_MAPPED` / `MATCH` |
| Some extracted IDs resolve and some do not | `EGP_PARTIAL_MATCH` / `CONFLICT_REVIEW_REQUIRED` |
| Evidence refs exist but none resolve | `UNRESOLVED_EGP_REFS` / `CONFLICT_REVIEW_REQUIRED` |
| No evidence refs and no explicit exception | `UNMAPPED` |
| Explicit system-required outside EGP | `NOT_IN_EGP_BUT_SYSTEM_REQUIRED` |

## Required Patch

```text
R7-M44A_SourcePathAndEvidenceRefNormalizationPatch
```

Patch requirements:

- R7-M36 alignment builder must read canonical static nodes from `ulga/grammar/grammar_nodes.json`.
- It must extract EGP row IDs from both `egp_refs` and `egp_evidence_refs`.
- It must normalize `A1_PLUS`, `A2_PLUS`, `B1_PLUS` into `A1+`, `A2+`, `B1+` for coverage matrix compatibility.
- It must report mapped / uncovered counts by EGP level in alignment table summary.
- Coverage matrix builder must use alignment summary counts rather than reconstructing counts from one grammar record per level.

## Scope Safety

```text
NO_RUNTIME_IMPLEMENTATION = true
NO_PRACTICEBANK_GENERATION = true
NO_LEARNER_STATE_WRITE = true
NO_AI_MAPPING_PROMOTION = true
NO_NEW_EVIDENCE_SELECTION = true
```

## NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M44A_SourcePathAndEvidenceRefNormalizationPatch
```
