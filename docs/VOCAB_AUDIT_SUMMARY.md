# VOCAB_DB_S0A Vocabulary Audit Summary

## Scope

Master summary for the deep pre-import audit of English Vocabulary Profile source data.

Inputs:

- `vocabulary/source/English Vocabulary Profile Online.xlsx`
- `docs/VOCAB_SOURCE_IMPORT_DESIGN.md`

No JSON conversion, source modification, vocabulary generation, dialogue/question/image/audio generation, or C# project creation was performed.

## Major Findings

- Canonical source sheet: `total(15696)`.
- Raw row count: 15696.
- CEFR levels present: A1, A2, B1, B2, C1, C2.
- C2 has 3807 rows and should be preserved as imported data only.
- Missing topic is the largest blocker: 8794 rows, 56.0%.
- Missing POS is smaller but still active-pool blocking: 111 rows, 0.7%.
- Duplicate words are common and expected: 3517 duplicate word groups.
- Probable exact duplicate composite-key groups: 970.
- A1-C1 all have noun as the largest POS; C2 is phrase-dominated.
- Active-ready pool counts shrink heavily when topic and POS are required, especially C1.

## Major Risks

1. Missing topic coverage:
   - C1 and C2 have more than 70% missing topic.
   - Topic-driven generation will be incomplete without recovery or mapping.
2. Duplicate semantics:
   - Word-level deduplication would destroy valid multi-sense and level-progression entries.
   - Composite duplicate handling still needs policy.
3. Phrase-heavy advanced levels:
   - B2-C2 include many phrases and phrasal verbs.
   - Downstream systems must support multi-word entries.
4. Source field ambiguity:
   - `Details` appears placeholder-like in sampled rows and should not be treated as a definition.
5. Topic taxonomy mismatch:
   - EVP vocabulary topics do not directly match existing theme profiles.
   - Mapping should be explicit and reviewable.

## Recommended Import Policy

- Import from `total(15696)` only as the canonical source.
- Use topic sheets only for reconciliation and recovery candidates.
- Preserve every raw row with deterministic row-based ids.
- Do not use `word` alone as an id.
- Import C2 rows but mark C2 inactive for active A1-C1 generation.
- Keep raw source values unchanged in normalized JSON.
- Add warning metadata for missing topic, missing POS, and composite duplicates.

## Recommended Validation Policy

Required for raw import:

- `word`
- `level`

Required for active generation eligibility:

- `word`
- `level`
- `topic`
- `part_of_speech`

Validation behavior:

- Invalid CEFR level: fail.
- Missing word: fail.
- Missing level: fail.
- Missing topic: import with warning, block from active generation.
- Missing POS: import with warning, block from active generation.
- Duplicate word: warn only.
- Duplicate composite key: warn and block affected duplicates until policy is defined.
- C2 active use: fail for A1-C1 profile generation.

## Recommended Pool Policy

| Pool | Active-ready count | Candidate policy |
| --- | ---: | --- |
| A1 | 471 | Native A1 only |
| A1_plus | 471 base | Up to 70 active-ready A2 candidates |
| A2 | 965 | Native A2 only |
| A2_plus | 965 base | Up to 144 active-ready B1 candidates |
| B1 | 1654 | Native B1 only |
| B1_plus | 1654 base | Up to 248 active-ready B2 candidates |
| B2 | 2253 | Native B2 only |
| B2_plus | 2253 base | Up to 337 active-ready C1 candidates |
| C1 | 638 | Native C1 only; no C2 candidates |

## Readiness for VOCAB_DB_S1_SourceImport_Fix

Status: Ready with policy constraints.

S1 can proceed if it implements:

- canonical import from `total(15696)`;
- deterministic ids;
- warning metadata;
- C2 imported-but-inactive status;
- missing topic/POS active blocking;
- duplicate word warning;
- composite duplicate warning and active blocking;
- no final learning content generation.

Open policy decisions before active use:

- Whether missing topics should be recovered automatically from topic sheets.
- Whether composite duplicate rows should be preserved, merged, or excluded.
- Whether `Details` should remain as raw placeholder text or be ignored in active profiles.
