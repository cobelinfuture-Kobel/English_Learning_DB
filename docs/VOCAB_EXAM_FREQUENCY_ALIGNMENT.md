# Vocabulary Exam Frequency Alignment Strategy (VOCAB_DB_S0C)

This document designs how the vocabulary frequency-band strategy interacts with official Cambridge English exams. Aligned sampling ensures that content generators produce text that mirrors the lexical requirements of these standardized assessments.

---

## 1. Exam Alignment Matrix

We target five Cambridge English exams. Each exam dictates a specific vocabulary range and frequency mix in our system:

| Target Exam | Equivalent CEFR | Target Active Vocabulary | Frequency Band Focus | Cambridge Word List Integration |
| :--- | :---: | :--- | :--- | :--- |
| **Cambridge Starters (YLE)** | A1 | A1 active pool | Tier 1 (95%), Tier 2 (5%) | Mandatory (100% of generated nouns/verbs must come from YLE Starters list). |
| **Cambridge Movers (YLE)** | A1+ / A2 | A1–A2 active pool | Tier 1 (80%), Tier 2 (20%) | Mandatory (Movers list prioritized). |
| **Cambridge Flyers (YLE)** | A2 / A2+ | A1–A2+ active pool | Tier 1 (70%), Tier 2 (25%), Tier 3 (5%) | Mandatory (Flyers list prioritized). |
| **A2 Key (KET)** | A2+ | A1–A2+ active pool | Tier 1 (60%), Tier 2 (30%), Tier 3 (10%) | High priority (KET syllabus mapped). |
| **B1 Preliminary (PET)** | B1 / B1+ | A1–B1+ active pool | Tier 1 (50%), Tier 2 (35%), Tier 3 (15%) | High priority (PET syllabus mapped). |

---

## 2. Exam Weighting and Sampling Priority

To ensure exam-relevant words are generated frequently:

1.  **Exam Multiplier (`exam_weight`):**
    *   Any vocabulary record included in a digitized Cambridge Exam Word List gets an `exam_weight` multiplier (e.g. `1.5` or `2.0`).
    *   When the generator selects words for a lesson, the selection probability is:
        $$\text{Sampling Probability} \propto \text{frequency\_score} \times \text{exam\_weight}$$
    *   This forces the generator to select exam-specific words (like `timetable` or `luggage`) over generic synonyms, while keeping the language natural.
2.  **Vocabulary Restriction for Distractors:**
    *   In multiple-choice questions designed for exam prep, distractors (incorrect answers) must be selected from the same exam-specific vocabulary list as the correct answer. This prevents distractors from being obviously out of register or level.
3.  **Active Exclusion of Non-Exam Words at YLE Levels:**
    *   For Starters, Movers, and Flyers content, the generator is **forbidden** from selecting non-exam nouns and verbs. Basic syntactic words (pronouns, prepositions) can be used for natural grammar, but content words must match the syllabus.
