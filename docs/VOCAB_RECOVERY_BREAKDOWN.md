# Vocabulary Recovery Method Breakdown (VOCAB_DB_S1)

## 1. Topic Recovery Method Breakdown

Of the **8,794 rows** with missing topics in the raw `total(15696)` sheet, the recovery pipeline successfully resolved **2,163 rows (24.6%)**, expanding the active-ready database. The remaining 6,631 rows could not be resolved and remain unmapped.

Below is the breakdown of topic recovery methods applied:

| Topic Recovery Method | Count | % of Total Dataset (15696) | % of Missing Topics (8794) | Confidence Tier |
| :--- | :---: | :---: | :---: | :---: |
| **topic_sheet_reconciliation** | 95 | 0.61% | 1.08% | **High** |
| **same_word_guideword_exact** | 78 | 0.50% | 0.89% | **High** |
| **unanimous_word_majority** (unanimous) | 1,448 | 9.23% | 16.47% | **High** |
| **unanimous_word_majority** (majority >50%) | 175 | 1.11% | 1.99% | **Medium** |
| **guideword_heuristics** | 113 | 0.72% | 1.29% | **High** |
| **closed_class_mapping** | 254 | 1.62% | 2.89% | **Medium** |
| *Total Topic Recovered* | *2,163* | *13.78%* | *24.60%* | |
| *Unmapped Topics* | *6,631* | *42.25%* | *75.40%* | |

---

## 2. Part-of-Speech (POS) Recovery Method Breakdown

Of the **111 rows** with missing parts of speech in the raw sheet, the pipeline recovered **110 rows (99.1%)**. Only 1 row remains unmapped (representing a C2 entry).

Below is the breakdown of POS recovery methods applied:

| POS Recovery Method | Count | % of Total Dataset (15696) | % of Missing POS (111) | Confidence Tier |
| :--- | :---: | :---: | :---: | :---: |
| **topic_sheet_reconciliation** | 0 | 0.00% | 0.00% | **High** |
| **same_word_guideword_exact** | 9 | 0.06% | 8.11% | **High** |
| **closed_class_whitelist** | 100 | 0.64% | 90.09% | **High** |
| **unique_word_pos** | 1 | 0.01% | 0.90% | **High** |
| **majority_pos_vote** | 0 | 0.00% | 0.00% | **Medium** |
| *Total POS Recovered* | *110* | *0.70%* | *99.10%* | |
| *Unmapped POS* | *1* | *0.01%* | *0.90%* | |
