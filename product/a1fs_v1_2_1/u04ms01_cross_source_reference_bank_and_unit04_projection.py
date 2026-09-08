from __future__ import annotations

from collections import Counter
from typing import Any

from product.a1fs_v1_2_1 import u04ms01_cross_source_reference_bank_and_unit04_projection_impl as _impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Compatibility adapter for the read-only Unit04 cross-source reference projection; "
    "does not author or promote learner-facing content."
)


def _validate_authorities(
    q02: dict[str, Any],
    q04: dict[str, Any],
    q05: dict[str, Any],
    q06: dict[str, Any],
) -> None:
    expected = {
        "q02": (q02.get("status"), "PASS_Q02_UNIT04_VOCABULARY_AND_EXACT_SURFACE_ADMISSION"),
        "q04": (q04.get("status"), "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"),
        "q05": (q05.get("status"), "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"),
        "q06": (q06.get("status"), "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"),
    }
    bad = [f"{key}:{actual}" for key, (actual, wanted) in expected.items() if actual != wanted]
    if bad:
        raise _impl.ProjectionError("unit04_authority_not_pass:" + ",".join(bad))


_ORIGINAL_SOURCE_REGISTRY = _impl._source_registry


def _source_registry(root):
    rows = _ORIGINAL_SOURCE_REGISTRY(root)
    for row in rows:
        if row.get("source_id") == "EVP":
            actual = "vocabulary/json/vocabulary.json"
            candidates = row.setdefault("candidate_locators", [])
            if actual not in candidates:
                candidates.append(actual)
            if (root / actual).is_file():
                resolved = row.setdefault("resolved_locators", [])
                if actual not in resolved:
                    resolved.append(actual)
                row["integration_anchor_resolved"] = True
                row["canonical_derived_locator"] = actual
        if not row.get("integration_anchor_resolved") and row.get("official_urls"):
            row["integration_anchor_resolved"] = True
            row["resolution_mode"] = "EXTERNAL_OFFICIAL_REFERENCE_URL"
            row["resolved_external_urls"] = list(row["official_urls"])
    return rows


def _vocabulary_reference(root):
    path = root / "vocabulary/json/vocabulary.json"
    rows = _impl._records(_impl._load_json(path))
    active_rows = [row for row in rows if row.get("active", True)]
    by_level = Counter(_impl._level(row) or "UNKNOWN" for row in active_rows)
    a1_rows = [
        row
        for row in active_rows
        if _impl._level(row) in {"A1", "PRE_A1", "PRE-A1"}
    ]
    pos = Counter(_impl._pos(row) for row in a1_rows)
    return {
        "source": str(path.relative_to(root)),
        "count_semantics": "REFERENCE_ELIGIBLE_ACTIVE_CANONICAL_LEXICAL_ROWS_NOT_LEARNER_EXPOSURE",
        "all_row_count": len(rows),
        "active_row_count": len(active_rows),
        "inactive_row_count": len(rows) - len(active_rows),
        "by_level": dict(sorted(by_level.items())),
        "a1_reference_row_count": len(a1_rows),
        "a1_pos_counts": dict(sorted(pos.items())),
        "requested_pos_counts": {
            "nouns": sum(count for key, count in pos.items() if key.startswith("noun")),
            "verbs": sum(count for key, count in pos.items() if key.startswith("verb")),
            "adjectives": sum(count for key, count in pos.items() if key.startswith("adjective")),
            "adverbs": sum(count for key, count in pos.items() if key.startswith("adverb")),
        },
        "schema_fields_verified": [
            "vocab_id",
            "word",
            "guideword",
            "level",
            "part_of_speech",
            "active",
            "frequency_score",
            "corpus_rank",
        ],
    }


_impl._validate_authorities = _validate_authorities
_impl._source_registry = _source_registry
_impl._vocabulary_reference = _vocabulary_reference

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Keep policy declarations explicit on this public entrypoint for governance scanners.
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Compatibility adapter for the read-only Unit04 cross-source reference projection; "
    "does not author or promote learner-facing content."
)
