# Vocabulary Frequency Strategy Master Summary (VOCAB_DB_S0C)

## 1. Recommended Frequency Model

We recommend the **Hybrid Frequency Model**. This model integrates three data dimensions:
1.  **Pedagogical CEFR Levels:** Handled natively via EGP/EVP classification (A1-C1 active pools).
2.  **Empirical Corpus Statistics:** Quantitative sorting using standard lemma frequency tables (BNC/COCA).
3.  **Assessment Alignment:** Cambridge exam syllabus overlays (YLE Starters/Movers/Flyers, KET, PET) acting as priority multipliers.

This hybrid approach ensures that content generation is grammatically sound, naturally common, and exam-relevant.

---

## 2. Tier Definitions Summary

Vocabulary will be structured into five frequency tiers based on reference corpus ranks:
*   **Tier 1: Core Essential** (Bands 1–1k). Critical baseline vocabulary.
*   **Tier 2: High Frequency** (Bands 1.5k–3k). Conversational standard vocabulary.
*   **Tier 3: Common Expansion** (Bands 3.5k–8k). Literacy and debate-enabling vocabulary.
*   **Tier 4: Low Frequency** (Bands 8.5k–15k). Stylistic synonyms and abstract vocabulary.
*   **Tier 5: Rare / Specialist** (Bands 15k+). Receptive reading challenge vocabulary.

---

## 3. CEFR & Exam Alignment Policy Summary

### CEFR Tier Mix
*   *A1:* 90% Tier 1, 10% Tier 2. Zero rare-word tolerance.
*   *B1:* 45% Tier 1, 35% Tier 2, 15% Tier 3, 5% Tier 4.
*   *C1:* 10% Tier 1, 30% Tier 2, 35% Tier 3, 20% Tier 4, 5% Tier 5. Up to 10% rare-word tolerance.

### Exam Weighting
*   Words appearing in official Cambridge syllabi get an `exam_weight` multiplier of `1.5` or `2.0`, which directly boosts their sampling priority in dialogue and question generators.
*   Distractors in multiple-choice questions must match the frequency band of the correct answer to prevent selection bias.

---

## 4. Readiness for Implementation

The vocabulary sub-system is **fully ready** to proceed to the implementation stage (`VOCAB_DB_S0D_FrequencyImplementation_Fix`).

### Next Steps for Implementation (S0D):
1.  **Source the Corpus Table:** Load a standardized frequency table (e.g. COCA/BNC lemma counts) into the workspace as a temporary script input.
2.  **Write the Import Extension Script:** Modify or create a tool (`tools/apply_frequency.py`) that reads the frequency table, maps the terms to our `vocabulary.json` records, calculates `frequency_band`, `frequency_score`, and `sampling_weight`, and writes the extended JSON back.
3.  **Digitize Exam Syllabi:** Load Young Learner (YLE) and standard KET/PET word lists, matching words in `vocabulary.json` to assign their `exam_weight` multipliers.
4.  **Write Pytest Verifications:** Ensure that:
    *   Tiers contain correct word counts.
    *   C1 records have appropriate frequency scores.
    *   Common words like `house` belong to Tier 1, while advanced terms belong to Tiers 3/4.
    *   No C# projects are created and source Excel files are untouched.
