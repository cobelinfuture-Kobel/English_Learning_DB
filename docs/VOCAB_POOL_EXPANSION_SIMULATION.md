# Vocabulary Active Pool Expansion Simulation (VOCAB_DB_S0B)

## 1. Overview of Active-Pool Constraints

To be eligible for active content generation in the English Learning Database, a vocabulary record must have:
1.  A valid, non-empty **Topic** (representing thematic alignment).
2.  A valid, non-empty **Part of Speech** (representing grammatical class).
3.  A CEFR level between **A1 and C1** (C2 is imported but excluded from active generation by default).
4.  Be marked as **Canonical** (not a redundant composite-key duplicate).

If a row is missing its Topic or POS, it is blocked from active generation. We simulated four recovery scenarios to measure their impact on the active pool.

---

## 2. Scenario Definitions

*   **Scenario A: No Recovery (Baseline)**
    *   *Rules:* No automated recovery is applied. Only rows with natively populated `Topic` and `Part of Speech` in the Excel spreadsheet are considered active-ready.
*   **Scenario B: High-Confidence Recovery Only**
    *   *Rules:*
        *   POS is recovered via topic-sheet reconciliation, same-word unique POS, or same-word + guideword unique POS.
        *   Topic is recovered via same-word + guideword unique topic, or unanimous word-level majority topic.
*   **Scenario C: Medium-Confidence Recovery**
    *   *Rules:*
        *   Includes Scenario B.
        *   POS is recovered using majority POS voting (>50% agreement).
        *   Topic is recovered using majority topic voting (>50% agreement).
*   **Scenario D: Maximum Recovery**
    *   *Rules:*
        *   Includes Scenario C.
        *   POS is recovered using a closed-class grammatical whitelist (numbers, conjunctions, prepositions).
        *   Topic is recovered using guideword keyword heuristics (e.g. `MONEY` -> `money`) and closed-class default mappings (e.g. determiners -> `describing things`).

---

## 3. Simulation Results (Active-Ready Counts)

Below are the active-ready counts for levels A1–C1 under each scenario:

| CEFR Level | Scenario A (Baseline) | Scenario B (High-Conf) | Scenario C (Med-Conf) | Scenario D (Max Recovery) | Net Growth (A -> D) | % Growth (A -> D) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A1** | 471 | 535 | 549 | 628 | +157 | +33.3% |
| **A2** | 965 | 1,127 | 1,150 | 1,240 | +275 | +28.5% |
| **B1** | 1,654 | 1,972 | 2,024 | 2,108 | +454 | +27.4% |
| **B2** | 2,253 | 2,698 | 2,743 | 2,812 | +559 | +24.8% |
| **C1** | 638 | 883 | 899 | 921 | +283 | +44.4% |
| **Total (A1-C1)** | **5,981** | **7,215** | **7,365** | **7,709** | **+1,728** | **+28.9%** |

---

## 4. Key Findings & Insights

1.  **Massive C1 Expansion:** The C1 level has a 73.5% missing topic rate in the raw source, leaving only 638 active-ready words. Maximum recovery increases this pool to **921 active-ready words (a 44.4% growth)**, which is crucial for preventing vocabulary starvation in advanced writing and dialog generation.
2.  **Diminishing Returns of Low-Confidence Methods:** The step from Scenario B to Scenario C (majority voting) adds only 150 rows. However, the step to Scenario D ( whitelist and guideword heuristics) adds 344 rows, showing that structured rules are more effective than simple majority votes.
3.  **Overall Pool Health:** Recovering 1,728 vocabulary records (28.9% total pool growth) expands the thematic coverage of the database, ensuring that lesson builders have a rich selection of terms for all 21 topic domains.
