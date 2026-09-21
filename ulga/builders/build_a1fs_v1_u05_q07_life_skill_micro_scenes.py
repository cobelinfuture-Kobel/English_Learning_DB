#!/usr/bin/env python3
"""Materialize Unit05 Q07 life-skill micro-scenes from approved Unit05 Q06 semantics."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as q06_builder

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json"
TASK_ID = "A1FS-V1-U05Q07_Unit05LifeSkillMicroSceneMaterializationAndSentenceBinding"
DECISION_REF = "OPERATOR_APPROVAL:2026-09-21:U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION"
A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

MEDIUM_BY_FAMILY = {
    "SCHOOL_CLASSROOM_LEARNING": "SCHOOL_OR_CLASSROOM",
    "HOME_BEDROOM_LIVING": "HOME_OR_ROOM",
    "BATHROOM_SELF_CARE": "BATHROOM_OR_SELF_CARE",
    "KITCHEN_DINING": "KITCHEN_OR_DINING",
    "FOOD_CAFE_PICNIC": "CAFE_OR_PICNIC",
    "FAMILY_PEOPLE_SOCIAL": "FAMILY_OR_SOCIAL",
    "BODY_APPEARANCE": "PEOPLE_DESCRIPTION",
    "CLOTHING_PERSONAL_ITEMS": "CLOTHING_OR_PERSONAL_ITEMS",
    "PETS_FARM_ZOO": "PETS_FARM_OR_ZOO",
    "PARK_GARDEN_NATURE": "PARK_OR_GARDEN",
    "SPORTS_PLAY": "SPORTS_OR_PLAYGROUND",
    "MUSIC_DANCE": "MUSIC_OR_DANCE",
    "MEDIA_ENTERTAINMENT_TECH": "MEDIA_OR_ENTERTAINMENT",
    "TOWN_PUBLIC_PLACES": "TOWN_PUBLIC_PLACE",
    "SHOP_MONEY_SERVICES": "SHOP_OR_MARKET",
    "TRANSPORT_TRAVEL": "TRANSPORT_OR_TRAVEL",
    "COMMUNICATION_WRITING": "COMMUNICATION_OR_WRITING",
}

EVENT_BY_FRAME_POLARITY = {
    ("NP", "AFFIRMATIVE"): "IDENTITY_OR_ROLE_CONFIRMATION",
    ("NP", "NEGATIVE"): "IDENTITY_OR_ROLE_CORRECTION",
    ("ADJ", "AFFIRMATIVE"): "STATE_OR_DESCRIPTION_CONFIRMATION",
    ("ADJ", "NEGATIVE"): "STATE_OR_DESCRIPTION_CONTRAST",
    ("PLACE", "AFFIRMATIVE"): "STATIC_LOCATION_CONFIRMATION",
    ("PLACE", "NEGATIVE"): "STATIC_LOCATION_CONTRAST",
}

NEGATIVE_PLACE_EVIDENCE = {
    "in": "Show the subject clearly outside the named container/place, with both subject and landmark visible.",
    "inside": "Show the subject clearly outside the visible boundary of the named container/place.",
    "on": "Show the subject clearly off the named supporting surface and visibly elsewhere.",
    "near": "Show the subject clearly far from the named landmark; ambiguous middle distance is not sufficient.",
    "at": "Show the subject clearly at a different named location.",
    "under": "Show the subject clearly not below the landmark, for example beside or above it.",
    "behind": "Show the subject clearly in front of or beside the landmark, not hidden behind it.",
    "between": "Show the subject clearly outside the interval defined by the two distinct landmarks.",
}


class U05Q07BuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().casefold()


def _frame_base(frame_id: str) -> str:
    if "-NP-" in frame_id:
        return "NP"
    if "-ADJ-" in frame_id:
        return "ADJ"
    if "-PLACE-" in frame_id:
        return "PLACE"
    raise U05Q07BuildError(f"UNKNOWN_FRAME:{frame_id}")


def _family_for(row: Mapping[str, Any]) -> str:
    text = normalize(f"{row.get('subject_surface','')} {row.get('complement_surface','')}")
    frame = _frame_base(str(row["frame_id"]))

    rules = (
        (("school","classroom","student","teacher","desk","library"), "SCHOOL_CLASSROOM_LEARNING"),
        (("bathroom",), "BATHROOM_SELF_CARE"),
        (("kitchen","plate","cup","dining"), "KITCHEN_DINING"),
        (("café","cafe","picnic"), "FOOD_CAFE_PICNIC"),
        (("player","playground","sports centre"), "SPORTS_PLAY"),
        (("coat","jacket","hat","shoe","clothes"), "CLOTHING_PERSONAL_ITEMS"),
        (("cat","dog","farm","zoo"), "PETS_FARM_ZOO"),
        (("park","garden"), "PARK_GARDEN_NATURE"),
        (("cinema","museum","camera","picture"), "MEDIA_ENTERTAINMENT_TECH"),
        (("shop","market"), "SHOP_MONEY_SERVICES"),
        (("bus stop","station","road","street","train","bus","car"), "TRANSPORT_TRAVEL"),
        (("pen","pencil","book"), "COMMUNICATION_WRITING"),
        (("bedroom","living room","home","house","room","bed","door","window","chair"), "HOME_BEDROOM_LIVING"),
        (("brother","sister","mother","father","parent","family","friend","baby","boy","girl","man","woman","child","person"), "FAMILY_PEOPLE_SOCIAL"),
    )
    for keywords, family in rules:
        if any(keyword in text for keyword in keywords):
            return family

    if frame == "ADJ":
        adjective = normalize(row.get("complement_surface", ""))
        if adjective in {"young","old","beautiful","big","small","black","blue","brown","green","grey","orange","red","white","yellow"}:
            return "BODY_APPEARANCE" if row.get("subject_class") in {"he","she","they"} else "HOME_BEDROOM_LIVING"
        if adjective in {"happy","sad","tired","hungry","well","nice","bad"}:
            return "FAMILY_PEOPLE_SOCIAL"
    if row.get("subject_class") in {"he","she","they"}:
        return "FAMILY_PEOPLE_SOCIAL"
    if row.get("subject_class") == "it":
        return "HOME_BEDROOM_LIVING"
    return "TOWN_PUBLIC_PLACES"


def _referent_binding(row: Mapping[str, Any]) -> dict[str, Any]:
    subject_class = str(row["subject_class"])
    anchors = {
        "he": ("NAMED_MALE_PERSON", "Ben"),
        "she": ("NAMED_FEMALE_PERSON", "Mia"),
        "it": ("VISIBLE_NONHUMAN_OR_OBJECT", "the target item"),
        "they": ("TWO_OR_MORE_VISIBLE_REFERENTS", "the target group"),
    }
    if subject_class not in anchors:
        return {
            "required": False,
            "subject_class": subject_class,
            "anchor_type": "SUBJECT_SURFACE_IS_SELF_ANCHORED",
            "anchor_label": row["subject_surface"],
        }
    anchor_type, anchor_label = anchors[subject_class]
    return {
        "required": True,
        "subject_class": subject_class,
        "anchor_type": anchor_type,
        "anchor_label": anchor_label,
        "antecedent_must_appear_before_or_with_pronoun_use": True,
    }


def _truth_spec(row: Mapping[str, Any]) -> dict[str, Any]:
    frame = _frame_base(str(row["frame_id"]))
    polarity = str(row["polarity"])
    subject = str(row["subject_surface"])
    complement = str(row["complement_surface"])
    relation = row.get("relation_surface")

    if frame == "NP":
        if polarity == "AFFIRMATIVE":
            mode = "EXPLICIT_IDENTITY_CATEGORY_OR_ROLE_CUE"
            directive = f"Provide an explicit visible or contextual cue that entails: {subject} is {complement}."
            alternative = False
        else:
            mode = "POSITIVE_ALTERNATIVE_IDENTITY_CATEGORY_OR_ROLE_CUE"
            directive = (
                f"Provide an explicit positive alternative identity/category/role cue for {subject} that makes "
                f"the proposition '{subject} is {complement}' false. Mere absence is not evidence."
            )
            alternative = True
    elif frame == "ADJ":
        if polarity == "AFFIRMATIVE":
            mode = "OBSERVABLE_OR_EXPLICIT_PROPERTY_STATE_CUE"
            directive = f"Show or state an observable cue that entails the property/state '{complement}' for {subject}."
            alternative = False
        else:
            mode = "EXPLICIT_INCOMPATIBLE_PROPERTY_STATE_CUE"
            directive = (
                f"Show or state a clear incompatible contrast for {subject} so '{complement}' is false. "
                "Mere absence of the target property/state is not sufficient."
            )
            alternative = True
    else:
        if polarity == "AFFIRMATIVE":
            mode = "STATIC_RELATION_TRUE"
            directive = f"Make the static location '{complement}' visibly or contextually true for {subject}."
            alternative = False
        else:
            mode = "STATIC_RELATION_FALSE_WITH_POSITIVE_CONTRAST"
            directive = NEGATIVE_PLACE_EVIDENCE.get(
                str(relation),
                f"Show {subject} in a clearly incompatible location so '{complement}' is false.",
            )
            alternative = True

    return {
        "frame_base": frame,
        "polarity": polarity,
        "evidence_mode": mode,
        "render_or_context_directive": directive,
        "explicit_positive_alternative_required_for_negative": alternative,
        "negation_proof_by_absence_allowed": False if polarity == "NEGATIVE" else None,
        "target_sentence_may_be_used_as_scene_prompt": False,
        "relation_surface": relation,
    }


def _scene_group_key(row: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["frame_id"]),
        str(row["polarity"]),
        normalize(row["subject_surface"]),
        normalize(row["complement_surface"]),
        normalize(row.get("relation_surface") or ""),
    )


def _q06_identity(row: Mapping[str, Any]) -> str:
    return str(row.get("sentence_id") or row.get("binding_id") or "")


def _scene_id(key: tuple[str, ...]) -> str:
    return "U05-SCENE-" + hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:20].upper()


def _binding_id(q06_identity: str, scene_ref_id: str) -> str:
    return "U05-SCENE-BIND-" + hashlib.sha256(f"{q06_identity}|{scene_ref_id}".encode("utf-8")).hexdigest()[:20].upper()


def _build_payload() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    q06 = q06_builder.build_report()
    rows = [*q06["reuse_bindings"], *q06["new_sentence_assets"]]
    if len(rows) != 855:
        raise U05Q07BuildError(f"Q06_USABLE_COUNT_DRIFT:{len(rows)}")

    context_rows = [row for row in rows if row["requires_context_binding"] is True]
    standalone_rows = [row for row in rows if row["requires_context_binding"] is False]
    if (len(context_rows), len(standalone_rows)) != (478, 377):
        raise U05Q07BuildError("Q06_CONTEXT_SPLIT_DRIFT")

    governed = set(contract["prior_scene_authority"]["governed_scene_families"])
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in context_rows:
        grouped[_scene_group_key(row)].append(row)

    scenes: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda row: (str(row["surface_variant"]), str(row["normalized_text"])))
        source = group[0]
        family = _family_for(source)
        if family not in governed:
            raise U05Q07BuildError(f"UNGOVERNED_SCENE_FAMILY:{family}")
        frame_base = _frame_base(str(source["frame_id"]))
        event = EVENT_BY_FRAME_POLARITY[(frame_base, str(source["polarity"]))]
        scene_ref_id = _scene_id(key)
        q06_ids = [_q06_identity(row) for row in group]
        if any(not value for value in q06_ids):
            raise U05Q07BuildError("Q06_IDENTITY_MISSING")
        scene = {
            "scene_ref_id": scene_ref_id,
            "unit_id": "GRAMMAR_BE_VERB_BASIC",
            "unit_number": 5,
            "source_class": "Q06_CONTEXT_REQUIRED_SEMANTIC_TRUTH",
            "canonical_scene_scope": "UNIT05_LOCAL_AUTHORITATIVE_INSTANCE",
            "scene_family": family,
            "medium_setting": MEDIUM_BY_FAMILY[family],
            "small_micro_scene_event": event,
            "semantic_frame_id": source["frame_id"],
            "polarity": source["polarity"],
            "subject_surface": source["subject_surface"],
            "subject_class": source["subject_class"],
            "complement_surface": source["complement_surface"],
            "relation_surface": source.get("relation_surface"),
            "semantic_scene_key_sha256": hashlib.sha256("|".join(key).encode("utf-8")).hexdigest(),
            "bound_q06_identity_count": len(q06_ids),
            "bound_q06_identities": q06_ids,
            "bound_sentence_texts": [row["text"] for row in group],
            "surface_variants": sorted({row["surface_variant"] for row in group}),
            "referent_binding_spec": _referent_binding(source),
            "truth_evidence_spec": _truth_spec(source),
            "answerability_guard": {
                "scene_binds_truth_of_all_bound_sentences": True,
                "unbound_context_required_use_allowed": False,
                "learner_visible_target_sentence_used_as_scene_prompt": False,
                "negative_truth_requires_positive_contrast_evidence": source["polarity"] == "NEGATIVE",
                "downstream_single_answer_use_requires_unique_licensed_cue": True,
            },
            "source_refs": [
                "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json",
                "ulga/builders/build_a1fs_v1_u05_q06_sentence_assets.py",
            ],
            "source_claim": "UNIT05_Q06_CONTEXT_REQUIRED_SENTENCE_BOUND_TO_UNIT05_LOCAL_SCENE_TRUTH",
            "a2_a2plus_unlocked": False,
        }
        scenes.append(scene)

        for row in group:
            qid = _q06_identity(row)
            bindings.append({
                "binding_id": _binding_id(qid, scene_ref_id),
                "q06_identity": qid,
                "q06_source_role": row["generation_role"],
                "q06_predecessor_sentence_id": row.get("predecessor_sentence_id"),
                "sentence_text": row["text"],
                "normalized_text": row["normalized_text"],
                "frame_id": row["frame_id"],
                "polarity": row["polarity"],
                "surface_variant": row["surface_variant"],
                "subject_class": row["subject_class"],
                "semantic_admission_class": row["semantic_admission_class"],
                "scene_ref_id": scene_ref_id,
                "context_binding_satisfied": True,
                "learner_use_requires_bound_scene": True,
                "usage_role": "CONTEXT_REQUIRED_Q06_SENTENCE",
            })

    if len(bindings) != 478:
        raise U05Q07BuildError("Q07_BINDING_COUNT_DRIFT")
    if len({row["binding_id"] for row in bindings}) != 478:
        raise U05Q07BuildError("Q07_BINDING_ID_NOT_DISTINCT")
    if len({row["scene_ref_id"] for row in scenes}) != len(scenes):
        raise U05Q07BuildError("Q07_SCENE_ID_NOT_DISTINCT")

    scene_by_id = {row["scene_ref_id"]: row for row in scenes}
    if set(row["scene_ref_id"] for row in bindings) != set(scene_by_id):
        raise U05Q07BuildError("Q07_SCENE_BINDING_SET_MISMATCH")

    scene_family_counts = Counter(row["scene_family"] for row in scenes)
    binding_frame_counts = Counter(row["frame_id"] for row in bindings)
    binding_polarity_counts = Counter(row["polarity"] for row in bindings)
    referent_required_scene_count = sum(1 for row in scenes if row["referent_binding_spec"]["required"])

    coverage = {
        "q06_usable_sentence_supply_count": 855,
        "q06_context_required_sentence_surface_count": 478,
        "q06_standalone_sentence_surface_count": 377,
        "unit05_scene_instance_count": len(scenes),
        "sentence_scene_binding_count": len(bindings),
        "surface_variant_scene_reuse_count": len(bindings) - len(scenes),
        "q06_unbound_context_required_sentence_count": 0,
        "used_scene_family_count": len(scene_family_counts),
        "used_scene_family_counts": dict(sorted(scene_family_counts.items())),
        "binding_frame_counts": dict(sorted(binding_frame_counts.items())),
        "binding_polarity_counts": dict(sorted(binding_polarity_counts.items())),
        "referent_required_scene_count": referent_required_scene_count,
        "new_global_scene_family_count": 0,
        "new_global_canonical_scene_identity_count": 0,
    }

    return {
        **contract,
        "coverage": coverage,
        "micro_scenes": scenes,
        "sentence_scene_bindings": bindings,
        "standalone_sentence_policy": {
            "standalone_sentence_surface_count": 377,
            "forced_scene_binding_count": 0,
            "policy": "Q06 APPROVE sentences remain valid standalone supply; Q07 does not invent unnecessary scenes for them.",
        },
        "integrity": {
            "scene_digest": digest(scenes),
            "binding_digest": digest(bindings),
            "bound_normalized_text_digest": digest(sorted(row["normalized_text"] for row in bindings)),
        },
        "acceptance": {
            "q06_context_required_sentence_bindings": "478/478",
            "q06_unbound_context_required_sentence_count": 0,
            "unit05_scene_instance_count": len(scenes),
            "sentence_scene_binding_count": 478,
            "surface_variant_scene_reuse_count": len(bindings) - len(scenes),
            "new_global_scene_family_count": 0,
            "new_global_canonical_scene_identity_count": 0,
            "status": "PASS_A1FS_V1_U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING",
        },
    }


def build_candidate() -> dict[str, Any]:
    payload = _build_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "q06_approved_sentence_asset_task_id": q06_builder.TASK_ID,
            "q06_source_main_sha": payload["source_main_sha"],
            "q07_contract_path": str(CONTRACT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
            "q06_context_required_sentence_surface_count": 478,
            "q07_scene_instance_count": payload["coverage"]["unit05_scene_instance_count"],
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u05_q07_life_skill_micro_scenes as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def build_report() -> dict[str, Any]:
    return admit_candidate(build_candidate())["payload"]


def main() -> int:
    from ulga.validators import validate_a1fs_v1_u05_q07_life_skill_micro_scenes as validator

    candidate = build_candidate()
    approved = admit_candidate(candidate)
    result = validator.validate_approved(candidate, approved)
    report = approved["payload"]
    print(f"STATUS={report['status']}")
    print(f"SCENES={report['coverage']['unit05_scene_instance_count']}")
    print(f"BINDINGS={report['coverage']['sentence_scene_binding_count']}")
    print(f"STANDALONE={report['coverage']['q06_standalone_sentence_surface_count']}")
    print(f"UNBOUND_CONTEXT_REQUIRED={report['coverage']['q06_unbound_context_required_sentence_count']}")
    print(f"ERROR_COUNT={result['error_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
