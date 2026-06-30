# VOCAB_DB_S0A Level Topic Analysis

## Scope

Read-only topic audit of canonical sheet `total(15696)` in `vocabulary/source/English Vocabulary Profile Online.xlsx`.

## CEFR Level x Topic Matrix

| Topic | A1 | A2 | B1 | B2 | C1 | C2 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| animals | 11 | 13 | 30 | 27 | 6 | 7 | 94 |
| arts and media | 15 | 43 | 73 | 70 | 13 | 28 | 242 |
| body and health | 19 | 35 | 68 | 107 | 38 | 89 | 356 |
| clothes | 14 | 27 | 22 | 16 | 5 | 4 | 88 |
| communication | 86 | 166 | 292 | 419 | 122 | 140 | 1225 |
| crime | 0 | 1 | 12 | 42 | 6 | 23 | 84 |
| describing things | 75 | 168 | 174 | 189 | 64 | 78 | 748 |
| education | 12 | 22 | 23 | 19 | 10 | 6 | 92 |
| food and drink | 46 | 71 | 62 | 37 | 21 | 16 | 253 |
| homes and buildings | 26 | 46 | 41 | 35 | 13 | 9 | 170 |
| money | 4 | 12 | 24 | 39 | 45 | 29 | 153 |
| natural world | 22 | 40 | 82 | 81 | 14 | 22 | 261 |
| people: actions | 48 | 91 | 253 | 379 | 71 | 110 | 952 |
| people: appearance | 17 | 17 | 20 | 26 | 5 | 6 | 91 |
| people: personality | 22 | 34 | 201 | 469 | 105 | 222 | 1053 |
| politics | 0 | 3 | 9 | 25 | 12 | 23 | 72 |
| relationships | 16 | 24 | 48 | 54 | 5 | 23 | 170 |
| shopping | 16 | 47 | 63 | 53 | 13 | 13 | 205 |
| technology | 7 | 30 | 41 | 67 | 10 | 6 | 161 |
| travel | 16 | 58 | 82 | 41 | 19 | 15 | 231 |
| work | 6 | 21 | 43 | 62 | 41 | 28 | 201 |
| Missing topic | 306 | 625 | 1274 | 1907 | 1772 | 2910 | 8794 |

## Top 10 Topics Per Level

| Level | Top topics |
| --- | --- |
| A1 | communication 86; describing things 75; people: actions 48; food and drink 46; homes and buildings 26; natural world 22; people: personality 22; body and health 19; people: appearance 17; relationships 16 |
| A2 | describing things 168; communication 166; people: actions 91; food and drink 71; travel 58; shopping 47; homes and buildings 46; arts and media 43; natural world 40; body and health 35 |
| B1 | communication 292; people: actions 253; people: personality 201; describing things 174; natural world 82; travel 82; arts and media 73; body and health 68; shopping 63; food and drink 62 |
| B2 | people: personality 469; communication 419; people: actions 379; describing things 189; body and health 107; natural world 81; arts and media 70; technology 67; work 62; relationships 54 |
| C1 | communication 122; people: personality 105; people: actions 71; describing things 64; money 45; work 41; body and health 38; food and drink 21; travel 19; natural world 14 |
| C2 | people: personality 222; communication 140; people: actions 110; body and health 89; describing things 78; money 29; arts and media 28; work 28; crime 23; politics 23 |

## Topic Coverage by Level

| Level | Non-empty topics covered | Missing topic count | Missing topic % |
| --- | ---: | ---: | ---: |
| A1 | 19 / 21 | 306 | 39.0% |
| A2 | 21 / 21 | 625 | 39.2% |
| B1 | 21 / 21 | 1274 | 43.4% |
| B2 | 21 / 21 | 1907 | 45.8% |
| C1 | 21 / 21 | 1772 | 73.5% |
| C2 | 21 / 21 | 2910 | 76.4% |

## Topic Sparsity Findings

- `A1` lacks non-empty entries for `crime` and `politics`.
- `A2` through `C2` have at least one entry in every detected non-empty topic.
- Missing topic rates become severe at advanced levels: `C1` 73.5% and `C2` 76.4%.
- Topic-based active pools are much smaller than raw level counts, especially for `C1`.

## Topic Pool Identification

### A1 Core Topic Pool

Recommended A1 core topics:

- communication
- describing things
- people: actions
- food and drink
- homes and buildings
- body and health
- people: appearance
- relationships
- shopping
- travel
- clothes
- education
- animals

Avoid using `crime` and `politics` at A1 because the canonical sheet has no A1 topic-labeled rows for them.

### A2 Expansion Topic Pool

Recommended A2 expansion topics:

- travel
- shopping
- homes and buildings
- arts and media
- natural world
- body and health
- technology
- relationships
- education
- work

### B1 Functional Topic Pool

Recommended B1 functional topics:

- communication
- people: actions
- people: personality
- describing things
- travel
- natural world
- arts and media
- body and health
- shopping
- work
- relationships

### B2/C1 Advanced Topic Pool

Recommended advanced topics:

- people: personality
- communication
- people: actions
- describing things
- body and health
- technology
- work
- money
- politics
- crime
- arts and media

## Import Implications

- Topic is required for active generation pools.
- Rows without topic should still be imported with warning metadata, but blocked from active topic-driven generation until mapped.
- Topic coverage is adequate for A1-B2 active pools, but C1 requires special handling because most C1 rows have no topic.
