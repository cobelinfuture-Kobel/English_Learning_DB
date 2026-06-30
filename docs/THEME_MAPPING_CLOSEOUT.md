# Theme Vocabulary Mapping Closeout Audit (THEME_DB_S1)

This closeout audit concludes the implementation and validation of the theme-to-vocabulary mapping layer.

---

## 1. Mapping Statistics
*   **Total Themes Mapped:** 25 themes (A1 to C1, including plus levels).
*   **Primary Topic Mappings:** 65 topic associations.
*   **Secondary Topic Mappings:** 51 topic associations.
*   **Blocked Topic Mappings:** 57 explicit exclusions.

---

## 2. Vocabulary Coverage Statistics

Below is a summary of active-ready vocabulary coverage for key communicative themes across levels:

*   **a1_personal_information_and_greetings (A1):**
    *   *Total vocab matching topics/CEFR:* 326
    *   *Active vocabulary count:* 322 (Primary: 60, Secondary: 262)
*   **a1_food_and_dining (A1):**
    *   *Total vocab matching topics/CEFR:* 233
    *   *Active vocabulary count:* 232 (Primary: 50, Secondary: 182)
*   **a2_travel_and_consumption (A2):**
    *   *Total vocab matching topics/CEFR:* 761
    *   *Active vocabulary count:* 758 (Primary: 169, Secondary: 589)
*   **b1_work_and_business_environment (B1):**
    *   *Total vocab matching topics/CEFR:* 1,515
    *   *Active vocabulary count:* 1,507 (Primary: 313, Secondary: 1,194)
*   **c1_precise_expression (C1):**
    *   *Total vocab matching topics/CEFR:* 3,467
    *   *Active vocabulary count:* 3,215 (Primary: 2,071, Secondary: 1,144)

---

## 3. Progression Summary

We established **4 explicit progression chains** linking themes across levels:
1.  **Food & Transactions Chain:**
    `a1_food_and_dining` $\rightarrow$ `a2_travel_and_consumption` $\rightarrow$ `b1_travel_and_living_abroad` $\rightarrow$ `c1_implicit_meanings_and_complex_texts`
2.  **Daily Life & Work Chain:**
    `a1_daily_life_and_routines` $\rightarrow$ `a2_daily_transactions_and_local_environment` $\rightarrow$ `b1_work_and_business_environment` $\rightarrow$ `b2_professional_and_academic_situations` $\rightarrow$ `c1_advanced_work_and_socializing`
3.  **Social & Personal Chain:**
    `a1_personal_information_and_greetings` $\rightarrow$ `a2_socializing_and_discussion` $\rightarrow$ `b1_personal_expression_and_socializing` $\rightarrow$ `b2_native_speed_communication` $\rightarrow$ `c1_precise_expression`
4.  **Travel & Nature Chain:**
    `a1_travel_and_weather` $\rightarrow$ `a2_travel_and_consumption` $\rightarrow$ `b1_travel_and_living_abroad` $\rightarrow$ `b2_in_depth_debates_and_meetings` $\rightarrow$ `c1_precise_expression`

---

## 4. Strengths & Weaknesses

### Strengths
*   **100% Normalized Comparisons:** Topic lookup is fully normalized to prevent hyphen/colon mismatches (e.g. `people: actions` vs `people-actions` are equated).
*   **PEDAGOGICAL ALIGNMENT:** Cumulative allowed CEFR levels correctly permit higher levels to draw upon vocabulary from lower levels.
*   **Zero Leakage:** Pytest validates that no blocked topic ever overlaps with primary topics, ensuring theme integrity.
*   **Progression Integrity:** Validation verifies that all next/prev progression references correspond to active theme IDs.

### Weaknesses
*   **Vocabulary Concentration:** Themes heavily rely on secondary supporting topics (`communication` and `describing things`) for sentence structure. While linguistically correct, it means different themes draw from a large shared pool of adjectives and connectors, reducing thematic uniqueness if not filtered.

---

## 5. Unresolved Risks
*   **Plus Level Word Counts:** Plus level themes (e.g., A1+, B1+) have very large active word lists because they borrow words from the next CEFR level (e.g. A1+ allowed levels = A1, A2). Downstream generators must use the frequency bands to restrict choice.
    *   *Mitigation:* Force generators to use preferred frequency bands (`tier_1` and `tier_2` only for YLE movers/flyers) to filter this large pool.
