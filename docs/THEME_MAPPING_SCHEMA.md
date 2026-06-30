# Theme Mapping Schema Design (THEME_DB_S0)

This document designs the JSON schema for `themes/theme_vocab_mapping.json`. This configuration file maps communicative themes to vocabulary topics, frequency constraints, and exam alignment parameters.

---

## 1. Target JSON File Path
*   `themes/theme_vocab_mapping.json`

---

## 2. Proposed JSON Schema Example

```json
{
  "themes": [
    {
      "theme_id": "a1_food_and_dining",
      "theme_name": "飲食與餐廳點餐",
      "level": "A1",
      "primary_topics": ["food and drink"],
      "secondary_topics": ["shopping", "describing things"],
      "blocked_topics": ["crime", "politics", "technology"],
      "preferred_frequency_bands": ["tier_1", "tier_2"],
      "allowed_cefr_levels": ["A1", "A1_plus", "A2"],
      "exam_alignment": {
        "exam_name": "Cambridge Starters",
        "exam_priority_boost": 2.0,
        "restricted_syllabus": true
      }
    }
  ]
}
```

---

## 3. Schema Field Specifications

### A. `theme_id`
*   **Type:** `string`
*   **Description:** Unique snake_case identifier for the theme (e.g. `a1_food_and_dining`).

### B. `theme_name`
*   **Type:** `string`
*   **Description:** The user-facing localized Chinese name of the theme (e.g. `飲食與餐廳點餐`).

### C. `level`
*   **Type:** `string enum`
*   **Allowed Values:** `"A1"`, `"A1_plus"`, `"A2"`, `"A2_plus"`, `"B1"`, `"B1_plus"`, `"B2"`, `"B2_plus"`, `"C1"`.

### D. `primary_topics`
*   **Type:** `array of strings`
*   **Description:** EVP topic names representing the core semantic focus of this theme. Vocabulary from these topics will be heavily sampled.

### E. `secondary_topics`
*   **Type:** `array of strings`
*   **Description:** EVP topic names representing supporting contexts (e.g. `describing things` for adjectives).

### F. `blocked_topics`
*   **Type:** `array of strings`
*   **Description:** EVP topic names completely banned from appearing in generated content for this theme (to prevent thematic dilution).

### G. `preferred_frequency_bands`
*   **Type:** `array of strings`
*   **Description:** Target frequency bands (e.g., `["tier_1", "tier_2"]`) to guide generator vocabulary selection.

### H. `allowed_cefr_levels`
*   **Type:** `array of strings`
*   **Description:** Allowed vocabulary CEFR levels that can be pulled for this theme's generation. This allows A1+ themes to borrow safe A2 words.

### I. `exam_alignment`
*   **Type:** `object`
*   **Fields:**
    *   `exam_name` (string): Target Cambridge exam (e.g. `"Cambridge Starters"`).
    *   `exam_priority_boost` (float): Selection multiplier for syllabus words.
    *   `restricted_syllabus` (boolean): If `true`, content words are strictly restricted to the exam syllabus list.
