#!/usr/bin/env python3
"""Deterministically materialize Unit05 Q06 sentence assets from the approved Unit05 Q02-Q05 scope.

The safe seed contains only Unit05-generated semantic propositions and the safe predecessor
collision index required to preserve dedup lineage. Private U01/U03 sentence bodies are not stored.
"""
from __future__ import annotations

import base64
import hashlib
import json
import lzma
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json"
Q02_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
Q03_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json"
Q04_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q04_be_chunk_authority.json"
Q05_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json"
SAFE_SEED_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_u05_q06_safe_seed.json"


def _safe_seed() -> dict[str, Any]:
    return json.loads(SAFE_SEED_PATH.read_text(encoding="utf-8"))


class U05Q06BuildError(ValueError):
    pass


def _decode_seed(value: str) -> Any:
    return json.loads(lzma.decompress(base64.b64decode(value)).decode("utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def normalize_sentence(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip().casefold()
    value = re.sub(r"\s+([,.!?;:])", r"\1", value)
    return re.sub(r"[.!?]+$", "", value).strip()


def _cap_subject(value: str) -> str:
    return value[:1].upper() + value[1:] if value else value


def _full_aff(prop: Mapping[str, Any]) -> str:
    return f"{_cap_subject(str(prop['subject_text']))} {prop['be_form']} {prop['complement']}."


def _full_neg(prop: Mapping[str, Any]) -> str:
    return f"{_cap_subject(str(prop['subject_text']))} {prop['be_form']} not {prop['complement']}."


def _primary_negative_contracted(prop: Mapping[str, Any]) -> str:
    subject = str(prop["subject_text"])
    subject_class = str(prop["subject_class"])
    complement = str(prop["complement"])
    be_form = str(prop["be_form"])
    if subject_class == "I":
        prefix = "I'm not"
    elif be_form == "is":
        prefix = f"{_cap_subject(subject)} isn't"
    elif be_form == "are":
        prefix = f"{_cap_subject(subject)} aren't"
    else:
        raise U05Q06BuildError(f"UNSUPPORTED_NEGATIVE_CONTRACTION:{subject_class}:{be_form}")
    return f"{prefix} {complement}."


def _affirmative_contracted(prop: Mapping[str, Any]) -> str:
    prefixes = {"I":"I'm","you":"You're","he":"He's","she":"She's","it":"It's","we":"We're","they":"They're"}
    subject_class = str(prop["subject_class"])
    if subject_class not in prefixes:
        raise U05Q06BuildError(f"UNSUPPORTED_AFFIRMATIVE_CONTRACTION:{subject_class}")
    return f"{prefixes[subject_class]} {prop['complement']}."


def _alternate_negative_contracted(prop: Mapping[str, Any]) -> str:
    prefixes = {"you":"You're not","he":"He's not","she":"She's not","it":"It's not","we":"We're not","they":"They're not"}
    subject_class = str(prop["subject_class"])
    if subject_class not in prefixes:
        raise U05Q06BuildError(f"UNSUPPORTED_ALT_NEGATIVE_CONTRACTION:{subject_class}")
    return f"{prefixes[subject_class]} {prop['complement']}."


def _row(prop: Mapping[str, Any], polarity: str, surface_variant: str, text: str) -> dict[str, Any]:
    return {
        **dict(prop),
        "polarity": polarity,
        "surface_variant": surface_variant,
        "text": text,
        "normalized_text": normalize_sentence(text),
    }


def build_candidates() -> list[dict[str, Any]]:
    propositions = _decode_seed(_safe_seed()["proposition_seed_b64"])
    if len(propositions) != 283:
        raise U05Q06BuildError("SEMANTIC_PROPOSITION_COUNT_DRIFT")

    rows: list[dict[str, Any]] = []
    first_by_frame_subject: dict[tuple[str, str], Mapping[str, Any]] = {}
    for prop in propositions:
        key = (str(prop["frame_base"]), str(prop["subject_class"]))
        first_by_frame_subject.setdefault(key, prop)
        rows.append(_row(prop, "AFFIRMATIVE", "FULL", _full_aff(prop)))
        rows.append(_row(prop, "NEGATIVE", "FULL", _full_neg(prop)))
        rows.append(_row(prop, "NEGATIVE", "CONTRACTED", _primary_negative_contracted(prop)))

    pronoun_order = ("I", "you", "he", "she", "it", "we", "they")
    frame_order = ("NP", "ADJ", "PLACE")
    for subject in pronoun_order:
        for frame in frame_order:
            prop = first_by_frame_subject.get((frame, subject))
            if prop is not None:
                rows.append(_row(prop, "AFFIRMATIVE", "CONTRACTED", _affirmative_contracted(prop)))
    for subject in ("you", "he", "she", "it", "we", "they"):
        for frame in frame_order:
            prop = first_by_frame_subject.get((frame, subject))
            if prop is not None:
                rows.append(_row(prop, "NEGATIVE", "CONTRACTED_ALT", _alternate_negative_contracted(prop)))

    if len(rows) != 884:
        raise U05Q06BuildError(f"SURFACE_CANDIDATE_COUNT_DRIFT:{len(rows)}")
    if len({row["normalized_text"] for row in rows}) != 884:
        raise U05Q06BuildError("CANDIDATE_NORMALIZED_IDENTITY_NOT_DISTINCT")
    return rows


FRAME_MAP = {
    ("NP","AFFIRMATIVE"):("U05-BF-NP-AFF","SUBJECT_BE_NOUN_PHRASE_COMPLEMENT"),
    ("ADJ","AFFIRMATIVE"):("U05-BF-ADJ-AFF","SUBJECT_BE_ADJECTIVE_COMPLEMENT"),
    ("PLACE","AFFIRMATIVE"):("U05-BF-PLACE-AFF","SUBJECT_BE_STATIC_PLACE_PP_COMPLEMENT"),
    ("NP","NEGATIVE"):("U05-BF-NP-NEG","SUBJECT_BE_NOT_NOUN_PHRASE_COMPLEMENT"),
    ("ADJ","NEGATIVE"):("U05-BF-ADJ-NEG","SUBJECT_BE_NOT_ADJECTIVE_COMPLEMENT"),
    ("PLACE","NEGATIVE"):("U05-BF-PLACE-NEG","SUBJECT_BE_NOT_STATIC_PLACE_PP_COMPLEMENT"),
}


def semantic_review(row: Mapping[str, Any]) -> tuple[str, str]:
    if row["frame_base"] == "NP" and row["complement"] in {"a person", "people"}:
        if row["polarity"] == "NEGATIVE":
            return "REJECT", "HUMAN_PERSON_NEGATION_NOT_A1_PEDAGOGICALLY_NATURAL"
        return "DEFER", "TRIVIAL_PERSON_IDENTITY_LOW_PEDAGOGICAL_UTILITY"
    if row["frame_base"] == "PLACE":
        return "CONTEXT_BOUND_APPROVE", "NATURAL_A1_STATIC_LOCATION_REQUIRES_CONTEXT_TRUTH_AT_USE_TIME"
    if row["subject_class"] in {"he", "she", "it", "they"}:
        return "CONTEXT_BOUND_APPROVE", "NATURAL_A1_PREDICATION_REQUIRES_REFERENT_BINDING_AT_USE_TIME"
    return "APPROVE", "NATURAL_A1_BE_PREDICATION_GPT56_REVIEWED"


def _current_authority_guard(contract: Mapping[str, Any]) -> None:
    q02 = json.loads(Q02_PATH.read_text(encoding="utf-8"))
    q03 = json.loads(Q03_PATH.read_text(encoding="utf-8"))
    q04 = json.loads(Q04_PATH.read_text(encoding="utf-8"))
    q05 = json.loads(Q05_PATH.read_text(encoding="utf-8"))
    if q02["summary"]["overall"]["admitted_identity_count"] != 106:
        raise U05Q06BuildError("Q02_ADMITTED_IDENTITY_DRIFT")
    allowed = {c for frame in q05["unit05_operational_frames"] for c in frame["q02_carrier_classes"]}
    direct = [
        row for row in q02["matrix"]
        if row["carrier_class"] in allowed
        and row["unit05_role"] == "TARGET_CARRIER"
        and str(row["unit05_admission_status"]).startswith("ADMITTED")
    ]
    if len(direct) != contract["generation_authority"]["direct_q02_carrier_count"]:
        raise U05Q06BuildError("Q02_DIRECT_CARRIER_DRIFT")
    if q03["acceptance"]["subject_agreement_rows"] != 9:
        raise U05Q06BuildError("Q03_SUBJECT_AGREEMENT_DRIFT")
    if q04["acceptance"]["new_surface_count"] != 66 or q04["acceptance"]["cumulative_distinct_chunk_surface_count"] != 156:
        raise U05Q06BuildError("Q04_CHUNK_AUTHORITY_DRIFT")
    if [row["frame_id"] for row in q05["unit05_operational_frames"]] != contract["generation_authority"]["q05_frame_ids"]:
        raise U05Q06BuildError("Q05_FRAME_AUTHORITY_DRIFT")
    if q05["q06_primary_generation_routing"]["predecessor_sentence_pool_for_dedup"] != 26610:
        raise U05Q06BuildError("Q05_PREDECESSOR_POOL_DRIFT")


def build_report() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    _current_authority_guard(contract)
    candidates = build_candidates()
    collisions = _decode_seed(_safe_seed()["collision_index_b64"])
    if len(collisions) != 100:
        raise U05Q06BuildError("PREDECESSOR_COLLISION_INDEX_COUNT_DRIFT")

    reuse: list[dict[str, Any]] = []
    new_assets: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in candidates:
        decision, reason = semantic_review(row)
        frame_id, family = FRAME_MAP[(row["frame_base"], row["polarity"])]
        common = {
            "text": row["text"],
            "normalized_text": row["normalized_text"],
            "frame_id": frame_id,
            "q03_frame_family": family,
            "polarity": row["polarity"],
            "surface_variant": row["surface_variant"],
            "subject_class": row["subject_class"],
            "subject_surface": row["subject_text"],
            "be_form": row["be_form"],
            "complement_surface": row["complement"],
            "carrier_ids": row["carrier_ids"],
            "semantic_class": row["semantic_class"],
            "relation_surface": row.get("relation"),
            "semantic_admission_class": decision,
            "semantic_admission_reason": reason,
            "requires_context_binding": decision == "CONTEXT_BOUND_APPROVE",
            "requires_antecedent_binding": row["subject_class"] in {"he", "she", "it", "they"},
        }
        collision = collisions.get(row["normalized_text"])
        if decision in {"REJECT", "DEFER"}:
            excluded.append({
                "candidate_id": "U05-CAND-" + hashlib.sha256(row["normalized_text"].encode()).hexdigest()[:20].upper(),
                **common,
                "decision": decision,
                "reason_code": reason,
                "predecessor_collision_units": [collision["unit"]] if collision else [],
            })
            continue
        if collision:
            ids = list(collision["ids"])
            reuse.append({
                "binding_id": "U05-REUSE-" + hashlib.sha256(row["normalized_text"].encode()).hexdigest()[:20].upper(),
                **common,
                "generation_role": "REUSE_VALIDATED_PREDECESSOR",
                "predecessor_unit": collision["unit"],
                "predecessor_sentence_id": sorted(ids)[0],
                "predecessor_sentence_ids": sorted(set(ids)),
                "dedup_match_type": collision["match"],
                "unit05_surface_quality_override": collision["match"] == "NORMALIZED_ONLY",
                "no_new_sentence_identity_created": True,
            })
        else:
            new_assets.append({
                "sentence_id": "U05-SENT-" + hashlib.sha256(row["normalized_text"].encode()).hexdigest()[:20].upper(),
                "unit_id": "GRAMMAR_BE_VERB_BASIC",
                "unit_number": 5,
                "level": "A1",
                **common,
                "canonical_admission_status": "ADMITTED",
                "generation_role": "UNIT05_NEW_ADMITTED",
                "mastery_role": "SUPPORT_VARIANT" if row["polarity"] == "AFFIRMATIVE" and row["surface_variant"] == "CONTRACTED" else "DIRECT_TARGET_OR_REQUIRED_NEGATIVE_VARIANT",
                "source_refs": [
                    "ulga/contracts/a1fs_v1_u05_q02_vocabulary_carrier_authority.json",
                    "ulga/contracts/a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json",
                    "ulga/contracts/a1fs_v1_u05_q04_be_chunk_authority.json",
                    "ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json",
                ],
                "reader360_generation_authority_used": False,
                "a2_unlocked": False,
            })

    usable = [*reuse, *new_assets]
    if (len(reuse), len(new_assets), len(excluded), len(usable)) != (94, 761, 29, 855):
        raise U05Q06BuildError("Q06_MATERIALIZATION_COUNT_DRIFT")

    integrity = contract["integrity"]
    candidate_identity = [{
        "text": row["text"],
        "normalized_text": row["normalized_text"],
        "frame_id": FRAME_MAP[(row["frame_base"], row["polarity"])][0],
        "surface_variant": row["surface_variant"],
    } for row in candidates]
    if digest(candidate_identity) != integrity["candidate_digest"]:
        raise U05Q06BuildError("Q06_CANDIDATE_DIGEST_DRIFT")
    if digest(reuse) != integrity["reuse_binding_digest"]:
        raise U05Q06BuildError("Q06_REUSE_DIGEST_DRIFT")
    if digest(new_assets) != integrity["new_sentence_asset_digest"]:
        raise U05Q06BuildError("Q06_NEW_ASSET_DIGEST_DRIFT")
    if digest(excluded) != integrity["excluded_candidate_digest"]:
        raise U05Q06BuildError("Q06_EXCLUSION_DIGEST_DRIFT")
    if digest(sorted(row["normalized_text"] for row in usable)) != integrity["usable_normalized_text_digest"]:
        raise U05Q06BuildError("Q06_USABLE_TEXT_DIGEST_DRIFT")

    return {
        **contract,
        "reuse_bindings": reuse,
        "new_sentence_assets": new_assets,
        "excluded_candidates": excluded,
    }


def main() -> int:
    report = build_report()
    a = report["acceptance"]
    print(f"STATUS={report['status']}")
    print(f"CANDIDATES={a['surface_candidate_count']}")
    print(f"USABLE={a['semantic_review_usable_count']}")
    print(f"REUSE={a['validated_predecessor_reuse_binding_count']}")
    print(f"NEW={a['unit05_new_admitted_sentence_asset_count']}")
    print(f"DEFERRED={a['deferred_count']}")
    print(f"REJECTED={a['rejected_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
