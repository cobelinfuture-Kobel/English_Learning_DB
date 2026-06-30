# Vocabulary Active Pool Quality Audit (VOCAB_DB_S1)

This audit evaluates the semantic and syntactic composition of the active-ready vocabulary pool (levels A1–C1) following deduplication and pipeline recovery.

---

## 1. Level-Specific Active Pool Breakdown

### Level A1
*   **Total Active Rows:** 625
*   **Nouns:** 252 (40.3%)
*   **Verbs:** 86 (13.8%)
*   **Adjectives:** 73 (11.7%)
*   **Phrases/Phrasal Verbs:** 44 (7.0%)
*   **Topic Coverage:** 20/21 (95.2%) — *Only "politics" has zero entries at A1, which is pedagogically expected for basic learners.*

### Level A2
*   **Total Active Rows:** 1,224
*   **Nouns:** 532 (43.5%)
*   **Verbs:** 160 (13.1%)
*   **Adjectives:** 161 (13.2%)
*   **Phrases/Phrasal Verbs:** 125 (10.2%)
*   **Topic Coverage:** 21/21 (100.0%)

### Level B1
*   **Total Active Rows:** 2,071
*   **Nouns:** 859 (41.5%)
*   **Verbs:** 384 (18.5%)
*   **Adjectives:** 320 (15.5%)
*   **Phrases/Phrasal Verbs:** 266 (12.8%)
*   **Topic Coverage:** 21/21 (100.0%)

### Level B2
*   **Total Active Rows:** 2,740
*   **Nouns:** 1,030 (37.6%)
*   **Verbs:** 521 (19.0%)
*   **Adjectives:** 471 (17.2%)
*   **Phrases/Phrasal Verbs:** 478 (17.4%)
*   **Topic Coverage:** 21/21 (100.0%)

### Level C1
*   **Total Active Rows:** 877
*   **Nouns:** 334 (38.1%)
*   **Verbs:** 178 (20.3%)
*   **Adjectives:** 192 (21.9%)
*   **Phrases/Phrasal Verbs:** 116 (13.2%)
*   **Topic Coverage:** 21/21 (100.0%)

---

## 2. Comparison Against Pool Expansion Simulation

Below we compare the actual deduplicated active-ready counts against the Scenario D counts from our pre-import simulation (`docs/VOCAB_POOL_EXPANSION_SIMULATION.md`):

| CEFR Level | Scenario D Count (Simulation) | Actual Active Count (Imported) | Variance (Redundant Merged) | Growth over Baseline (5981) |
| :--- | :---: | :---: | :---: | :---: |
| **A1** | 628 | 625 | -3 | +32.7% |
| **A2** | 1,240 | 1,224 | -16 | +26.8% |
| **B1** | 2,108 | 2,071 | -37 | +25.2% |
| **B2** | 2,812 | 2,740 | -72 | +21.6% |
| **C1** | 921 | 877 | -44 | +37.5% |
| **Total** | **7,709** | **7,537** | **-172** | **+26.0%** |

### Variance Analysis:
The variance of **-172 records** represents the active-ready rows that were identified as exact composite-key duplicates. Deduplicating these records ensures the active pool remains clean and free of redundant senses without losing semantic variety. The net growth over the baseline remains a massive **+26.0%**, increasing the active vocabulary from 5,981 to 7,537.
