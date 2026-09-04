#!/usr/bin/env python3
"""Validate append-only Unit03 Layer2 pronoun coverage against formal C-I structure."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement_contract.json"
VALIDATOR_ID = "A1FS-V1-U03SPK-L2-PCOV-CI-FULLFIX-VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U03_SPEAKING_LAYER2_PRONOUN_COVERAGE_CI_FULLFIX"
TARGETS = ("you", "we", "it")
ALL_PRONOUNS = ("i", "you", "he", "she", "it", "we", "they")


class SupplementValidationError(ValueError):
    pass


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SupplementValidationError(message)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(x) for x in value if isinstance(x, Mapping)]
    if isinstance(value, Mapping):
        for key in ("records", "sets", "items", "data", "atomic_sentences", "sentences"):
            candidate = value.get(key)
            if isinstance(candidate, list):
                return [dict(x) for x in candidate if isinstance(x, Mapping)]
    raise SupplementValidationError("records_list_not_found")


def _utterances(row: Mapping[str, Any]) -> list[str]:
    value = row.get("utterances")
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    turns = row.get("turns")
    if isinstance(turns, list):
        return [
            str(x.get("text", "")).strip()
            for x in turns
            if isinstance(x, Mapping) and str(x.get("text", "")).strip()
        ]
    return []


def _initial_pronoun(text: str) -> str | None:
    match = re.match(r"^\s*(I|You|He|She|It|We|They)\b", text)
    return match.group(1).lower() if match else None


def _body(text: str, pronoun: str) -> str:
    return re.sub(rf"^{pronoun}\s+", "", text.strip(), count=1, flags=re.I).lower()


def pronoun_counts(rows: Sequence[Mapping[str, Any]]) -> Counter[str]:
    out: Counter[str] = Counter()
    for row in rows:
        for text in _utterances(row):
            p = _initial_pronoun(text)
            if p:
                out[p] += 1
    return out


def _check_donor_binding(row: Mapping[str, Any], donor_by_id: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    donor_id = str(row.get("source_layer2_connected_id") or "")
    _require(donor_id in donor_by_id, f"source_layer2_connected_id_invalid:{row.get('connected_id')}")
    donor = donor_by_id[donor_id]
    _require(row.get("family") == donor.get("family"), f"donor_family_mismatch:{row.get('connected_id')}")
    for field in ("scene_family", "scene_location", "q10_source_item_id"):
        _require(row.get(field) == donor.get(field), f"donor_{field}_mismatch:{row.get('connected_id')}")
    return donor


def _check_direct_atomic(
    atom: Mapping[str, Any],
    *,
    pronoun: str,
    expected_text: str,
    atom_id: str,
) -> None:
    _require(str(atom.get("text", "")).strip() == expected_text, f"direct_atomic_text_mismatch:{atom_id}")
    _require(str(atom.get("subject_pronoun", "")).lower() == pronoun, f"direct_atomic_pronoun_mismatch:{atom_id}")
    _require(atom.get("semantic_admission_class") == "APPROVE", f"direct_atomic_not_approved:{atom_id}")
    _require(atom.get("reference_mode") == "DIRECT", f"direct_atomic_not_direct:{atom_id}")


def validate_payload(
    payload: Mapping[str, Any],
    *,
    base_rows: Sequence[Mapping[str, Any]],
    atomic_rows: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    supplement = _rows(payload.get("supplement_records", []))
    _require(supplement, "supplement_records_required")

    structure = contract["layer2_structure"]
    allowed = structure["allowed_family_by_target"]
    expected_card_counts = {str(k): int(v) for k, v in structure["card_counts"].items()}
    expected_rows = {str(k): int(v) for k, v in structure["utterances_per_card"].items()}

    base_ids = {
        str(row.get("connected_id") or row.get("set_id") or "")
        for row in base_rows
        if row.get("connected_id") or row.get("set_id")
    }
    donor_by_id = {
        str(row.get("connected_id")): row
        for row in base_rows
        if row.get("connected_id")
    }
    supplement_ids = [str(row.get("connected_id") or "") for row in supplement]
    _require(all(supplement_ids), "supplement_connected_id_required")
    _require(len(supplement_ids) == len(set(supplement_ids)), "supplement_connected_id_duplicate")
    _require(not (set(supplement_ids) & base_ids), "supplement_connected_id_collides_with_base")
    prefix = contract["append_only"]["supplement_id_prefix"]
    _require(all(x.startswith(prefix) for x in supplement_ids), "supplement_connected_id_prefix_invalid")

    atom_by_id = {
        str(row.get("atomic_id")): row
        for row in atomic_rows
        if row.get("atomic_id")
    }
    family_counts: Counter[str] = Counter()
    target_card_counts: Counter[str] = Counter()
    atom_ids_used: list[str] = []

    for row in supplement:
        row_id = str(row.get("connected_id"))
        target = str(row.get("target_subject_pronoun") or "").lower()
        _require(target in TARGETS, f"invalid_target_subject_pronoun:{row_id}")
        family = str(row.get("family") or "")
        _require(family == allowed[target], f"target_family_mismatch:{row_id}:{target}:{family}")
        _require(family in expected_rows, f"unrecognized_layer2_family:{row_id}:{family}")
        family_counts[family] += 1
        target_card_counts[target] += 1

        donor = _check_donor_binding(row, donor_by_id)
        utterances = _utterances(row)
        _require(len(utterances) == expected_rows[family], f"formal_layer2_row_count_mismatch:{row_id}")
        _require(all("___" not in x and "[...]" not in x for x in utterances), f"learner_blank_forbidden:{row_id}")

        ids = [str(x) for x in row.get("atomic_source_ids", [])]
        _require(ids, f"atomic_source_ids_required:{row_id}")
        _require(all(x in atom_by_id for x in ids), f"atomic_source_id_missing:{row_id}")
        atom_ids_used.extend(ids)

        if target == "we":
            _require(family == "C_SENTENCE_CHAINING", f"we_must_be_part_c:{row_id}")
            _require(all(_initial_pronoun(x) == "we" for x in utterances), f"part_c_we_target_only_required:{row_id}")
            _require(len(ids) == 6, f"part_c_we_six_atomic_ids_required:{row_id}")
            for text, atom_id in zip(utterances, ids):
                _check_direct_atomic(atom_by_id[atom_id], pronoun="we", expected_text=text, atom_id=atom_id)

        elif target == "you":
            _require(family == "H_INTERACTION_ROLEPLAY", f"you_must_be_part_h:{row_id}")
            turns = row.get("turns")
            _require(isinstance(turns, list) and len(turns) == 8, f"part_h_eight_turns_required:{row_id}")
            speakers = [str(x.get("speaker", "")) for x in turns if isinstance(x, Mapping)]
            texts = [str(x.get("text", "")).strip() for x in turns if isinstance(x, Mapping)]
            _require(speakers == ["A", "B"] * 4, f"part_h_ab_alternation_required:{row_id}")
            _require(texts == utterances, f"part_h_turn_utterance_binding_required:{row_id}")
            _require([_initial_pronoun(x) for x in utterances] == ["you", "i"] * 4, f"part_h_you_i_reference_pattern_required:{row_id}")
            _require(len(ids) == 8, f"part_h_eight_atomic_ids_required:{row_id}")
            for pair_index in range(4):
                you_text = utterances[pair_index * 2]
                i_text = utterances[pair_index * 2 + 1]
                _require(_body(you_text, "you") == _body(i_text, "i"), f"part_h_you_i_body_mismatch:{row_id}:{pair_index}")
                you_id = ids[pair_index * 2]
                i_id = ids[pair_index * 2 + 1]
                _check_direct_atomic(atom_by_id[you_id], pronoun="you", expected_text=you_text, atom_id=you_id)
                _check_direct_atomic(atom_by_id[i_id], pronoun="i", expected_text=i_text, atom_id=i_id)

        else:
            _require(family == "E_SHOW_AND_TELL", f"it_must_be_part_e:{row_id}")
            meta = row.get("antecedent")
            _require(isinstance(meta, Mapping), f"it_antecedent_metadata_required:{row_id}")
            _require(meta.get("referent_type") == "SINGULAR_NONHUMAN", f"it_antecedent_nonhuman_required:{row_id}")
            _require(int(meta.get("utterance_index", -1)) == 0, f"it_antecedent_must_be_first:{row_id}")
            _require(str(meta.get("text", "")).strip() == utterances[0], f"it_antecedent_text_binding_required:{row_id}")
            _require(_initial_pronoun(utterances[0]) != "it", f"it_antecedent_must_precede_it:{row_id}")
            _require(all(_initial_pronoun(x) == "it" for x in utterances[1:4]), f"part_e_three_it_target_lines_required:{row_id}")
            _require(all(_initial_pronoun(x) != "it" for x in utterances[4:]), f"part_e_support_must_not_add_it_count:{row_id}")

            source_atomic_id = str(meta.get("source_atomic_id") or "")
            _require(source_atomic_id in atom_by_id, f"it_antecedent_source_atomic_required:{row_id}")
            source_identity = str(atom_by_id[source_atomic_id].get("text", "")).strip()
            identity_match = re.match(r"^It is (a|an) (.+)\.$", source_identity, flags=re.I)
            _require(identity_match is not None, f"it_identity_atomic_required:{row_id}")
            expected_antecedent = f"This is {identity_match.group(1)} {identity_match.group(2)}."
            _require(utterances[0] == expected_antecedent, f"it_antecedent_derivation_mismatch:{row_id}")
            _require(utterances[1] == source_identity, f"part_e_identity_must_be_first_it_line:{row_id}")

            _require(len(ids) == 3, f"part_e_three_target_atomic_ids_required:{row_id}")
            _require(ids[0] == source_atomic_id, f"part_e_identity_atomic_order_required:{row_id}")
            for text, atom_id in zip(utterances[1:4], ids):
                atom = atom_by_id[atom_id]
                _require(str(atom.get("text", "")).strip() == text, f"it_atomic_text_mismatch:{atom_id}")
                _require(str(atom.get("subject_pronoun", "")).lower() == "it", f"it_atomic_pronoun_mismatch:{atom_id}")
                _require(atom.get("semantic_admission_class") in {"APPROVE", "CONTEXT_BOUND_APPROVE"}, f"it_atomic_not_approved:{atom_id}")
                _require(atom.get("reference_mode") == "REFERENCE_BOUND", f"it_atomic_not_reference_bound:{atom_id}")

            support = [str(x).strip() for x in row.get("source_layer2_support_utterances", [])]
            _require(support == utterances[4:6], f"part_e_support_binding_required:{row_id}")
            donor_utterances = _utterances(donor)
            _require(all(x in donor_utterances for x in support), f"part_e_support_not_from_donor:{row_id}")
            _require("Object" in str(donor.get("title", "")), f"part_e_object_donor_required:{row_id}")

    _require(len(supplement) == int(structure["supplement_connected_sets"]), "supplement_connected_set_count_mismatch")
    _require(sum(len(_utterances(row)) for row in supplement) == int(structure["supplement_utterances"]), "supplement_utterance_count_mismatch")
    for target, count in expected_card_counts.items():
        _require(target_card_counts[target] == count, f"target_card_count_mismatch:{target}:{target_card_counts[target]}!={count}")

    expected_family_counts = {
        allowed[target]: count for target, count in expected_card_counts.items()
    }
    _require(dict(family_counts) == expected_family_counts, f"supplement_family_counts_mismatch:{dict(family_counts)}")

    add = pronoun_counts(supplement)
    base = pronoun_counts(base_rows)
    combined = base + add
    for p, exact in contract["additional_exact_counts"].items():
        _require(add[p] == int(exact), f"additional_pronoun_exact_count_mismatch:{p}:{add[p]}!={exact}")
    for p, minimum in contract["combined_minimums"].items():
        _require(combined[p] >= int(minimum), f"combined_pronoun_minimum_not_met:{p}:{combined[p]}<{minimum}")
    _require(all(combined[p] > 0 for p in ALL_PRONOUNS), "combined_seven_pronoun_coverage_required")

    you_surfaces = [
        text for row in supplement if row.get("target_subject_pronoun") == "you"
        for text in _utterances(row) if _initial_pronoun(text) == "you"
    ]
    we_surfaces = [
        text for row in supplement if row.get("target_subject_pronoun") == "we"
        for text in _utterances(row) if _initial_pronoun(text) == "we"
    ]
    _require(len(you_surfaces) == len(set(you_surfaces)), "you_target_exact_repeat_forbidden")
    _require(len(we_surfaces) == len(set(we_surfaces)), "we_target_exact_repeat_forbidden")

    receipt_core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "supplement_set_count": len(supplement),
        "supplement_utterance_count": sum(len(_utterances(row)) for row in supplement),
        "supplement_family_counts": dict(family_counts),
        "supplement_target_card_counts": dict(target_card_counts),
        "additional_sentence_initial_pronoun_counts": {p: add[p] for p in TARGETS},
        "combined_sentence_initial_pronoun_counts": {p: combined[p] for p in ALL_PRONOUNS},
        "base_set_count": len(base_rows),
        "base_utterance_count": sum(len(_utterances(row)) for row in base_rows),
        "atomic_source_id_count": len(set(atom_ids_used)),
        "append_only_base_ids_unchanged": True,
        "formal_c_i_family_contract_pass": True,
        "formal_interaction_turn_contract_pass": True,
        "it_antecedent_policy_pass": True,
        "expected_supplement_logical_pages": int(structure["print_contract"]["logical_pages"]),
        "a2_unlocked": False,
    }
    receipt_sha = hashlib.sha256(
        json.dumps(receipt_core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**receipt_core, "receipt_sha256": receipt_sha, "validation_status": PASS_STATUS}


def validate_files(
    *,
    payload_path: Path,
    base_layer2_path: Path,
    atomic_pool_path: Path,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = _load(contract_path)
    _require(_sha(base_layer2_path) == contract["base_sources"]["layer2_data_sha256"], "base_layer2_sha256_mismatch")
    _require(_sha(atomic_pool_path) == contract["base_sources"]["atomic_pool_sha256"], "atomic_pool_sha256_mismatch")
    base_rows = _rows(_load(base_layer2_path))
    atomic_rows = _rows(_load(atomic_pool_path))
    _require(len(base_rows) == int(contract["base_sources"]["base_connected_sets"]), "base_connected_set_count_mismatch")
    _require(sum(len(_utterances(x)) for x in base_rows) == int(contract["base_sources"]["base_utterances"]), "base_utterance_count_mismatch")
    payload = _load(payload_path)
    _require(isinstance(payload, Mapping), "payload_object_required")
    return validate_payload(payload, base_rows=base_rows, atomic_rows=atomic_rows, contract=contract)
