# Vocabulary Frequency Source Analysis (VOCAB_DB_S0C)

This document evaluates candidate sources of vocabulary frequency data for the English Learning Database. Integrating frequency data allows the system to prioritize core vocabulary, structure learner progression, and enable exam-aligned sampling.

---

## 1. Candidate Source Evaluation

### Model A: Internal Frequency Only
*   **Description:** Track and calculate the occurrences of words within the generated learning content database (dialogues, questions, readings) dynamically.
*   **Advantages:**
    *   Perfect alignment with what learners actually read/hear in the system.
    *   No external corpus licensing or integration required.
*   **Disadvantages:**
    *   *Cold Start Problem:* No frequency data is available until content has been generated.
    *   *Silo Bias:* Reflects and amplifies the generator's biases instead of natural English.
*   **Implementation Complexity:** Low.

### Model B: EVP Level-Based Approximation
*   **Description:** Approximate frequency using EGP/EVP CEFR levels (e.g. assume A1 = top 1,000 words, A2 = words 1,001–2,500, etc.).
*   **Advantages:**
    *   Zero external dependencies.
    *   Utilizes natively populated database fields immediately.
*   **Disadvantages:**
    *   *Intra-level Ambiguity:* Highly inaccurate within a single level. For example, `yes` (extremely common) and `yet` (common) are both A1, but `yet` has a much lower natural occurrence frequency.
    *   *No Fine-grained Sorting:* Cannot rank words within a level.
*   **Implementation Complexity:** Very Low.

### Model C: Cambridge Exam Vocabulary Weighting
*   **Description:** Weight words based on their occurrence or inclusion in official Cambridge English syllabi (Starters, Movers, Flyers, KET, PET).
*   **Advantages:**
    *   Highly optimized for learners preparing for Young Learners (YLE) and standard Cambridge tests.
    *   Ensures curriculum alignment.
*   **Disadvantages:**
    *   Does not cover C1 or advanced B2 vocabulary.
    *   Treats vocabulary as binary lists rather than a continuous scale of frequency.
*   **Implementation Complexity:** Moderate (requires digitizing and mapping official syllabus lists).

### Model D: CEFR Progression Weighting
*   **Description:** Weight vocabulary based on the developmental progression of grammatical and lexical levels.
*   **Advantages:**
    *   Aligned with academic frameworks for language acquisition.
*   **Disadvantages:**
    *   Fails to capture real-world spoken/written frequencies.
*   **Implementation Complexity:** Moderate.

### Model E: Hybrid Frequency Model (Recommended)
*   **Description:** Combine a standard external reference corpus (e.g., British National Corpus (BNC) or Corpus of Contemporary American English (COCA)) for baseline frequency, overlaid with Cambridge syllabus weightings (as multipliers) and EGP/EVP CEFR levels as structural boundaries.
*   **Advantages:**
    *   *Pedagogically sound:* Base CEFR levels guarantee that structural levels are respected.
    *   *Statistically accurate:* Corpus data provides precise, real-world sorting within levels.
    *   *Exam-focused:* Multipliers prioritize vocabulary likely to appear on targeted Cambridge assessments.
*   **Disadvantages:**
    *   Requires mapping external corpus frequency tables (lemmas) to our normalized vocabulary word lists.
    *   Multi-word units (phrases, idioms) require custom frequency approximation.
*   **Implementation Complexity:** High.

---

## 2. Recommendation and Selection

We recommend the **Hybrid Frequency Model (Model E)**. 

To implement it, we will map a clean reference lemma frequency table (derived from BNC/COCA) to our `vocabulary.json` records. When a word also appears in a Cambridge syllabus list, its sampling priority will be boosted. This provides the ideal blend of empirical usage frequency, curricular focus, and CEFR structural progression.
