# EGP_DB_S5 Theme Profile Design Scan

## Scope

This is a design-only scan for theme profile architecture. It does not generate learning content, dialogues, questions, images, audio, JSON theme profiles, or a C# project.

Source files inspected:

- `themes/theme_mapping.json`
- `level_profiles/A1.json`
- `level_profiles/A1_plus.json`
- `level_profiles/A2.json`
- `level_profiles/A2_plus.json`
- `level_profiles/B1.json`
- `level_profiles/B1_plus.json`
- `level_profiles/B2.json`
- `level_profiles/B2_plus.json`
- `level_profiles/C1.json`
- `docs/A1_C1_情境.txt`

## Theme Mapping Scan

| Level | Mapping status | Category count | Notes count | Category source |
| --- | --- | ---: | ---: | --- |
| `A1` | `mapped` | 9 | 1 | Native explicit categories |
| `A1_plus` | `descriptive_only` | 0 | 2 | Inherit from `A1` plus extension notes |
| `A2` | `mapped` | 3 | 1 | Native explicit categories |
| `A2_plus` | `descriptive_only` | 0 | 2 | Inherit from `A2` plus extension notes |
| `B1` | `mapped` | 3 | 1 | Native explicit categories |
| `B1_plus` | `descriptive_only` | 0 | 2 | Inherit from `B1` plus extension notes |
| `B2` | `mapped` | 3 | 1 | Native explicit categories |
| `B2_plus` | `descriptive_only` | 0 | 2 | Inherit from `B2` plus extension notes |
| `C1` | `mapped` | 3 | 1 | Native explicit categories |

### Levels With Explicit Categories

- `A1`
- `A2`
- `B1`
- `B2`
- `C1`

### Levels With `descriptive_only` Status

- `A1_plus`
- `A2_plus`
- `B1_plus`
- `B2_plus`

### Missing Category Mappings

The plus levels exist in `theme_mapping.json`, but they do not contain explicit `categories` arrays:

- `A1_plus`
- `A2_plus`
- `B1_plus`
- `B2_plus`

This should not block downstream generation. Theme profiles should inherit base CEFR categories and attach plus-level notes as extension constraints.

## Level Profile Relationship Scan

All active level profiles have matching `theme_level` keys in `themes/theme_mapping.json`.

| Profile | Active | CEFR base | Theme level | Theme mapping status |
| --- | --- | --- | --- | --- |
| `A1` | true | `A1` | `A1` | `mapped` |
| `A1_plus` | true | `A1` | `A1_plus` | `descriptive_only` |
| `A2` | true | `A2` | `A2` | `mapped` |
| `A2_plus` | true | `A2` | `A2_plus` | `descriptive_only` |
| `B1` | true | `B1` | `B1` | `mapped` |
| `B1_plus` | true | `B1` | `B1_plus` | `descriptive_only` |
| `B2` | true | `B2` | `B2` | `mapped` |
| `B2_plus` | true | `B2` | `B2_plus` | `descriptive_only` |
| `C1` | true | `C1` | `C1` | `mapped` |

## Proposed Theme Profile Schema

Future S6 output path:

- `themes/profiles/A1.json`
- `themes/profiles/A1_plus.json`
- `themes/profiles/A2.json`
- `themes/profiles/A2_plus.json`
- `themes/profiles/B1.json`
- `themes/profiles/B1_plus.json`
- `themes/profiles/B2.json`
- `themes/profiles/B2_plus.json`
- `themes/profiles/C1.json`

Recommended schema:

```json
{
  "level": "A1_plus",
  "cefr_base": "A1",
  "theme_source": {
    "mapping_file": "themes/theme_mapping.json",
    "source_file": "docs/A1_C1_情境.txt"
  },
  "mapping_status": "inherited_with_extension_notes",
  "inherited_from": "A1",
  "theme_categories": [
    {
      "name": "",
      "description": "",
      "source_level": "",
      "source_line": 0,
      "inherited": true
    }
  ],
  "subthemes": [],
  "communicative_functions": [],
  "allowed_contexts": [],
  "blocked_contexts": [],
  "learner_output_modes": [],
  "media_requirements": {
    "image_required": false,
    "audio_required": false,
    "image_complexity": "none",
    "audio_complexity": "none"
  },
  "exam_alignment": {
    "framework": "general_cefr",
    "cambridge_alignment": "undecided"
  },
  "generation_constraints": {
    "learning_content_generation_enabled": false,
    "dialogue_generation_enabled": false,
    "question_generation_enabled": false,
    "must_use_theme_category": true,
    "allow_inherited_categories": true,
    "extension_notes": []
  },
  "validation_rules": {
    "required_keys": [
      "level",
      "cefr_base",
      "theme_source",
      "mapping_status",
      "theme_categories",
      "validation_rules"
    ],
    "require_at_least_one_theme_category": true,
    "allow_descriptive_only_source_when_inherited": true,
    "duplicate_theme_category_check": true,
    "theme_level_must_match_level_profile": true
  }
}
```

## Inheritance Policy

Plus-level profiles should not invent new categories. They should inherit base CEFR categories and add plus-level notes as constraints.

| Profile | Inherits categories from | Adds extension notes from | Final category policy |
| --- | --- | --- | --- |
| `A1` | None | `A1` notes | Native `A1` categories only |
| `A1_plus` | `A1` | `A1_plus` notes | `A1` categories plus A1+ extension notes |
| `A2` | None | `A2` notes | Native `A2` categories only |
| `A2_plus` | `A2` | `A2_plus` notes | `A2` categories plus A2+ extension notes |
| `B1` | None | `B1` notes | Native `B1` categories only |
| `B1_plus` | `B1` | `B1_plus` notes | `B1` categories plus B1+ extension notes |
| `B2` | None | `B2` notes | Native `B2` categories only |
| `B2_plus` | `B2` | `B2_plus` notes | `B2` categories plus B2+ extension notes |
| `C1` | None | `C1` notes | Native `C1` categories only |

### Plus-Level Operational Rule

For `descriptive_only` plus levels:

1. Read the plus-level notes from `theme_mapping.json`.
2. Copy categories from the base CEFR level.
3. Mark copied categories with `inherited: true`.
4. Set `mapping_status` to `inherited_with_extension_notes`.
5. Preserve plus-level notes under `generation_constraints.extension_notes`.
6. Do not create new category names from prose notes.

## Proposed Field Semantics

### `theme_categories`

Canonical list of selectable theme categories. For native mapped levels, these come directly from `theme_mapping.json`. For plus levels, these are inherited from the base CEFR profile.

### `subthemes`

Reserved for future finer-grained classification. S6 should initialize as an empty list unless a source category already has explicit child items.

### `communicative_functions`

High-level speech or writing functions implied by theme categories, such as introducing oneself, describing routines, making arrangements, negotiating, debating, or presenting. S6 should keep these as controlled tags, not generated prompts.

### `allowed_contexts`

Context tags derived from category names and descriptions. These constrain future generators without creating content.

### `blocked_contexts`

Contexts that are inappropriate for the level. For lower levels, this may include abstract debate, hostile negotiation, legal/medical professional contexts, or dense academic discussion.

### `learner_output_modes`

Allowed mode tags such as `word`, `phrase`, `sentence`, `short_answer`, `short_message`, `paragraph`, `discussion`, `presentation`, or `formal_writing`.

### `media_requirements`

Whether future image/audio generation is required or optional for this level. S5 does not decide final generation behavior; it only defines the schema.

### `exam_alignment`

Alignment target for future validation and reporting. Current recommendation is `general_cefr` until Cambridge-only alignment is explicitly required.

## Validation Design

S6 should add tests for:

- All 9 theme profile files exist.
- Every active level profile has a matching theme profile.
- Every theme profile contains the required schema keys.
- Native mapped levels contain their native categories.
- Plus levels inherit categories from their base CEFR level.
- Plus levels preserve extension notes.
- `C1` uses native C1 categories only.
- No theme profile creates a C2 active theme profile.
- No generated learning/dialogue/question/media content appears in theme profiles.

## Unresolved Risks

### Plus-Level Category Ambiguity

`A1_plus`, `A2_plus`, `B1_plus`, and `B2_plus` contain prose notes but no explicit category lists. Inheritance avoids data fabrication, but it may make plus levels feel too similar to their base CEFR level unless extension notes are enforced by validators.

### Advanced Level Theme Breadth

`B2` and `C1` categories are broad and cover professional, academic, social, and abstract contexts. Future profiles may need controlled subtheme expansion to prevent overly broad generator targets.

### B1 Plus and B2 Overlap

`B1_plus` notes emphasize opinion, debate, polysemy, and broad-topic pros/cons, which overlap with `B2` categories such as formal debate and meetings. S6 should keep `B1_plus` inherited from B1 and use extension notes to limit complexity.

### Exam Alignment Scope

It is unresolved whether `exam_alignment` should target Cambridge exams only or general CEFR outcomes. Current design keeps this as `general_cefr` with Cambridge alignment undecided.

### Media Requirements by Level

It is unresolved whether image/audio requirements should vary by level. Lower levels may benefit from images and slower audio, while advanced levels may need less visual support and more authentic audio. S6 should keep media fields declarative and disabled by default.

## Readiness for EGP_DB_S6_ThemeProfile_Fix

Status: Ready.

The imported `theme_mapping.json` and existing `level_profiles/*.json` provide enough structure to generate deterministic theme profile JSON files in S6.

S6 should:

- Create `themes/profiles/`.
- Generate 9 theme profile JSON files.
- Apply inheritance for plus levels.
- Preserve source notes and category source lines.
- Add tests for matching level profiles, required keys, inheritance, and no C2 active profile.
- Avoid generating learning content, dialogues, questions, images, or audio.
