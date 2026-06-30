# VOCAB_DB_S0 Source Import Design Scan

## Scope

This document records the read-only inspection and import architecture design for the English Vocabulary Profile source workbook.

No JSON conversion was performed. No source file was modified. No learning content, dialogue, question, image, audio, or C# project was generated.

## Source File

| Source file | Status | Classification | Intended use |
| --- | --- | --- | --- |
| `vocabulary/source/English Vocabulary Profile Online.xlsx` | Found | Vocabulary source | Authority source for vocabulary records, CEFR level, topic, part of speech, and guideword/sense information. |

## Workbook Inspection

### Sheets

The workbook contains one canonical total sheet and 21 topic sheets.

| Sheet | Rows | Columns |
| --- | ---: | ---: |
| `total(15696)` | 15696 | 6 |
| `animal(94)` | 94 | 6 |
| `arts and media(242)` | 242 | 6 |
| `body and health(356)` | 356 | 6 |
| `clothes(88)` | 88 | 6 |
| `communication(1225)` | 1225 | 6 |
| `crime(84)` | 84 | 6 |
| `describing things(748)` | 748 | 6 |
| `education(92)` | 92 | 6 |
| `food and drink(253)` | 253 | 6 |
| `homes and buildings(170)` | 170 | 6 |
| `money(153)` | 153 | 6 |
| `natural world(261)` | 261 | 6 |
| `people-actions(952)` | 952 | 6 |
| `people-appearace(91)` | 91 | 6 |
| `people-personality(1053)` | 1053 | 6 |
| `politics(72)` | 72 | 6 |
| `relationships(170)` | 170 | 6 |
| `shopping(205)` | 205 | 6 |
| `technology(161)` | 161 | 6 |
| `travel(231)` | 231 | 6 |
| `work(201)` | 201 | 6 |

Design decision: use `total(15696)` as the canonical import sheet. Topic sheets should be treated as cross-check sources because they duplicate subsets of the total sheet.

### Column Names

All inspected sheets use the same columns:

1. `Base Word`
2. `Guideword`
3. `Level`
4. `Part of Speech`
5. `Topic`
6. `Details`

Recommended normalized field mapping:

| Target field | Source column |
| --- | --- |
| `word` | `Base Word` |
| `guideword` | `Guideword` |
| `level` | `Level` |
| `part_of_speech` | `Part of Speech` |
| `topic` | `Topic` |
| `details` | `Details` |
| `source_sheet` | workbook sheet name |
| `source_row` | Excel row number |

### CEFR Distribution

From canonical sheet `total(15696)`:

| Level | Count |
| --- | ---: |
| A1 | 784 |
| A2 | 1594 |
| B1 | 2937 |
| B2 | 4164 |
| C1 | 2410 |
| C2 | 3807 |

### Topic Distribution

From canonical sheet `total(15696)`, 21 unique non-empty topics were detected:

| Topic | Count |
| --- | ---: |
| communication | 1225 |
| people: personality | 1053 |
| people: actions | 952 |
| describing things | 748 |
| body and health | 356 |
| natural world | 261 |
| food and drink | 253 |
| arts and media | 242 |
| travel | 231 |
| shopping | 205 |
| work | 201 |
| relationships | 170 |
| homes and buildings | 170 |
| technology | 161 |
| money | 153 |
| animals | 94 |
| education | 92 |
| people: appearance | 91 |
| clothes | 88 |
| crime | 84 |
| politics | 72 |

Missing topic values: 8794.

### Part-of-Speech Distribution

From canonical sheet `total(15696)`:

| Part of speech | Count |
| --- | ---: |
| noun | 5167 |
| phrase | 3656 |
| adjective | 2420 |
| verb | 2318 |
| adverb | 801 |
| phrasal verb | 728 |
| preposition | 233 |
| pronoun | 101 |
| determiner | 85 |
| modal verb | 37 |
| exclamation | 33 |
| auxiliary verb | 6 |

Missing part-of-speech values: 111.

### Duplicate Detection

From canonical sheet `total(15696)`:

- Duplicate `word` count: 3517.
- Duplicate composite key count: 970.

Important interpretation:

- Duplicate `word` values are expected in EVP data because the same word can appear with different guidewords, levels, meanings, topics, or parts of speech.
- A future importer should not fail merely because `word` is repeated.
- The stricter duplicate check should use a normalized composite key such as:

```text
word + guideword + level + part_of_speech + topic
```

Composite duplicates should be reported as warnings first because some repeated rows may still reflect multiple source locations or topic-sheet duplication. If the canonical `total(15696)` sheet has exact repeated composite entries, S1/S2 should decide whether to preserve, merge, or block them.

Sample duplicate composite keys detected:

| word | guideword | level | part_of_speech | topic | Count |
| --- | --- | --- | --- | --- | ---: |
| glow |  | C2 | verb |  | 2 |
| network | people | C1 | noun |  | 2 |
| restart |  | C1 | verb |  | 2 |
| refresh |  | C1 | verb |  | 2 |
| underground |  | B2 | adjective | natural world | 2 |
| get sth off your chest | idiom | C2 | phrase | communication | 2 |
| quite a bit |  | B1 | phrase | describing things | 2 |
| be on the ball | idiom | C1 | phrase | people: personality | 2 |
| in attendance |  | C2 | phrase |  | 2 |
| not have a clue |  | B2 | phrase |  | 2 |

### Missing Value Detection

From canonical sheet `total(15696)`:

| Column | Missing count | Required for import? | Initial validation action |
| --- | ---: | --- | --- |
| `Base Word` | 0 | Yes | Fail if missing |
| `Guideword` | 8407 | No | Allow empty |
| `Level` | 0 | Yes | Fail if missing |
| `Part of Speech` | 111 | Yes | Warn or block until resolved |
| `Topic` | 8794 | Yes | Warn or block until resolved |
| `Details` | 0 | No | Allow placeholder value |

The user-required fields include `topic` and `part_of_speech`, but the source has substantial missing topics and 111 missing part-of-speech values. S1/S2 must decide whether to block those rows, import them with warning flags, or assign a controlled placeholder such as `unmapped`.

### Sample 10 Rows

From canonical sheet `total(15696)`:

| # | Base Word | Guideword | Level | Part of Speech | Topic | Details |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | cattle |  | B1 |  | animals | Details |
| 2 | clothes |  | A1 |  | clothes | Details |
| 3 | albeit |  | C2 |  |  | Details |
| 4 | although | BUT | B1 |  | communication | Details |
| 5 | although | DESPITE | B1 |  | communication | Details |
| 6 | and | ALSO | A1 |  | communication | Details |
| 7 | and | AFTER | A1 |  | communication | Details |
| 8 | and | AFTER VERB | A2 |  | communication | Details |
| 9 | and | EMPHASIZE | B1 |  | communication | Details |
| 10 | as | BECAUSE | A2 |  | communication | Details |

## Vocabulary Architecture Design

### `vocabulary/json/vocabulary_profile.json`

Purpose: canonical normalized vocabulary records from the `total(15696)` sheet after validation.

Recommended structure:

```json
{
  "source": {
    "file": "vocabulary/source/English Vocabulary Profile Online.xlsx",
    "sheet": "total(15696)",
    "authority": "English Vocabulary Profile"
  },
  "records": [
    {
      "id": "",
      "word": "",
      "guideword": "",
      "level": "",
      "part_of_speech": "",
      "topic": "",
      "details": "",
      "source_sheet": "",
      "source_row": 0,
      "import_warnings": []
    }
  ]
}
```

Recommended id policy:

- Generate deterministic ids from canonical source row and normalized fields.
- Example shape: `evp_total_000002` or a stable hash over `source_sheet`, `source_row`, `word`, `guideword`, `level`, `part_of_speech`, and `topic`.
- Do not use `word` alone as the id because EVP contains many repeated words.

### `vocabulary/mapping/vocabulary_level_mapping.json`

Purpose: define allowed EVP CEFR levels and their active status in the English learning database.

Recommended structure:

```json
{
  "levels": {
    "A1": {"active": true},
    "A2": {"active": true},
    "B1": {"active": true},
    "B2": {"active": true},
    "C1": {"active": true},
    "C2": {
      "active": false,
      "preserve_as_imported_data": true
    }
  }
}
```

Design note: C2 should be preserved for data integrity but excluded from active A1-C1 generation until a future C2 profile exists.

### `vocabulary/mapping/topic_mapping.json`

Purpose: normalize topic labels and support alignment with existing theme profiles.

Recommended structure:

```json
{
  "source_topics": [],
  "normalization": {
    "people-actions": "people: actions",
    "people-appearace": "people: appearance",
    "people-personality": "people: personality"
  },
  "topic_to_theme_candidates": {}
}
```

Design note: workbook sheet names include typos or alternate separators, such as `people-appearace(91)`, while canonical topic labels use `people: appearance`. Topic mapping should normalize sheet-derived labels and cell-derived labels separately.

## Validation Design

Required normalized fields:

- `word`
- `level`
- `topic`
- `part_of_speech`

Required checks:

1. Duplicate words:
   - Warn on duplicate `word`.
   - Fail or warn on duplicate composite key depending on S1/S2 policy.
   - Never use `word` alone as the primary key.
2. Invalid CEFR level:
   - Allowed values: `A1`, `A2`, `B1`, `B2`, `C1`, `C2`.
   - Any other value should fail validation.
3. Missing topic:
   - Current source has 8794 missing topics.
   - Rows with missing `topic` should be blocked from active generation unless explicitly mapped to a controlled placeholder.
4. Missing part_of_speech:
   - Current source has 111 missing part-of-speech values.
   - Rows with missing `part_of_speech` should be blocked from active generation unless resolved.
5. Required word:
   - `Base Word` is complete in this source; future imports should still fail if empty.
6. Required level:
   - `Level` is complete in this source; future imports should still fail if empty.
7. Canonical sheet check:
   - Importer should read `total(15696)` only for canonical output.
   - Topic sheets should be used for reconciliation, not appended into the canonical record list.

## Integration Risks

- Large missing topic count means active vocabulary pools will be incomplete unless missing-topic policy is defined.
- Many source rows are phrases or phrasal verbs, so downstream systems must not assume vocabulary entries are single words.
- Duplicate words are normal in EVP and must not be treated as fatal without sense-level keys.
- The `Details` column currently contains the placeholder value `Details` in sampled rows, so it should not be assumed to contain a definition.
- Topic sheet names and topic cell values are not always identical, and at least one sheet name appears misspelled: `people-appearace(91)`.
- C2 has 3807 records, much larger than C1, so preserving C2 without activating it must be explicit in level mapping.
- Vocabulary topics should later be aligned with theme profiles, but they are not the same taxonomy.

## Readiness for Next Step

Status: ready for `VOCAB_DB_S1_SourceImport_Fix` after validation policy is confirmed.

Minimum S1 decisions:

- Whether missing `topic` and `part_of_speech` rows are imported with warnings, blocked from active use, or excluded.
- Whether duplicate composite keys are preserved or deduplicated.
- Whether canonical ids use row-based ids or stable hashes.
- Whether `Details` is retained as a raw placeholder field or ignored until richer source data exists.
