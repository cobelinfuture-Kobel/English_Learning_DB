# Theme Frequency Integration Policy (THEME_DB_S0)

This document establishes the frequency-band constraints and exam weighting rules for generated theme-specific content.

---

## 1. Frequency Mix & Weighting Policy

For each communicative theme, generators must prioritize vocabulary matching the target level's frequency guidelines while boosting exam-aligned words.

| Theme Level | Preferred Frequency Bands | Max Rare-Word Ratio | Exam Priority Boost | Target Exam Alignment |
| :--- | :--- | :---: | :---: | :--- |
| **A1 Themes** | Tier 1 (90%), Tier 2 (10%) | 0.0% | **High (2.0x)** | Cambridge Starters (YLE) |
| **A1+ Themes** | Tier 1 (80%), Tier 2 (15%), Tier 3 (5%) | 0.0% | **High (2.0x)** | Cambridge Movers (YLE) |
| **A2 Themes** | Tier 1 (65%), Tier 2 (25%), Tier 3 (10%) | 1.0% | **Moderate (1.5x)** | Cambridge Movers & Flyers |
| **A2+ Themes** | Tier 1 (55%), Tier 2 (30%), Tier 3 (15%) | 2.0% | **Moderate (1.5x)** | A2 Key (KET) |
| **B1 Themes** | Tier 1 (45%), Tier 2 (35%), Tier 3 (20%) | 3.0% | **Moderate (1.5x)** | B1 Preliminary (PET) |
| **B1+ Themes** | Tier 1 (35%), Tier 2 (40%), Tier 3 (25%) | 4.0% | **Moderate (1.5x)** | B1 Preliminary (PET) |
| **B2 Themes** | Tier 1 (25%), Tier 2 (40%), Tier 3 (35%) | 5.0% | **None (1.0x)** | *Standard general use* |
| **B2+ Themes** | Tier 1 (15%), Tier 2 (35%), Tier 3 (50%) | 8.0% | **None (1.0x)** | *Standard general use* |
| **C1 Themes** | Tier 1 (10%), Tier 2 (30%), Tier 3 (60%) | 10.0% | **None (1.0x)** | *Academic general use* |

*   **Max Rare-Word Ratio:** The percentage limit of tokens from lower frequency bands (Tier 4/5) or unlisted words permitted in generated passages.
*   **Exam Priority Boost:** Multiplier applied to words listed in official syllabi (YLE/KET/PET) within the theme's matched topic to prioritize their selection.

---

## 2. Theme-Specific Weighting Overrides

Certain themes require custom frequency overrides to support their specialized communicative goals:

1.  **Shopping & Money Themes (A1-T5, A2-T2, B1-T1):**
    *   *Override:* Increase priority for words matching the `money` and `shopping` topics regardless of their raw frequency rank. (This ensures that words like `change`, `price`, and `cash` are used even if they have lower general corpus counts).
2.  **Health & Symptoms (A1-T9):**
    *   *Override:* Body parts (e.g. `finger`, `stomach`) and symptoms (e.g. `headache`, `cold`) are often Tier 2/3 but are essential for A1 medical scenarios. Increase their priority multiplier to `2.5x` specifically for A1-T9 generation.
3.  **Academic & Workplace (B1-T2, B2-T1, C1-T1):**
    *   *Override:* Boost vocabulary in the `work` and `technology` topics. Allow Tier 4 words (e.g. `qualification`, `application`) up to 10% in B1 Workplace dialogues to reflect authentic professional settings.
