# Vocabulary Frequency Generator Policy (VOCAB_DB_S0C)

This document establishes the design policies for consuming vocabulary frequency metadata in downstream content generators.

---

## 1. Dialogue Generator Policy
*   **Vocabulary Constraint:** Dialogues must strictly mimic natural speech. Therefore, they should favor Tier 1 (Core) and Tier 2 (High Frequency) words.
*   **Lexical Density:** The ratio of content words to function words must be kept low. Turn-taking lines should be brief (max 10-15 words).
*   **Policy Rule:** At least 85% of words in any generated dialogue for levels A1-B1 must come from Tier 1 and Tier 2. Rare idioms (Tier 5) are strictly prohibited below B2.

## 2. Question Generator Policy
*   **Assessment Consistency:** In multiple-choice questions, vocabulary familiarity must not distract from the targeted grammar test point.
*   **Distractor Rule:** All distractors (incorrect options) must be selected from the same frequency tier (or higher) as the correct answer. For example, if the correct answer is `purchase` (Tier 3), the distractors cannot be `buy` (Tier 1) or `acquisition` (Tier 4), as this introduces a vocabulary familiarity bias.
*   **Sentence Context:** The carrier sentence for the question must not contain words of a higher CEFR level or lower frequency band than the target level.

## 3. Story Generator Policy
*   **Lexical Variety:** Stories require descriptive language (adjectives, adverbs) which naturally fall into Tier 3 and Tier 4.
*   **Policy Rule:** Generators are permitted a "lexical exposure margin" of up to 5% of tokens. This means a B1 story can include up to 5% Tier 4/5 words to serve as contextual reading challenges (with definitions provided), while the remaining 95% is restricted to B1 active vocabulary.

## 4. Reading Generator Policy
*   **Type-Token Ratio (TTR):** To ensure reading texts are accessible, generators must maintain a high token-to-type ratio for lower levels (repeating the same core words) and lower ratios for higher levels.
*   **Policy Rule:**
    *   *A1-A2:* TTR must be above `0.6` (high repetition of core Tier 1 vocabulary).
    *   *B2-C1:* TTR can drop to `0.3` (introducing varied synonyms from Tier 3 and Tier 4).

## 5. Listening Generator Policy
*   **Acoustic Familiarity:** Unfamiliar, low-frequency words are harder to recognize in spoken audio.
*   **Policy Rule:** Speech rate (words per minute, WPM) and vocabulary frequency are inversely proportional:
    *   *Lower frequency vocabulary:* Speech rate must slow down (e.g. 100 WPM for B1 texts containing Tier 3 words).
    *   *High frequency vocabulary:* Speech rate can be natural (e.g. 140 WPM for B1 texts containing only Tier 1 & 2 words).
