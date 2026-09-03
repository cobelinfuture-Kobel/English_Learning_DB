#!/usr/bin/env python3
"""Validate the append-only Unit03 Layer2 subject-pronoun coverage supplement."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement_contract.json"
VALIDATOR_ID = "A1FS-V1-U03SPK-L2-PCOV-SUPPLEMENT-VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_U03_SPEAKING_LAYER2_PRONOUN_COVERAGE_SUPPLEMENT"
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
        return [str(x.get("text", "")).strip() for x in turns if isinstance(x, Mapping) and str(x.get("text", "")).strip()]
    return []

def _initial_pronoun(text: str) -> str | None:
    match = re.match(r"^\s*(I|You|He|She|It|We|They)\b", text)
    return match.group(1).lower() if match else None

def pronoun_counts(rows: Sequence[Mapping[str, Any]]) -> Counter[str]:
    out: Counter[str] = Counter()
    for row in rows:
        for text in _utterances(row):
            p = _initial_pronoun(text)
            if p:
                out[p] += 1
    return out

def validate_payload(payload: Mapping[str, Any], *, base_rows: Sequence[Mapping[str, Any]], atomic_rows: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> dict[str, Any]:
    supplement = _rows(payload.get("supplement_records", []))
    _require(supplement, "supplement_records_required")
    base_ids = {str(row.get("connected_id") or row.get("set_id") or "") for row in base_rows}
    supplement_ids = [str(row.get("connected_id") or "") for row in supplement]
    _require(all(supplement_ids), "supplement_connected_id_required")
    _require(len(supplement_ids) == len(set(supplement_ids)), "supplement_connected_id_duplicate")
    _require(not (set(supplement_ids) & base_ids), "supplement_connected_id_collides_with_base")
    prefix = contract["append_only"]["supplement_id_prefix"]
    _require(all(x.startswith(prefix) for x in supplement_ids), "supplement_connected_id_prefix_invalid")

    atomic_by_id = {str(row.get("atomic_id") or ""): row for row in atomic_rows if row.get("atomic_id")}
    atom_ids_used: list[str] = []
    for row in supplement:
        target = str(row.get("target_subject_pronoun") or "").lower()
        _require(target in TARGETS, f"invalid_target_subject_pronoun:{row.get('connected_id')}")
        utterances = _utterances(row)
        _require(utterances, f"utterances_required:{row.get('connected_id')}")
        _require(all("___" not in text and "[...]" not in text for text in utterances), f"learner_blank_forbidden:{row.get('connected_id')}")
        ids = [str(x) for x in row.get("atomic_source_ids", [])]
        _require(ids, f"atomic_source_ids_required:{row.get('connected_id')}")
        _require(all(x in atomic_by_id for x in ids), f"atomic_source_id_missing:{row.get('connected_id')}")
        atom_ids_used.extend(ids)
        if target in {"you", "we"}:
            target_lines = [x for x in utterances if _initial_pronoun(x) == target]
            _require(len(target_lines) == len(utterances), f"direct_target_only_required:{row.get('connected_id')}")
            atomic_texts = {str(atomic_by_id[x].get("text", "")).strip() for x in ids}
            _require(set(utterances).issubset(atomic_texts), f"direct_utterance_not_exact_atomic:{row.get('connected_id')}")
            for x in ids:
                atom = atomic_by_id[x]
                _require(str(atom.get("subject_pronoun", "")).lower() == target, f"direct_atomic_pronoun_mismatch:{x}")
                _require(atom.get("semantic_admission_class") == "APPROVE", f"direct_atomic_not_approved:{x}")
                _require(atom.get("reference_mode") == "DIRECT", f"direct_atomic_not_direct:{x}")
        else:
            meta = row.get("antecedent")
            _require(isinstance(meta, Mapping), f"it_antecedent_metadata_required:{row.get('connected_id')}")
            _require(meta.get("referent_type") == "SINGULAR_NONHUMAN", f"it_antecedent_nonhuman_required:{row.get('connected_id')}")
            _require(int(meta.get("utterance_index", -1)) == 0, f"it_antecedent_must_be_first:{row.get('connected_id')}")
            _require(str(meta.get("text", "")).strip() == utterances[0], f"it_antecedent_text_binding_required:{row.get('connected_id')}")
            source_atomic_id = str(meta.get("source_atomic_id") or "")
            _require(source_atomic_id in atomic_by_id, f"it_antecedent_source_atomic_required:{row.get('connected_id')}")
            source_identity = str(atomic_by_id[source_atomic_id].get("text", "")).strip()
            identity_match = re.match(r"^It is (a|an) (.+)\.$", source_identity, flags=re.I)
            _require(identity_match is not None, f"it_antecedent_identity_atomic_required:{row.get('connected_id')}")
            expected_antecedent = f"This is {identity_match.group(1)} {identity_match.group(2)}."
            _require(utterances[0] == expected_antecedent, f"it_antecedent_derivation_mismatch:{row.get('connected_id')}")
            _require(_initial_pronoun(utterances[0]) != "it", f"it_antecedent_must_precede_it:{row.get('connected_id')}")
            _require(all(_initial_pronoun(x) == "it" for x in utterances[1:]), f"it_chain_target_only_required:{row.get('connected_id')}")
            for x in ids:
                atom = atomic_by_id[x]
                if str(atom.get("subject_pronoun", "")).lower() == "it":
                    _require(atom.get("semantic_admission_class") in {"APPROVE", "CONTEXT_BOUND_APPROVE"}, f"it_atomic_not_approved:{x}")
                    _require(atom.get("reference_mode") == "REFERENCE_BOUND", f"it_atomic_not_reference_bound:{x}")

    add = pronoun_counts(supplement)
    base = pronoun_counts(base_rows)
    combined = base + add
    for p, minimum in contract["additional_minimums"].items():
        _require(add[p] >= int(minimum), f"additional_pronoun_minimum_not_met:{p}:{add[p]}<{minimum}")
    for p, minimum in contract["combined_minimums"].items():
        _require(combined[p] >= int(minimum), f"combined_pronoun_minimum_not_met:{p}:{combined[p]}<{minimum}")
    _require(all(combined[p] > 0 for p in ALL_PRONOUNS), "combined_seven_pronoun_coverage_required")

    direct_surfaces = [text for row in supplement if str(row.get("target_subject_pronoun", "")).lower() in {"you", "we"} for text in _utterances(row)]
    _require(len(direct_surfaces) == len(set(direct_surfaces)), "you_we_supplement_exact_repeat_forbidden")

    receipt_core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "supplement_set_count": len(supplement),
        "supplement_utterance_count": sum(len(_utterances(row)) for row in supplement),
        "additional_sentence_initial_pronoun_counts": {p: add[p] for p in TARGETS},
        "combined_sentence_initial_pronoun_counts": {p: combined[p] for p in ALL_PRONOUNS},
        "base_set_count": len(base_rows),
        "base_utterance_count": sum(len(_utterances(row)) for row in base_rows),
        "atomic_source_id_count": len(set(atom_ids_used)),
        "append_only_base_ids_unchanged": True,
        "it_antecedent_policy_pass": True,
        "a2_unlocked": False
    }
    receipt_sha = hashlib.sha256(json.dumps(receipt_core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**receipt_core, "receipt_sha256": receipt_sha, "validation_status": PASS_STATUS}

def validate_files(*, payload_path: Path, base_layer2_path: Path, atomic_pool_path: Path, contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = _load(contract_path)
    _require(_sha(base_layer2_path) == contract["base_sources"]["layer2_data_sha256"], "base_layer2_sha256_mismatch")
    _require(_sha(atomic_pool_path) == contract["base_sources"]["atomic_pool_sha256"], "atomic_pool_sha256_mismatch")
    base_rows = _rows(_load(base_layer2_path))
    atomic_rows = _rows(_load(atomic_pool_path))
    payload = _load(payload_path)
    _require(isinstance(payload, Mapping), "payload_object_required")
    return validate_payload(payload, base_rows=base_rows, atomic_rows=atomic_rows, contract=contract)
