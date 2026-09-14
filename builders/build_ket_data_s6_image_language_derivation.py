from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

TASK_ID = "KET_Data_S6_CoreBridgeImplementation"
CONTRACT_SCHEMA = "ket.data.s6.image_language_derivation.contract.v1"
OUTPUT_SCHEMA = "ket.data.s6.image_language_derivation.v1"
EXPECTED_SCENE_COUNT = 15
EXPECTED_RECORD_COUNT = 16
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


class S6BuildError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _sha256_json(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _vocab_sort_key(vocab_id: str):
    m = re.fullmatch(r"v_(\d+)", vocab_id or "")
    return (0, int(m.group(1))) if m else (1, vocab_id or "")


def _fact_ref(iid: str, fact: dict) -> str:
    kind = fact.get("kind")
    value = fact.get("value")
    if kind == "relation":
        if not isinstance(value, dict) or set(value) != {"subject", "relation", "object"}:
            raise S6BuildError(f"FACT_RELATION_SHAPE:{iid}")
        return f"{iid}#relation:{value['subject']}|{value['relation']}|{value['object']}"
    singular = {"participant": "participant", "object": "object", "action": "action"}
    if kind not in singular or not isinstance(value, str) or not value:
        raise S6BuildError(f"FACT_SHAPE:{iid}")
    return f"{iid}#{singular[kind]}:{value}"


def _fact_present(scene: dict, fact: dict) -> bool:
    kind = fact.get("kind")
    value = fact.get("value")
    if kind == "participant":
        return value in (scene.get("participants") or [])
    if kind == "object":
        return value in (scene.get("objects") or [])
    if kind == "action":
        return value in (scene.get("actions") or [])
    if kind == "relation":
        return value in (scene.get("relations") or [])
    return False


def _render_pattern(pattern: dict, seed: dict) -> str:
    meta = pattern.get("metadata") or {}
    text = meta.get("canonical_pattern") or pattern.get("label") or ""
    relation_choice = seed.get("relation_choice")
    if relation_choice:
        if relation_choice not in {"in", "on", "under"} or "in/on/under" not in text:
            raise S6BuildError("RELATION_CHOICE")
        text = text.replace("in/on/under", relation_choice)
    for key, value in (seed.get("slot_values") or {}).items():
        text = text.replace("{" + key + "}", value)
    if "{" in text or "}" in text:
        raise S6BuildError("UNRESOLVED_PATTERN_SLOT")
    return text


def _index_vocab(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    out = defaultdict(list)
    for row in rows:
        word = str(row.get("word") or "").strip().lower()
        pos = str(row.get("part_of_speech") or "").strip().lower()
        if not word or not pos:
            continue
        if row.get("duplicate_status") != "canonical":
            continue
        if row.get("review_required") is True:
            continue
        if not row.get("vocab_id"):
            continue
        out[(word, pos)].append(row)
    for rows_for_key in out.values():
        rows_for_key.sort(key=lambda x: _vocab_sort_key(x.get("vocab_id")))
    return out


def _bind_lexical(seed: dict, scene: dict, contract: dict, vocab_index: dict, target_level: str) -> list[dict]:
    allowed_levels = set(contract["authority_binding_contract"]["allowed_vocabulary_levels"][target_level])
    transforms = contract.get("allowed_semantic_transforms") or {}
    result = []
    for item in seed.get("lexical_bindings") or []:
        source_kind = item.get("source_fact_kind")
        source_value = item.get("source_fact_value")
        source_fact = {"kind": source_kind, "value": source_value}
        if not _fact_present(scene, source_fact):
            raise S6BuildError(f"LEXICAL_SOURCE_FACT:{seed['seed_id']}:{source_kind}:{source_value}")
        surface = str(item.get("surface") or "").strip().lower()
        pos = str(item.get("part_of_speech") or "").strip().lower()
        transform = item.get("transform")
        if transform == "IDENTITY":
            if surface != str(source_value).lower():
                raise S6BuildError(f"LEXICAL_IDENTITY_TRANSFORM:{seed['seed_id']}")
        elif transform == "PLURAL_TO_SINGULAR_MEMBER":
            if (transforms.get(transform) or {}).get(source_value) != surface:
                raise S6BuildError(f"LEXICAL_PLURAL_TRANSFORM:{seed['seed_id']}:{source_value}:{surface}")
        else:
            raise S6BuildError(f"LEXICAL_TRANSFORM:{seed['seed_id']}:{transform}")
        eligible = [x for x in vocab_index.get((surface, pos), []) if x.get("level") in allowed_levels]
        candidates = [x for x in eligible if x.get("active") is True]
        if not candidates:
            candidates = eligible
        if not candidates:
            raise S6BuildError(f"VOCAB_UNRESOLVED:{seed['seed_id']}:{surface}:{pos}:{target_level}")
        refs = [x["vocab_id"] for x in candidates]
        result.append({
            "surface": surface,
            "part_of_speech": pos,
            "source_fact_ref": _fact_ref(seed["image_asset_id"], source_fact),
            "transform": transform,
            "vocabulary_refs": refs,
            "vocabulary_levels": sorted({x.get("level") for x in candidates}),
            "binding_precision": contract["authority_binding_contract"]["vocabulary_binding_precision"],
        })
    return result


def materialize(root=None, *, output_path=None) -> dict:
    root = _root(root)
    contract_path = root / "data" / "ket" / "ket_s6_image_language_derivation.json"
    contract = _json(contract_path)
    if (
        contract.get("schema"), contract.get("task_id"), contract.get("source_stage"),
        contract.get("output_stage"), contract.get("contract_source")
    ) != (CONTRACT_SCHEMA, TASK_ID, "KET_DATA_S5", "KET_DATA_S6", "KET_S6_1.txt"):
        raise S6BuildError("CONTRACT")
    engine = contract.get("semantic_engine_contract") or {}
    if engine.get("model") != "GPT-5.6 Sol" or engine.get("prompt_contract_version") != "KET_S6_V1":
        raise S6BuildError("SEMANTIC_ENGINE")
    if engine.get("live_model_call_in_ci") is not False or engine.get("frozen_candidate_required") is not True:
        raise S6BuildError("NONDETERMINISTIC_MODEL_POLICY")
    policy = contract.get("language_asset_policy") or {}
    if policy.get("learner_facing") is not False or policy.get("question_generation_allowed") is not False:
        raise S6BuildError("LEARNER_FACING_BOUNDARY")
    if policy.get("derivation_asset_not_learning_content") is not True:
        raise S6BuildError("DERIVATION_BOUNDARY")

    pred = contract.get("s5_predecessor") or {}
    s5_contract_path = root / pred["contract_path"]
    s5_bytes = s5_contract_path.read_bytes()
    if _git_blob_sha(s5_bytes) != pred.get("contract_git_blob_sha"):
        raise S6BuildError("S5_CONTRACT_BLOB_DRIFT")
    from builders.build_ket_data_s5_image_semantic_representation import materialize as materialize_s5
    s5 = materialize_s5(root)
    scene_rows = [x for x in s5.get("assets") or [] if x.get("semantic_status") == "SCENE_STRUCTURED"]
    if len(scene_rows) != pred.get("expected_scene_structured_count") or len(scene_rows) != EXPECTED_SCENE_COUNT:
        raise S6BuildError("S5_SCENE_COUNT")
    scenes = {x["image_asset_id"]: x for x in scene_rows}

    auth = contract["authority_binding_contract"]
    patterns = _json(root / auth["pattern_authority_path"])
    grammar_nodes = _json(root / auth["grammar_node_authority_path"])
    vocab_rows = _json(root / auth["vocabulary_authority_path"])
    pattern_map = {x.get("id"): x for x in patterns}
    grammar_map = {x.get("id"): x for x in grammar_nodes}
    vocab_index = _index_vocab(vocab_rows)
    level_profiles = {level: _json(root / path) for level, path in auth["level_profile_paths"].items()}

    records = []
    seen_seed_ids = set()
    for n, seed in enumerate(contract.get("candidate_seeds") or [], 1):
        seed_id = seed.get("seed_id")
        if not seed_id or seed_id in seen_seed_ids:
            raise S6BuildError("SEED_ID")
        seen_seed_ids.add(seed_id)
        iid = seed.get("image_asset_id")
        scene = scenes.get(iid)
        if not scene:
            raise S6BuildError(f"NON_SCENE_OR_UNKNOWN_IMAGE:{seed_id}:{iid}")
        target = seed.get("derivation_target_level")
        if target not in policy.get("target_levels", []):
            raise S6BuildError(f"TARGET_LEVEL:{seed_id}:{target}")
        profile = level_profiles[target]
        pattern_ref = seed.get("pattern_ref")
        pattern = pattern_map.get(pattern_ref)
        if not pattern:
            raise S6BuildError(f"PATTERN_UNKNOWN:{seed_id}:{pattern_ref}")
        pmeta = pattern.get("metadata") or {}
        if pmeta.get("review_status") != auth["pattern_admission"]["review_status"] or pmeta.get("generator_allowed") is not True:
            raise S6BuildError(f"PATTERN_NOT_ADMITTED:{seed_id}:{pattern_ref}")
        if pattern.get("cefr_level") != "A1" or pmeta.get("cefr_level") != "A1":
            raise S6BuildError(f"PATTERN_LEVEL:{seed_id}:{pattern_ref}")
        rendered = _render_pattern(pattern, seed)
        if rendered != seed.get("sentence"):
            raise S6BuildError(f"PATTERN_RENDER:{seed_id}:{rendered!r}")

        support_facts = seed.get("support_facts") or []
        if not support_facts:
            raise S6BuildError(f"NO_SUPPORT_FACTS:{seed_id}")
        for fact in support_facts:
            if not _fact_present(scene, fact):
                raise S6BuildError(f"FACT_UNSUPPORTED:{seed_id}:{fact}")
        fact_refs = [_fact_ref(iid, fact) for fact in support_facts]
        if any("[" in x or "]" in x for x in fact_refs):
            raise S6BuildError(f"INDEX_FACT_REF:{seed_id}")

        grammar_refs = list(pmeta.get("grammar_refs") or [])
        if not grammar_refs:
            raise S6BuildError(f"GRAMMAR_REFS_EMPTY:{seed_id}")
        egp_source_refs = []
        allowed_grammar_ids = set(profile.get("allowed_grammar_ids") or [])
        for grammar_ref in grammar_refs:
            node = grammar_map.get(grammar_ref)
            if not node:
                raise S6BuildError(f"GRAMMAR_NODE_UNKNOWN:{seed_id}:{grammar_ref}")
            source_record_id = (node.get("metadata") or {}).get("source_record_id")
            if not source_record_id:
                raise S6BuildError(f"GRAMMAR_SOURCE_ID_EMPTY:{seed_id}:{grammar_ref}")
            if source_record_id not in allowed_grammar_ids:
                raise S6BuildError(f"GRAMMAR_NOT_LEVEL_ALLOWED:{seed_id}:{grammar_ref}:{source_record_id}:{target}")
            egp_source_refs.append(source_record_id)

        lexical = _bind_lexical(seed, scene, contract, vocab_index, target)
        vocabulary_refs = sorted({ref for b in lexical for ref in b["vocabulary_refs"]}, key=_vocab_sort_key)
        if not vocabulary_refs:
            raise S6BuildError(f"VOCAB_EMPTY:{seed_id}")

        sentence = seed["sentence"]
        word_count = len(WORD_RE.findall(sentence))
        if word_count < int(profile["sentence_length_min"]) or word_count > int(profile["sentence_length_max"]):
            raise S6BuildError(f"SENTENCE_LENGTH:{seed_id}:{word_count}:{target}")
        if seed.get("candidate_source") != "GPT-5.6_SOL_FROZEN_CANDIDATE" or seed.get("semantic_review_status") != "APPROVED_FOR_DETERMINISTIC_ADMISSION_CHECK":
            raise S6BuildError(f"FROZEN_CANDIDATE:{seed_id}")

        semantic_input = {
            "image_asset_id": iid,
            "target_level": target,
            "support_facts": support_facts,
            "pattern_ref": pattern_ref,
            "slot_values": seed.get("slot_values") or {},
            "relation_choice": seed.get("relation_choice"),
        }
        records.append({
            "language_asset_id": f"KET_S6_LANG_{n:06d}",
            "seed_id": seed_id,
            "image_asset_id": iid,
            "source_exam_context": policy["source_exam_context"],
            "derivation_target_level": target,
            "fact_refs": fact_refs,
            "sentence": sentence,
            "sentence_word_count": word_count,
            "pattern_refs": [pattern_ref],
            "grammar_refs": grammar_refs,
            "egp_source_refs": egp_source_refs,
            "vocabulary_refs": vocabulary_refs,
            "vocabulary_bindings": lexical,
            "semantic_engine": engine["model"],
            "prompt_contract_version": engine["prompt_contract_version"],
            "input_semantic_digest": _sha256_json(semantic_input),
            "candidate_digest": _sha256_text(sentence),
            "candidate_source": seed["candidate_source"],
            "semantic_review_status": seed["semantic_review_status"],
            "derivation_status": "ADMITTED",
            "validation_status": "PASS",
            "learner_facing": False,
        })

    if len(records) != EXPECTED_RECORD_COUNT:
        raise S6BuildError("RECORD_COUNT")
    by_level = Counter(x["derivation_target_level"] for x in records)
    a1_scene_ids = {x["image_asset_id"] for x in records if x["derivation_target_level"] == "A1"}
    non_scene_count = sum(1 for x in records if x["image_asset_id"] not in scenes)
    summary = {
        "scene_source_count": len(scenes),
        "scene_images_with_a1_asset": len(a1_scene_ids),
        "language_asset_count": len(records),
        "target_level_counts": dict(sorted(by_level.items())),
        "non_scene_language_asset_count": non_scene_count,
        "new_image_identity_count": 0,
        "live_model_call_count": 0,
    }
    if summary != contract.get("expected_summary"):
        raise S6BuildError("SUMMARY_DRIFT")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": "KET_DATA_S5",
        "output_stage": "KET_DATA_S6",
        "contract_source": "KET_S6_1.txt",
        "s5_predecessor": {
            **pred,
            "materialized_scene_count": len(scenes),
        },
        "semantic_engine_contract": engine,
        "language_asset_policy": policy,
        "authority_binding_contract": auth,
        "summary": summary,
        "language_assets": records,
    }
    if output_path:
        Path(output_path).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ns = ap.parse_args()
    print(json.dumps(materialize(output_path=ns.output)["summary"], ensure_ascii=False, indent=2))