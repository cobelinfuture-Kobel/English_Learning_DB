# VOCAB_DB_S0A Vocabulary Level Pool Design

## Scope

Design-only vocabulary pool policy. No final JSON profiles are created in this step.

Active-ready means a row has:

- non-empty `Base Word`
- valid `Level`
- non-empty `Topic`
- non-empty `Part of Speech`

Rows missing topic or POS should be imported with warnings but blocked from active generation until resolved.

## Pool Counts

| Pool | Native rows | Active-ready rows | Blocked missing required rows |
| --- | ---: | ---: | ---: |
| A1 | 784 | 471 | 313 |
| A2 | 1594 | 965 | 629 |
| B1 | 2937 | 1654 | 1283 |
| B2 | 4164 | 2253 | 1911 |
| C1 | 2410 | 638 | 1772 |

## A1 Vocabulary Pool

Active rules:

- Native A1 rows only.
- Require topic and POS.
- Prefer core concrete topics: communication, describing things, people: actions, food and drink, homes and buildings, body and health, clothes, travel, shopping.

Blocked rules:

- Missing topic.
- Missing POS.
- C2 entries.
- Probable exact duplicates until reviewed.

## A1 Plus Candidate Pool

Candidate policy:

- Base active pool: A1 active-ready rows.
- Candidate source: active-ready A2 rows.
- Candidate limit: 70 rows, based on 15% of A1 active-ready count.
- Candidate selection should be deterministic first-pass sorted by source row until a complexity selector exists.

Topic requirements:

- Prefer A2 expansion topics that extend A1 life contexts: travel, shopping, homes and buildings, arts and media, natural world, body and health.

POS requirements:

- Prefer nouns, verbs, adjectives, and short phrases.
- Avoid dense phrase/idiom-heavy rows.

## A2 Vocabulary Pool

Active rules:

- Native A2 rows only.
- Require topic and POS.
- Allow all 21 detected topics, but prioritize high-frequency practical topics.

Blocked rules:

- Missing topic.
- Missing POS.
- C2 entries.
- Probable exact duplicates until reviewed.

## A2 Plus Candidate Pool

Candidate policy:

- Base active pool: A2 active-ready rows.
- Candidate source: active-ready B1 rows.
- Candidate limit: 144 rows, based on 15% of A2 active-ready count.
- Candidate selection should be deterministic first-pass sorted by source row.

Topic requirements:

- Prefer B1 functional contexts: communication, people: actions, people: personality, travel, natural world, arts and media, shopping, work.

POS requirements:

- Allow phrasal verbs and phrases only if topic is present and row is not a probable exact duplicate.

## B1 Vocabulary Pool

Active rules:

- Native B1 rows only.
- Require topic and POS.
- Prioritize communication, people: actions, people: personality, describing things, travel, natural world, arts and media, body and health, shopping, work.

Blocked rules:

- Missing topic.
- Missing POS.
- Probable exact duplicates until reviewed.

## B1 Plus Candidate Pool

Candidate policy:

- Base active pool: B1 active-ready rows.
- Candidate source: active-ready B2 rows.
- Candidate limit: 248 rows, based on 15% of B1 active-ready count.
- Candidate selection should be deterministic first-pass sorted by source row.

Topic requirements:

- Prefer transition topics: work, technology, relationships, body and health, communication, people: personality.

POS requirements:

- Allow more phrase and phrasal-verb entries, but keep exact duplicate warnings out of active generation.

## B2 Vocabulary Pool

Active rules:

- Native B2 rows only.
- Require topic and POS.
- Support broader abstract and professional topics.

Blocked rules:

- Missing topic.
- Missing POS.
- Probable exact duplicates until reviewed.

## B2 Plus Candidate Pool

Candidate policy:

- Base active pool: B2 active-ready rows.
- Candidate source: active-ready C1 rows.
- Candidate limit: 337 rows, based on 15% of B2 active-ready count.
- Candidate selection should be deterministic first-pass sorted by source row.

Topic requirements:

- Prefer advanced but still C1-bounded topics: communication, people: personality, people: actions, money, work, body and health, technology, arts and media.

POS requirements:

- Phrases are allowed, but idiom-heavy rows should be review-required.

## C1 Vocabulary Pool

Active rules:

- Native C1 rows only.
- Require topic and POS.
- No C2 candidate borrowing.

Blocked rules:

- Missing topic.
- Missing POS.
- C2 entries.
- Probable exact duplicates until reviewed.

Risk:

- C1 has only 638 active-ready rows after topic/POS filtering, despite 2410 native rows. Missing-topic recovery is important before relying on C1 pool breadth.

## Cross-Level Rules

- C2 remains imported data only and should not be active.
- Plus pools borrow from the next CEFR level only.
- Candidate count should not exceed 15% of active-ready base pool count.
- Active pools must exclude missing topic/POS rows.
- Active pools must exclude probable exact duplicate rows until deduplication policy is implemented.
- All generated future profile files should preserve traceability to source row.
