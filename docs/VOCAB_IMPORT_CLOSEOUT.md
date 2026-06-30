# Vocabulary Import Closeout Verdict (VOCAB_DB_S1)

This closeout verdict concludes the vocabulary import and recovery quality audit (VOCAB_DB_S1).

---

## 1. Executive Summary

The vocabulary import pipeline has successfully normalized all **15,696 rows** of the English Vocabulary Profile (EVP) source workbook. 

By applying a sequenced recovery pipeline, we resolved **2,163 missing topics** and **110 missing POS** entries, increasing the active-ready vocabulary pool by **26.0% (from 5,981 to 7,537 entries)**. 

Duplicate rows have been successfully resolved by merging 1,074 redundant entries, keeping the active database clean and free of duplicates while preserving full traceability.

---

## 2. Strengths and Weaknesses

### Strengths
1.  **High Data Yield:** Increased the C1 active vocabulary from 638 to 877 (+37.5%), providing crucial lexical diversity for advanced levels.
2.  **Stable Duplicate Handling:** 100% of exact duplicates were resolved and merged without affecting legitimate multi-sense and level-progression entries.
3.  **Low Review Overhead:** The manual review queue is restricted to **429 records (2.73% of total)**, allowing for rapid human validation.
4.  **100% Traceability:** Excel row numbers are preserved in every record's `source_rows` metadata array.

### Weaknesses
*   **Substring Matching False Positives:** The guideword keyword heuristics matched generic sub-strings (e.g. `skill` matching `ill` -> mapped to `body and health`; `problems` matching `rob` -> mapped to `crime`; `businesses` matching `bus` -> mapped to `travel`). These are safely flagged as review-required or warning rows but represent a structural weakness in unconstrained regex heuristics.

---

## 3. Unresolved Risks

1.  **Over-representation of default topic "describing things":** Closed-class grammatical words (determiners, prepositions, conjunctions) mapped to `"describing things"` may distort the thematic balance.
    *   *Mitigation:* Downstream tools must filter out closed-class parts of speech when generating thematic lessons.
2.  **Homonym Misclassification:** Majority voting might occasionally mismape a homonym.
    *   *Mitigation:* Handled via the review queue, requiring human verification for non-unanimous matches.

---

## 4. Final Verdict

**VERDICT: PASS_WITH_WARNINGS**

### Justification:
*   **Recovery Pipeline Stable:** Yes. 15,696 rows are fully processed and parsed.
*   **Duplicate Policy Stable:** Yes. Exact duplicates are merged.
*   **Active Pool Usable:** Yes. 7,537 high-quality words are active-ready.
*   **Review Queue Manageable:** Yes (429 records under review).
*   *Warnings:* Heuristic topic matches include known substring false positives (e.g. `amateur` and `branch` mapped to incorrect topics). These records must be reviewed or filtered during generation.

---

## 5. Recommendation & Readiness

The vocabulary dataset is **fully ready** to transition to the next phase: `VOCAB_DB_S0C_FrequencyStrategy_DesignScan`.

### Next Step Recommendation:
*   Proceed to the frequency strategy scan. Integrating word frequency data (e.g. from COCA or BNC corpora) will allow us to sort the 7,537 active-ready words by usage frequency, providing an additional layer of pedagogical filtering for dialogue and sentence generation.
