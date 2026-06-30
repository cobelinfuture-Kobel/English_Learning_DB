# Vocabulary Review Queue Audit (VOCAB_DB_S1)

This audit evaluates the composition of the manual review queue (records with `review_required = true`). These records represent recovered fields where the confidence tier is Medium (e.g. closed-class mappings or non-unanimous majority votes).

---

## 1. Review Queue Statistics

*   **Total Dataset Records:** 15,696
*   **Total Review Queue Records:** 429
*   **Percentage of Dataset:** 2.73% (Highly manageable for developer/linguist review)

---

## 2. Review Queue Distribution

### Level Distribution
The review queue is evenly distributed across levels, reflecting that missing topics and closed-class words are present across all proficiencies:
*   **A1:** 81 records (18.9%)
*   **A2:** 100 records (23.3%)
*   **B1:** 102 records (23.8%)
*   **B2:** 88 records (20.5%)
*   **C1:** 21 records (4.9%)
*   **C2:** 37 records (8.6%) — *Can be reviewed last since C2 is inactive for generation.*

### Recovery Method Distribution (Topic)
*   **closed_class_mapping:** 254 records (59.2%) — Grammatical function words (determiners, prepositions, conjunctions) mapped to the default topic `"describing things"`.
*   **unanimous_word_majority** (Medium Confidence): 175 records (40.8%) — Words mapped based on a majority topic vote (>50% agreement) but with some conflicting occurrences.

### Recovery Method Distribution (POS)
*   **none / natively populated:** 360 records (83.9%) — POS was natively populated in raw Excel, but topic required review.
*   **closed_class_whitelist:** 66 records (15.4%) — POS was whitelisted, but topic required review.
*   **same_word_guideword_exact:** 3 records (0.7%) — POS was copied from another sense, but topic required review.

---

## 3. Review Action Recommendations

1.  **Bulk-approve Closed-Class Mappings:** The 254 closed-class grammatical words (determiners, pronouns, prepositions) mapped to `"describing things"` are linguistically sound and can be approved in bulk.
2.  **Verify Non-Unanimous Majorities (175 rows):** These should be audited for homonyms (e.g., matching a verb sense to a noun topic).
3.  **Audit C1 Queue first (21 rows):** Since C1 is a high-demand and low-count level (877 active words), resolving its 21 review queue items will yield the highest immediate benefit for advanced generation.
