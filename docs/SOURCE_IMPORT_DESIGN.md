# EGP_DB_S1 Source Import Design Scan

## Scope

This document records the read-only inspection and import architecture design for the English Learning Database.

This step does not generate learning content, dialogues, questions, images, audio, JSON conversion output, or a C# project. Source files remain read-only.

## Source Files

| Source file | Status | Classification | Use |
| --- | --- | --- | --- |
| `grammar_profile/source/English Grammar Profile Online.xlsx` | Found | Grammar source | Authority source for English Grammar Profile records. |
| `docs/A1_C1_情境.txt` | Found | Theme source | Level-based theme/category source for future theme mapping. |

## Excel Inspection

Workbook: `grammar_profile/source/English Grammar Profile Online.xlsx`

### Sheets

| Sheet | Header row | Data rows | Columns |
| --- | ---: | ---: | ---: |
| `Data` | 1 | 1222 | 8 |

### Columns

The `Data` sheet contains these columns:

1. `id`
2. `SuperCategory`
3. `SubCategory`
4. `Level`
5. `Lexical Range`
6. `Guideword`
7. `Can-do statement`
8. `Example`

### CEFR Level Distribution

| Level | Count |
| --- | ---: |
| A1 | 109 |
| A2 | 291 |
| B1 | 338 |
| B2 | 243 |
| C1 | 129 |
| C2 | 112 |

### Duplicate IDs

No duplicate values were detected in the `id` column.

### Missing Values

| Column | Missing count |
| --- | ---: |
| `id` | 0 |
| `SuperCategory` | 0 |
| `SubCategory` | 0 |
| `Level` | 0 |
| `Lexical Range` | 0 |
| `Guideword` | 0 |
| `Can-do statement` | 4 |
| `Example` | 4 |

Rows with missing required grammar fields:

| Excel row | id | Level | Guideword | Missing fields |
| ---: | --- | --- | --- | --- |
| 214 | `1741163708343x852921288542131100` | B1 | `FORM: 'WHICH', 'WHOSE'` | `Can-do statement`, `Example` |
| 422 | `1741163709241x116456418775643170` | B2 | `FORM: NEGATIVE` | `Can-do statement`, `Example` |
| 838 | `1741163712056x976576319443112100` | C2 | `PRESENT PERFECT CONTINUOUS COMMENT` | `Can-do statement`, `Example` |
| 1001 | `1741163713638x947110035097887900` | B1 | `General comment` | `Can-do statement`, `Example` |

### Sample 10 Records

The first 10 source records were sampled during terminal inspection. They all come from sheet `Data` and include these ids and levels:

| # | id | Level | SuperCategory | SubCategory | Guideword |
| ---: | --- | --- | --- | --- | --- |
| 1 | `1741163706316x198445876411383900` | A2 | ADJECTIVES | combining | `FORM: COMBINING TWO ADJECTIVES WITH 'BUT'` |
| 2 | `1741163706316x926291459998112000` | A1 | ADJECTIVES | combining | `FORM: COMBINING TWO ADJECTIVES WITH 'AND'` |
| 3 | `1741163706317x106352194611554880` | B2 | ADJECTIVES | combining | `FORM: COMPOUND ADJECTIVES` |
| 4 | `1741163706317x286016181282525020` | B1 | ADJECTIVES | combining | `FORM: COMBINING MORE THAN TWO ADJECTIVES` |
| 5 | `1741163706317x294956758156726500` | B1 | ADJECTIVES | combining | `FORM: COMBINING THE SAME COMPARATIVE ADJECTIVE WITH 'AND'` |
| 6 | `1741163706317x456519880167863600` | B1 | ADJECTIVES | combining | `FORM: BEFORE THE NOUN` |
| 7 | `1741163706317x556163615013575200` | B1 | ADJECTIVES | combining | `FORM: COMPOUND ADJECTIVES` |
| 8 | `1741163706317x616093618641182500` | B1 | ADJECTIVES | combining | `FORM: COMBINING COMPARATIVE ADJECTIVES WITH 'AND'` |
| 9 | `1741163706317x691908853350257800` | B2 | ADJECTIVES | combining | `FORM: PHRASES MODIFYING NOUNS` |
| 10 | `1741163706318x964351339627643300` | C1 | ADJECTIVES | combining | `FORM: COMPOUND ADJECTIVES` |

## Theme Inspection

Source: `docs/A1_C1_情境.txt`

### Levels

All expected levels were found:

- `A1`
- `A1+`
- `A2`
- `A2+`
- `B1`
- `B1+`
- `B2`
- `B2+`
- `C1`

### Theme Categories

Only numbered or bullet-list entries are treated as direct theme category mappings. Descriptive paragraphs are retained as level notes, not categories.

| Level | Category count | Categories |
| --- | ---: | --- |
| A1 | 9 | 個人資訊與社交問候; 日常生活與作息; 學校與教室情境; 居家與生活環境; 購物與基礎交易; 飲食與餐廳點餐; 興趣、休閒與能力; 旅遊、交通與天氣; 健康與醫療 |
| A1+ | 0 | No explicit category list; descriptive paragraph only. |
| A2 | 3 | 日常實務與當地環境; 出行與消費; 社交與討論 |
| A2+ | 0 | No explicit category list; descriptive paragraph only. |
| B1 | 3 | 旅遊與海外生活; 職場與商業環境; 個人表達與社交 |
| B1+ | 0 | No explicit category list; descriptive paragraph only. |
| B2 | 3 | 專業與學術情境; 深入辯論與會議; 母語人士交流 |
| B2+ | 0 | No explicit category list; descriptive paragraph only. |
| C1 | 3 | 高難度職場與社交; 言外之意與複雜文本; 精準表達 |

### Theme Duplicate Check

No duplicate explicit theme category names were detected within the same level.

No duplicate explicit theme category names were detected across levels.

### Missing Mappings

These levels exist in the source file but do not have explicit category mappings:

- `A1+`
- `A2+`
- `B1+`
- `B2+`

Importers should preserve their descriptive notes but should not invent categories during import.

## Import Architecture Design

### `grammar_profile/json/grammar_profile.json`

Purpose: canonical normalized grammar records derived from the English Grammar Profile workbook after validation.

Recommended structure:

```json
{
  "source": {
    "file": "grammar_profile/source/English Grammar Profile Online.xlsx",
    "sheet": "Data",
    "authority": "English Grammar Profile"
  },
  "records": [
    {
      "id": "",
      "level": "",
      "category": "",
      "subcategory": "",
      "lexical_range": "",
      "guideword": "",
      "can_do_statement": "",
      "example": "",
      "source": {
        "sheet": "",
        "row": 0
      }
    }
  ]
}
```

Field mapping:

| Target field | Source column |
| --- | --- |
| `id` | `id` |
| `level` | `Level` |
| `category` | `SuperCategory` |
| `subcategory` | `SubCategory` |
| `lexical_range` | `Lexical Range` |
| `guideword` | `Guideword` |
| `can_do_statement` | `Can-do statement` |
| `example` | `Example` |

### `grammar_profile/mapping/level_mapping.json`

Purpose: normalize CEFR level values and define allowed grammar levels.

Recommended structure:

```json
{
  "grammar_levels": ["A1", "A2", "B1", "B2", "C1", "C2"],
  "theme_levels": ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1"],
  "normalization": {}
}
```

Design note: grammar source uses standard CEFR levels including `C2`; theme source uses plus levels and stops at `C1`. These should be modeled as related but separate level sets.

### `themes/theme_mapping.json`

Purpose: normalized theme categories and level notes derived from `docs/A1_C1_情境.txt`.

Recommended structure:

```json
{
  "source": {
    "file": "docs/A1_C1_情境.txt"
  },
  "levels": [
    {
      "level": "",
      "notes": [],
      "categories": [
        {
          "name": "",
          "description": "",
          "source_line": 0
        }
      ]
    }
  ]
}
```

Design note: plus levels with descriptive paragraphs but no explicit category list should have `categories: []` and preserve the paragraph text under `notes`.

## Validation Design

Required normalized grammar fields:

- `id`
- `level`
- `category`
- `can_do_statement`
- `example`

Validation rules:

1. Duplicate ID check: fail if any normalized grammar record id appears more than once.
2. Empty statement check: fail if `can_do_statement` is empty after trimming whitespace.
3. Empty example check: fail if `example` is empty after trimming whitespace.
4. Invalid CEFR level check: fail if grammar `level` is not one of `A1`, `A2`, `B1`, `B2`, `C1`, `C2`.
5. Required field check: fail if any required normalized field is missing.
6. Theme level check: fail if a theme level is not one of `A1`, `A1+`, `A2`, `A2+`, `B1`, `B1+`, `B2`, `B2+`, `C1`.
7. Theme duplicate check: fail or warn on duplicate category names within the same level.
8. Theme missing mapping check: warn, not fail, when a level has descriptive notes but no explicit category list.

## Integration Risks

- The workbook currently has 4 rows that fail required `can_do_statement` and `example` validation.
- Theme plus levels exist but do not all have explicit category mappings.
- Grammar levels and theme levels are not identical; C2 exists in grammar, while plus levels exist only in theme source.
- Import must be deterministic and idempotent. Re-running the importer should produce stable ids and stable output ordering.
- Validators must run before any generated JSON is written.
- Downstream generators must consume validated JSON only; they must not read raw source files directly.

## Readiness

This project is ready to design and implement the import pipeline, but not ready to write final generated JSON without validation handling.

Minimum next step:

- Implement source import with validation-first behavior.
- Treat the 4 missing grammar records as validation failures or explicitly excluded records.
- Preserve theme plus-level descriptions without inventing categories.
