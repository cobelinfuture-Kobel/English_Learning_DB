# Vocabulary Recovery Architecture Design (VOCAB_DB_S0B)

## 1. Overview of Normalized Database Fields

To implement the recovery strategies deterministically, the vocabulary importer will generate a normalized JSON dataset. The raw source attributes (e.g. `Topic`, `Part of Speech`) will remain unchanged to preserve raw auditing, while recovered values will be written to distinct fields with associated metadata.

---

## 2. Proposed Database Schema Additions

Each vocabulary record in the normalized JSON output will include these architecture fields:

```json
{
  "word": "although",
  "guideword": "BUT",
  "level": "B1",
  "raw_topic": "",
  "raw_pos": "",
  
  "topic": "communication",
  "topic_status": "recovered",
  
  "part_of_speech": "conjunction",
  "pos_status": "recovered",
  
  "duplicate_status": "canonical",
  "source_rows": [5],
  
  "recovery_method": "pos_closed_class_whitelist",
  "recovery_confidence": "high",
  "review_required": false,
  "active": true
}
```

---

## 3. Field Specifications & Status Taxonomies

### A. Topic Fields
*   `topic` (string): The resolved topic category (must match one of the 21 vocabulary topics). If unrecoverable, contains `""`.
*   `topic_status` (string enum):
    *   `natively_populated`: The topic was present in the raw sheet.
    *   `recovered`: The topic was successfully recovered by the pipeline.
    *   `unmapped`: The topic is missing and could not be recovered.

### B. Part of Speech (POS) Fields
*   `part_of_speech` (string): The resolved part of speech.
*   `pos_status` (string enum):
    *   `natively_populated`: Present in raw sheet.
    *   `recovered`: Recovered by the pipeline.
    *   `unmapped`: Missing and could not be recovered.

### C. Duplicate Status Fields
*   `duplicate_status` (string enum):
    *   `canonical`: The first occurrence of a composite key.
    *   `redundant`: Subsquent identical occurrences of a composite key.
*   `source_rows` (array of integers): Excel row numbers from which this entry was compiled (e.g. `[11314, 12623]`).

### D. Recovery Metadata Fields
*   `recovery_method` (string): Record of which pipeline step was successful:
    *   `none` (natively populated or unmapped)
    *   `topic_sheet_reconciliation` (Method A)
    *   `same_word_guideword_exact` (Method B)
    *   `unanimous_word_majority` (Method C - unanimous)
    *   `majority_word_vote` (Method C - majority)
    *   `guideword_heuristics` (Method D)
    *   `pos_closed_class_whitelist` (Method E)
*   `recovery_confidence` (string enum):
    *   `none`: Unmapped or natively populated.
    *   `high`: Reconciliations, exact matches, unanimous votes, whitelists, and direct heuristics.
    *   `medium`: Majority votes (>50% but not unanimous).
    *   `low`: Unconstrained statistical lookups.
*   `review_required` (boolean): Flag to mark entries that require human verification (e.g., conflicting majority votes or medium/low confidence recoveries).
*   `active` (boolean): Flag indicating eligibility for content generation. Must be `true` only when `duplicate_status == "canonical"`, `level != "C2"`, `topic_status != "unmapped"`, and `pos_status != "unmapped"`.
