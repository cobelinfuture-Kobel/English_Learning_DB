# VOCAB_DB_S0A Missing Part-of-Speech Analysis

## Scope

Read-only audit of rows where `Part of Speech` is empty in canonical sheet `total(15696)`.

## Missing POS Count by Level

| Level | Total rows | Missing POS | Missing POS % |
| --- | ---: | ---: | ---: |
| A1 | 784 | 30 | 3.8% |
| A2 | 1594 | 32 | 2.0% |
| B1 | 2937 | 33 | 1.1% |
| B2 | 4164 | 10 | 0.2% |
| C1 | 2410 | 2 | 0.1% |
| C2 | 3807 | 4 | 0.1% |
| Total | 15696 | 111 | 0.7% |

## Missing POS Count by Topic

| Topic | Missing POS rows |
| --- | ---: |
| `<missing topic>` | 86 |
| communication | 19 |
| describing things | 2 |
| animals | 1 |
| clothes | 1 |
| work | 1 |
| natural world | 1 |

## Findings

- Missing POS is small compared with missing topic: 111 rows total.
- Most missing POS rows also have missing topic, which compounds active-pool risk.
- A1, A2, and B1 contain most missing POS rows.
- Several early sample rows are common function words or broad entries with missing POS, such as `and`, `as`, and `although`.

## Candidate Recovery Strategies

1. Exact word and guideword lookup: infer POS from another row with the same `Base Word` and `Guideword`.
2. Word-level majority POS: infer POS only if the same word has one dominant POS across the workbook.
3. Closed-class whitelist: recover obvious function words such as conjunctions, prepositions, determiners, pronouns, and modal verbs from a controlled list.
4. Topic-sheet reconciliation: if a topic sheet row has the same word/guideword/level with POS populated, use it as a candidate recovery.
5. Manual review: keep all automatic POS recovery as `candidate_pos` until validated.

## Recommended Policy

- Import missing POS rows with warning metadata.
- Block missing POS rows from active generation until recovered.
- Do not assign POS from unconstrained language-model guesses.
- Keep both raw POS and recovered POS fields if recovery is implemented later.
