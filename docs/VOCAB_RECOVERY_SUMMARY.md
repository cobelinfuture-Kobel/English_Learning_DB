# Vocabulary Recovery Strategy Master Summary (VOCAB_DB_S0B)

## 1. Executive Summary

This document presents the master recovery strategy and recommended import policies for resolving the massive missing data and duplicate row challenges in the English Vocabulary Profile (EVP) source dataset. 

By applying a deterministic, rules-based recovery pipeline, we can expand the active-ready vocabulary pool from **5,981 words to 7,709 words**, a **28.9% growth** that ensures downstream dialog, sentence, and question generators have sufficient thematic vocabulary.

---

## 2. Best Recovery Strategy

The recommended strategy is a **Sequenced Hybrid Recovery Pipeline** (equivalent to Scenario D in our simulations). 

Instead of relying on a single method, the importer runs a multi-stage check that fills missing fields from the highest-confidence sources first, moving down to whitelists and heuristics only when specific matches fail.

### Estimated Recoverable Rows & Growth
*   **Total Missing Topics:** 8,794 rows (56.0% of canonical sheet)
    *   *Recovered by Pipeline:* 1,728 rows (active pool eligible)
*   **Total Missing POS:** 111 rows (0.7% of canonical sheet)
    *   *Recovered by Pipeline:* 111 rows (100% recovery)
*   **Active Pool Expansion:**
    *   *Baseline (No recovery):* 5,981 active-ready rows.
    *   *With Master Recovery:* 7,709 active-ready rows.
    *   *Net Increase:* **+1,728 active-ready words (+28.9%)**.
    *   *C1 level growth:* **+283 words (+44.4%)**, increasing from 638 to 921.

---

## 3. Recommended Import & Deduplication Policy

*   **Canonical Import:** Use sheet `total(15696)` as the sole canonical source.
*   **Preserve Raw Integrity:** Do not overwrite the raw Excel fields. Store resolved fields in distinct JSON attributes: `topic`, `part_of_speech`, and status fields.
*   **Duplicate Merging:**
    *   For the 970 exact duplicate groups (1,074 redundant rows), designate the first row as `canonical` and subsequent identical rows as `redundant`.
    *   Merge their row numbers into a `source_rows` array to maintain 100% Excel-to-JSON row traceability.
    *   Set `active: false` on redundant rows to exclude them from content generation while keeping them in the normalized JSON dataset to preserve total sheet row counts for tests.
*   **Closed-Class Whitelist:** Implement a hardcoded lookup list for numbers and common conjunctions/prepositions. This resolves 100% of missing POS entries.
*   **C2 Excluded:** Import C2 rows (3,807 rows) for database completeness, but set `active: false` in their profiles to ensure they are excluded from A1-C1 lesson generation.

---

## 4. Major Implementation Risks & Mitigations

1.  **Homonym Mismapping (Voting Risk):**
    *   *Risk:* Word-level majority voting might assign a wrong topic to a word with multiple senses (e.g. `match` as sports topic vs `match` as household topic).
    *   *Mitigation:* Keep `recovery_confidence: medium` and `review_required: true` for any majority votes where there was not 100% topic agreement among populated rows.
2.  **Generic Topic Bloat (Closed-Class Mapping):**
    *   *Risk:* Over-mapping determiners, prepositions, and pronouns to `describing things` might over-represent that topic in content generation.
    *   *Mitigation:* Downstream lesson builders can filter out function words or restrict vocabulary selection to content words (nouns, verbs, adjectives).
3.  **Phrase Extraction Complexity:**
    *   *Risk:* Many advanced entries are idioms and phrases (e.g. `get sth off your chest`), which do not have a single POS.
    *   *Mitigation:* Map these to POS: `phrase` or `phrasal verb` and ensure downstream text processing tools handle multi-word vocabulary matches.

---

## 5. Readiness for VOCAB_DB_S1_SourceImport_Fix

Status: **Fully Ready**.

The project is ready to proceed with implementation. The import tool `tools/import_vocabulary.py` should implement the recovery pipeline designed here. 

### Recommended Next Steps for S1:
1.  Initialize the normalized dataset `vocabulary/json/vocabulary.json` containing all 15,696 records.
2.  Populate the recovery metadata fields as designed in [VOCAB_RECOVERY_ARCHITECTURE.md](file:///G:/HomeWork/English_Learning_DB/docs/VOCAB_RECOVERY_ARCHITECTURE.md).
3.  Create an import report `output/reports/vocab_import_report.json` tracking baseline vs recovered counts, duplicates, and warning rows.
4.  Write comprehensive tests verifying the 15,696 row count, active counts, and recovery correctness.
