# CEFR × Vocabulary Frequency Policy (VOCAB_DB_S0C)

This document establishes the frequency-band mix policy for each target CEFR level. Content generators must follow these ratios to ensure readability and prevent cognitive overload.

---

## 1. Level-Specific Frequency Mix Ratios

For any generated text (dialogues, stories, readings) at a given level, the vocabulary used must conform to the following target ratios:

| Level | Tier 1 (Core) | Tier 2 (High) | Tier 3 (Common) | Tier 4 (Low) | Tier 5 (Rare) | Max Rare-Word Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A1** | 90% | 10% | 0% | 0% | 0% | 0% |
| **A1+** | 80% | 15% | 5% | 0% | 0% | 0% |
| **A2** | 65% | 25% | 10% | 0% | 0% | 1% |
| **A2+** | 55% | 30% | 12% | 3% | 0% | 2% |
| **B1** | 45% | 35% | 15% | 5% | 0% | 3% |
| **B1+** | 35% | 40% | 18% | 5% | 2% | 4% |
| **B2** | 25% | 40% | 23% | 8% | 4% | 5% |
| **B2+** | 15% | 35% | 30% | 15% | 5% | 8% |
| **C1** | 10% | 30% | 35% | 20% | 5% | 10% |

*   **Max Rare-Word Ratio:** The maximum percentage of tokens in a single generated text that can belong to Tier 5 or remain outside the learner's active pool (designed to allow natural syntax without overwhelming the student).

---

## 2. Progression Policies

### A1 to A2 Progression (Focus on Tier 1 & 2 consolidation)
*   **Goal:** Solidify the core 1,000 words while introducing Tier 2 items.
*   **Policy:** A1+ acts as a buffer. It restricts grammar to complex A1 structures but expands the lexical mix to include 5% Tier 3 words (e.g. basic connectors or adjectives).

### A2 to B1 Progression (Focus on Tier 3 expansion)
*   **Goal:** Transition from survival conversations to wider reading.
*   **Policy:** B1 generators must ensure that at least 15% of the content words are Tier 3 (Common Expansion), introducing descriptive synonyms for Tier 1 words (e.g., using `purchase` alongside `buy`).

### B1 to B2 Progression (Focus on Tier 4 introduction)
*   **Goal:** Prepare for academic reading and debate.
*   **Policy:** B2 and B2+ levels introduce Tier 4 (Low Frequency) and academic terms. Tier 5 (Rare/Specialist) words are permitted up to 5% to contextually challenge the learner.

### B2 to C1 Progression (Focus on Register and Nuance)
*   **Goal:** Achieve native-like flexibility.
*   **Policy:** C1 allows up to 10% Tier 5/unlisted words. The focus shifts from introducing new grammar to refining register (formal vs informal) and precision (specific Tier 4/5 words instead of generic Tier 1/2 words).
