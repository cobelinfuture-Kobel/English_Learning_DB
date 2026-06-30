# VOCAB_DB_S0A Duplicate Analysis

## Scope

Read-only duplicate audit of canonical sheet `total(15696)`.

## Duplicate Summary

| Duplicate class | Count |
| --- | ---: |
| Duplicate word groups | 3517 |
| Legitimate multi-sense groups | 2565 |
| Level progression groups | 1779 |
| Probable exact duplicate composite-key groups | 970 |
| Probable exact duplicate extra rows | 1074 |

Classification is based on normalized lowercase fields:

```text
word + guideword + level + part_of_speech + topic
```

## Class A: Legitimate Multi-Sense Entries

These are repeated words with different guidewords, parts of speech, topics, or sense metadata. They should be preserved as separate vocabulary entries.

| Word | Sense count | Levels | Sample source rows |
| --- | ---: | --- | --- |
| although | 2 | B1 | 5, 6 |
| and | 5 | A1, A2, B1 | 7, 8, 9, 10, 17 |
| as | 6 | A1, A2, B1 | 11, 15, 18, 19, 20 |
| but | 3 | A1, B1 | 13, 25, 10917 |
| close | 11 | A1, A2, B1, B2, C1, C2 | 14, 581, 1094, 1199, 1410 |
| after | 9 | A1, A2, B1, B2, C1, C2 | 16, 1627, 10838, 10839, 10840 |
| before | 9 | A1, A2, B1, C2 | 22, 23, 24, 1672, 10849 |
| if | 5 | A2, B1, B2 | 41, 42, 43, 44, 45 |

## Class B: Level Progression Entries

These are repeated words appearing at multiple CEFR levels. They are valid EVP behavior and should not be deduplicated by word alone.

| Word | Levels | Sample source rows |
| --- | --- | --- |
| and | A1, A2, B1 | 7, 8, 9, 10, 17 |
| as | A1, A2, B1 | 11, 15, 18, 19, 20 |
| but | A1, B1 | 13, 25, 10917 |
| close | A1, A2, B1, B2, C1, C2 | 14, 581, 1094, 1199, 1410 |
| after | A1, A2, B1, B2, C1, C2 | 16, 1627, 10838, 10839, 10840 |
| before | A1, A2, B1, C2 | 22, 23, 24, 1672, 10849 |
| fifth | A2, B1 | 32, 4027 |
| however | A2, C2 | 39, 4873 |
| like | A1, A2, B1, B2 | 48, 5352, 11077, 11078, 11079 |

## Class C: Probable Exact Duplicates

These repeat the same composite key. They need review before S1 decides whether to preserve, merge, or block duplicates.

| Word | Guideword | Level | POS | Topic | Rows | Count |
| --- | --- | --- | --- | --- | --- | ---: |
| glow |  | C2 | verb |  | 4226, 4227 | 2 |
| network | people | C1 | noun |  | 5636, 5638 | 2 |
| restart |  | C1 | verb |  | 7030, 7031 | 2 |
| refresh |  | C1 | verb |  | 7502, 7560 | 2 |
| underground |  | B2 | adjective | natural world | 10505, 10506 | 2 |
| get sth off your chest | idiom | C2 | phrase | communication | 11314, 12623 | 2 |
| quite a bit |  | B1 | phrase | describing things | 11317, 14147 | 2 |
| be on the ball | idiom | C1 | phrase | people: personality | 11318, 13489 | 2 |
| in attendance |  | C2 | phrase |  | 11319, 12635 | 2 |
| not have a clue |  | B2 | phrase |  | 11322, 12469 | 2 |

## Recommended Duplicate Policy

- Do not fail import on duplicate `word`.
- Preserve legitimate multi-sense and level-progression entries.
- Generate deterministic row-based ids so repeated words remain traceable.
- Warn on duplicate composite keys.
- Block probable exact duplicates from active generation until deduplication policy is implemented.
- Never collapse rows across CEFR levels without an explicit sense-level merge rule.
