# Theme Vocabulary Mapping Strategy Summary (THEME_DB_S0)

## 1. Executive Summary

This document concludes the design scan for the theme-to-vocabulary mapping architecture (THEME_DB_S0). By mapping the 21 EGP vocabulary topics and frequency bands to the 21 localized communicative themes, we establish a robust framework for downstream dialogue, story, and question generators.

---

## 2. Strategy Highlights

### A. Mapping Strategy
*   **Primary Mapping:** Core theme concepts align with specific topics (e.g. A1 Food maps to the `food and drink` topic).
*   **Universal Supporting Topics:** `communication` (for connectors) and `describing things` (for adjectives) serve as secondary topics across all themes to support functional grammar.
*   **Thematic Quarantining:** Irrelevant topics (e.g., `crime` in A1 classroom settings) are explicitly blocked.

### B. Progression Strategy
*   **CEFR Spiraling:** Topics reappear at higher levels with increasing semantic abstraction, lexical diversity, and syntactic complexity (e.g. from ordering pizza at A1 to discussing organic farming policies at C1).
*   **Plus Level Bridges:** Plus levels (A1+, A2+, B1+, B2+) function as grammar and vocabulary bridges, utilizing base level themes but allowing exposure to the next CEFR tier.

### C. Frequency & Exam Strategy
*   **Lexical Alignment:** Ratios limit low-frequency words (Tier 4/5) at lower levels to prevent cognitive overload.
*   **Syllabus Boosting:** Exam-aligned vocabulary receives a multiplier boost (1.5x–2.0x) during generator sampling. For YLE levels, non-syllabus content words are completely blocked.

---

## 3. Readiness for THEME_DB_S1_ThemeVocabularyMapping_Fix

The mapping system is **fully ready** to transition to the implementation phase (`THEME_DB_S1_ThemeVocabularyMapping_Fix`).

### Next Steps for S1:
1.  **Generate `themes/theme_vocab_mapping.json`:** Write the concrete mapping configuration file containing all 21 localized themes mapped to their primary/secondary/blocked topics, frequency bands, and exam parameters as designed in [THEME_MAPPING_SCHEMA.md](file:///G:/HomeWork/English_Learning_DB/docs/THEME_MAPPING_SCHEMA.md).
2.  **Create verification tests:** Validate that:
    *   The mapping JSON contains all levels (A1, A1+, A2, A2+, B1, B1+, B2, B2+, C1).
    *   Topics are mapped correctly.
    *   Blocked topics are correct.
    *   Tiers and exam alignment are populated.
3.  **Run full pytest validation** to ensure integration. No source files will be modified, and no C# projects will be created.
