# Vocabulary Duplicate Recovery Policy (VOCAB_DB_S0B)

## 1. Overview of Duplicate Classes

The English Vocabulary Profile (EVP) total sheet contains duplicate records. To avoid bloating the active pool while preserving data integrity, we classify duplicate rows into three distinct categories:

### Class A: Legitimate Multi-Sense Entries (Preserve)
*   **Description:** Repeated words that have different guidewords, topics, or parts of speech (representing different semantic senses).
*   **Action:** **Preserve all.** These must be imported as separate database records because they represent distinct learning targets (e.g. `bank` as "river side" vs `bank` as "financial institution").

### Class B: Level Progression Entries (Preserve)
*   **Description:** The same word sense appearing at multiple CEFR levels (representing semantic progression).
*   **Action:** **Preserve all.** These represent the learning path of the word and should not be collapsed (e.g., a word introduced at A2 that takes on a more refined usage at B2).

### Class C: Probable Exact Duplicates (Merge)
*   **Description:** Duplicate rows that have the exact same composite key:
    `word + guideword + level + part_of_speech + topic`
*   **Analysis:** An audit of all **970 duplicate groups** (covering 2,044 raw rows) reveals that **100% of these groups have identical Details columns**.
*   **Findings:** There is absolutely no semantic difference between the duplicate rows. They are literal sheet-level redundant rows resulting from manual collation errors in the source spreadsheet.
*   **Action:** **Merge into a single canonical entry.**

---

## 2. Duplicate Resolution Policy

The importer will implement the following policy for duplicate rows:

1.  **Deduplicate Composite Keys:** For each unique composite key:
    `word_norm + guide_norm + level_norm + pos_norm + topic_norm`
    *   If multiple rows in `total(15696)` share the exact same key:
        *   Designate the **first occurrence** (by Excel row order) as the **Canonical Record**.
        *   Designate subsequent occurrences as **Redundant Records**.
2.  **Tracking Source Rows:** Do not discard row metadata. The Canonical Record should include an array of all raw source Excel row numbers:
    `source_rows: [11314, 12623]`
3.  **Deduplication Count Estimates:**
    *   **Total duplicate groups:** 970
    *   **Total rows involved:** 2,044
    *   **Rows preserved (as Canonical Records):** 970
    *   **Rows merged/redundant (blocked from active database):** 1,074
    *   **Ambiguity Review Queue:** 0 (since details are 100% identical in all groups, no human review is required).

---

## 3. Database Schema Mapping for Duplicates

In the normalized JSON output, each record will have the following status fields to denote duplicate handling:

```json
{
  "duplicate_status": "canonical", 
  "source_rows": [11314, 12623],
  "active": true
}
```

For the redundant records (which are kept in a separate file or a raw import log to maintain 100% trace, or kept as inactive in the database):
*   Option A: Do not write redundant records to the main `vocabulary.json` (exclude them during merge).
*   Option B: Include them but set `"duplicate_status": "redundant"`, `"active": false`, and `"review_required": false`.
*   **Recommended Option:** **Option B.** Keep all rows in the normalized output to maintain a 1:1 mapping with the raw spreadsheet rows (satisfying "preserve all rows" rule of EGP source imports, and preventing file length mismatches in raw tests), but set their active state to `false` and duplicate status to `"redundant"`. This ensures database queries only load `"duplicate_status": "canonical"` and `"active": true` entries.
