# Vocabulary Frequency Schema Design (VOCAB_DB_S0C)

This document designs the metadata schema extension for vocabulary records in `vocabulary.json` to support frequency bands and exam weighting.

---

## 1. Proposed Database Schema Extension

Each normalized vocabulary record will be extended with the following five fields:

```json
{
  "vocab_id": "v_10825",
  "word": "can",
  "guideword": "REQUEST",
  "level": "A1",
  "topic": "communication",
  "part_of_speech": "modal verb",
  
  "frequency_band": "tier_1",
  "frequency_score": 1240.52,
  "exam_weight": 2.0,
  "learning_priority": 98,
  "sampling_weight": 2.48,
  
  "active": true
}
```

---

## 2. Field Specifications and Types

### A. `frequency_band`
*   **Type:** `string enum`
*   **Allowed Values:** `"tier_1"`, `"tier_2"`, `"tier_3"`, `"tier_4"`, `"tier_5"`
*   **Description:** The frequency tier mapped from the reference corpus rank.
*   **Default:** `"tier_5"` (for unlisted/rare terms).

### B. `frequency_score`
*   **Type:** `float`
*   **Description:** Normalized occurrences per million words (PMR) in the reference corpus (e.g. BNC/COCA).
*   **Default:** `0.0` (for words not found in reference corpus).

### C. `exam_weight`
*   **Type:** `float`
*   **Description:** Multiplier applied to exam-aligned vocabulary.
    *   `1.0`: Standard word (no exam alignment).
    *   `1.5`: Appeared on KET/PET syllabus.
    *   `2.0`: Appeared on YLE (Starters/Movers/Flyers) syllabus (highly restricted).
*   **Default:** `1.0`.

### D. `learning_priority`
*   **Type:** `integer (1 to 100)`
*   **Description:** A calculated score indicating pedagogical priority.
    *   Formula:
        $$\text{learning\_priority} = f(\text{level}, \text{frequency\_score}, \text{exam\_weight})$$
    *   A1 exam words have priority `95-100`; C1 rare words have priority `1-10`.
*   **Default:** `50` (or calculated upon import).

### E. `sampling_weight`
*   **Type:** `float`
*   **Description:** The actual numerical probability weight loaded by content generators when choosing vocabulary.
    *   Formula:
        $$\text{sampling\_weight} = \text{frequency\_score} \times \text{exam\_weight}$$
*   **Default:** `0.0`.
