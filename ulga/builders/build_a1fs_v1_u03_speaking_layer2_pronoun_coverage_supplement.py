#!/usr/bin/env python3
"""Append-only Unit03 Speaking Layer2 supplement for you/we/it coverage.

The accepted 200-set Layer2 artifact is read-only. This builder derives a separate
policy-bound speaking supplement from approved Unit03 atomic sentences and
accepted Layer2/Q10 scene donors; it never edits or replaces existing records.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.validators import validate_a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement as supplement_validator

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"
TASK_ID = "A1FS-V1-U03SPK-L2-PCOV_AppendOnlySubjectPronounCoverageSupplement"
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement_contract.json"

SAFE_SEE_OBJECTS = {
    "book", "books", "pen", "pens", "pencil", "pencils", "bag", "bags", "page", "pages",
    "letter", "letters", "picture", "pictures", "photo", "photos", "computer", "computers",
    "desk", "desks", "table", "tables", "chair", "chairs", "question", "questions", "answer", "answers",
    "game", "games", "ball", "balls", "cd", "cds", "dvd", "dvds", "camera", "cameras", "teacher", "teachers"
}
SAFE_HAVE_OBJECTS = {
    "book", "books", "pen", "pens", "pencil", "pencils", "bag", "bags", "page", "pages",
    "letter", "letters", "picture", "pictures", "photo", "photos", "question", "questions", "answer", "answers",
    "game", "games", "ball", "balls", "cd", "cds", "dvd", "dvds", "camera", "cameras"
}
SAFE_LIKE_OBJECTS = {"book", "books", "music", "game", "games", "picture", "pictures", "photo", "photos", "football", "basketball", "film", "films", "movie", "movies", "stories", "story"}
SAFE_ACTION_BODIES = {
    "ask a question.", "ask a teacher.", "invite friends.", "invite a friend.", "learn at school.",
    "listen to music.", "meet a teacher.", "meet friends.", "play football.", "play a game.",
    "read books.", "study at school.", "visit family.", "visit friends.", "watch a game.",
    "watch football.", "write a sentence.", "write sentences."
}
SAFE_IT_NOUNS = {"book", "pen", "player", "apple", "bag", "box", "room"}
IT_ATTRIBUTE_TEXTS = ("It is small.", "It is big.", "It is red.", "It is blue.", "It is new.", "It is old.")

class SupplementBuildError(ValueError):
    pass

def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SupplementBuildError(message)

def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
    raise SupplementBuildError("records_list_not_found")

def _utterances(row: Mapping[str, Any]) -> list[str]:
    value = row.get("utterances")
    return [str(x).strip() for x in value if str(x).strip()] if isinstance(value, list) else []

def _body(text: str, pronoun: str) -> str:
    return re.sub(rf"^{pronoun}\s+", "", text.strip(), count=1, flags=re.I).lower()

def _contains_word(text: str, words: set[str]) -> bool:
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    return bool(tokens & words)

def _safe_direct_atomic(row: Mapping[str, Any], pronoun: str) -> bool:
    if str(row.get("subject_pronoun", "")).lower() != pronoun:
        return False
    if row.get("semantic_admission_class") != "APPROVE" or row.get("reference_mode") != "DIRECT":
        return False
    text = str(row.get("text", "")).strip()
    if not re.match(rf"^{pronoun.capitalize()}\b", text):
        return False
    body = _body(text, pronoun)
    if body in SAFE_ACTION_BODIES:
        return True
    if body.startswith("can see "):
        return _contains_word(body, SAFE_SEE_OBJECTS)
    if body.startswith("have "):
        return _contains_word(body, SAFE_HAVE_OBJECTS)
    if body.startswith("like ") or body.startswith("don't like "):
        return _contains_word(body, SAFE_LIKE_OBJECTS)
    if body.startswith("can play ") and ("football" in body or "game" in body):
        return True
    if body.startswith("can learn at school") or body.startswith("can study at school"):
        return True
    return False

def _paired_direct_rows(atomic_rows: Sequence[Mapping[str, Any]], base_surfaces: set[str], needed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_pronoun: dict[str, dict[str, dict[str, Any]]] = {"you": {}, "we": {}}
    for pronoun in ("you", "we"):
        for row in atomic_rows:
            if not _safe_direct_atomic(row, pronoun):
                continue
            text = str(row.get("text", "")).strip()
            if text in base_surfaces:
                continue
            by_pronoun[pronoun].setdefault(_body(text, pronoun), dict(row))
    shared = sorted(set(by_pronoun["you"]) & set(by_pronoun["we"]))
    _require(len(shared) >= needed, f"insufficient_safe_paired_you_we_atomic_capacity:{len(shared)}<{needed}")
    shared = shared[:needed]
    return ([by_pronoun["you"][x] for x in shared], [by_pronoun["we"][x] for x in shared])

def _it_anchor_candidates(atomic_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_nouns: set[str] = set()
    for row in atomic_rows:
        if str(row.get("subject_pronoun", "")).lower() != "it":
            continue
        if row.get("semantic_admission_class") not in {"APPROVE", "CONTEXT_BOUND_APPROVE"}:
            continue
        if row.get("reference_mode") != "REFERENCE_BOUND":
            continue
        text = str(row.get("text", "")).strip()
        match = re.match(r"^It is (a|an) (.+)\.$", text, flags=re.I)
        if not match:
            continue
        phrase = match.group(2).lower()
        tokens = re.findall(r"[a-z]+", phrase)
        noun = tokens[-1] if tokens else ""
        if noun not in SAFE_IT_NOUNS or noun in seen_nouns:
            continue
        seen_nouns.add(noun)
        value = dict(row)
        value["_article"] = match.group(1).lower()
        value["_noun_phrase"] = match.group(2)
        value["_noun"] = noun
        out.append(value)
    return sorted(out, key=lambda x: str(x.get("atomic_id", "")))

def _it_attribute_rows(atomic_rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    wanted = set(IT_ATTRIBUTE_TEXTS)
    found: dict[str, dict[str, Any]] = {}
    for row in atomic_rows:
        text = str(row.get("text", "")).strip()
        if text not in wanted:
            continue
        if str(row.get("subject_pronoun", "")).lower() != "it":
            continue
        if row.get("semantic_admission_class") not in {"APPROVE", "CONTEXT_BOUND_APPROVE"} or row.get("reference_mode") != "REFERENCE_BOUND":
            continue
        found[text] = dict(row)
    _require(len(found) >= 5, f"insufficient_reference_bound_it_attributes:{len(found)}<5")
    return found

def _attrs_for_phrase(phrase: str, available: Mapping[str, Mapping[str, Any]], index: int) -> list[dict[str, Any]]:
    lower = phrase.lower()
    size = "It is small." if "big" not in lower else "It is big."
    if "small" in lower:
        size = "It is small."
    color = "It is red." if index % 2 == 0 else "It is blue."
    if "blue" in lower:
        color = "It is blue."
    elif "red" in lower:
        color = "It is red."
    age = "It is new." if index % 2 == 0 else "It is old."
    if "old" in lower:
        age = "It is old."
    elif "new" in lower:
        age = "It is new."
    chosen = [size, color, age]
    missing = [x for x in chosen if x not in available]
    _require(not missing, f"required_it_attribute_atomic_missing:{missing}")
    return [dict(available[x]) for x in chosen]

def _donors(base_rows: Sequence[Mapping[str, Any]], family: str) -> list[dict[str, Any]]:
    rows = [dict(x) for x in base_rows if str(x.get("family", "")) == family and x.get("q10_source_item_id")]
    if not rows:
        rows = [dict(x) for x in base_rows if x.get("q10_source_item_id")]
    _require(bool(rows), "accepted_q10_scene_donor_required")
    return rows

def _make_direct_cards(pronoun: str, rows: Sequence[Mapping[str, Any]], donors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card_idx in range(12):
        group = [dict(x) for x in rows[card_idx * 4:(card_idx + 1) * 4]]
        donor = donors[card_idx % len(donors)]
        cards.append({
            "connected_id": f"U03-CONN-SUP-{pronoun.upper()}-{card_idx + 1:03d}",
            "family": "F_PERSONAL_SPEAKING",
            "title": f"Pronoun Coverage · {pronoun.capitalize()} · {card_idx + 1:02d}",
            "purpose": f"Keep {pronoun} as the subject across four already-approved complete utterances.",
            "scene_family": donor.get("scene_family"),
            "scene_location": donor.get("scene_location"),
            "q10_source_item_id": donor.get("q10_source_item_id"),
            "target_subject_pronoun": pronoun,
            "atomic_source_ids": [x["atomic_id"] for x in group],
            "lexical_source_sentence_ids": [x.get("source_sentence_id") for x in group if x.get("source_sentence_id")],
            "support_note": "Append-only coverage supplement. Every learner utterance is an exact approved DIRECT Unit03 atomic sentence.",
            "utterances": [str(x["text"]).strip() for x in group]
        })
    return cards

def _make_it_cards(anchor_rows: Sequence[Mapping[str, Any]], attrs: Mapping[str, Mapping[str, Any]], donors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    _require(len(anchor_rows) >= 7, f"insufficient_safe_it_anchor_capacity:{len(anchor_rows)}<7")
    cards: list[dict[str, Any]] = []
    for idx in range(14):
        anchor_source = anchor_rows[idx % len(anchor_rows)]
        donor = donors[idx % len(donors)]
        phrase = str(anchor_source["_noun_phrase"])
        article = str(anchor_source["_article"])
        if str(anchor_source["_noun"]) == "apple":
            chosen = ("It is small.", "It is red.", "It is old.")
            _require(all(text in attrs for text in chosen), "required_apple_it_attribute_atomic_missing")
            attr_rows = [dict(attrs[text]) for text in chosen]
        else:
            attr_rows = _attrs_for_phrase(phrase, attrs, idx)
        anchor_text = f"This is {article} {phrase}."
        cards.append({
            "connected_id": f"U03-CONN-SUP-IT-{idx + 1:03d}",
            "family": "E_SHOW_AND_TELL",
            "title": f"Object Reference · It · {idx + 1:02d}",
            "purpose": "Name one singular non-human object first, then track the same referent with It.",
            "scene_family": donor.get("scene_family"),
            "scene_location": donor.get("scene_location"),
            "q10_source_item_id": donor.get("q10_source_item_id"),
            "target_subject_pronoun": "it",
            "atomic_source_ids": [anchor_source["atomic_id"], *[x["atomic_id"] for x in attr_rows]],
            "lexical_source_sentence_ids": [x.get("source_sentence_id") for x in [anchor_source, *attr_rows] if x.get("source_sentence_id")],
            "support_note": "The first line establishes a singular non-human antecedent. All It lines use approved REFERENCE_BOUND atomics; empty/expletive it is forbidden.",
            "antecedent": {
                "utterance_index": 0,
                "text": anchor_text,
                "referent_type": "SINGULAR_NONHUMAN",
                "noun": anchor_source["_noun"],
                "source_atomic_id": anchor_source["atomic_id"],
                "derivation": "THIS_IS_ANTECEDENT_FROM_APPROVED_IT_IDENTITY_ATOMIC"
            },
            "utterances": [anchor_text, *[str(x["text"]).strip() for x in attr_rows]]
        })
    return cards

def build_supplement(*, base_layer2_path: Path, atomic_pool_path: Path, contract_path: Path = CONTRACT_PATH) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _load(contract_path)
    _require(_sha(base_layer2_path) == contract["base_sources"]["layer2_data_sha256"], "base_layer2_sha256_mismatch")
    _require(_sha(atomic_pool_path) == contract["base_sources"]["atomic_pool_sha256"], "atomic_pool_sha256_mismatch")
    base_rows = _rows(_load(base_layer2_path))
    atomic_rows = _rows(_load(atomic_pool_path))
    base_surfaces = {text for row in base_rows for text in _utterances(row)}
    you_rows, we_rows = _paired_direct_rows(atomic_rows, base_surfaces, 48)
    personal_donors = _donors(base_rows, "F_PERSONAL_SPEAKING")
    object_donors = _donors(base_rows, "E_SHOW_AND_TELL")
    anchors = _it_anchor_candidates(atomic_rows)
    attrs = _it_attribute_rows(atomic_rows)
    supplement_records = [
        *_make_direct_cards("you", you_rows, personal_donors),
        *_make_direct_cards("we", we_rows, personal_donors),
        *_make_it_cards(anchors, attrs, object_donors),
    ]
    payload = {
        "schema_version": contract["schema_version"],
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "task_id": TASK_ID,
        "append_only": True,
        "base_attestation": {
            "layer2_data_sha256": _sha(base_layer2_path),
            "atomic_pool_sha256": _sha(atomic_pool_path),
            "base_connected_set_count": len(base_rows),
            "base_utterance_count": sum(len(_utterances(x)) for x in base_rows)
        },
        "supplement_records": supplement_records,
        "a2_unlocked": False
    }
    qa = supplement_validator.validate_payload(payload, base_rows=base_rows, atomic_rows=atomic_rows, contract=contract)
    return payload, qa

def render_html(records: Sequence[Mapping[str, Any]]) -> str:
    cards = []
    for row in records:
        lines = "".join(f"<li>{html.escape(text)}</li>" for text in row.get("utterances", []))
        cards.append(f"<article class='card'><h2>{html.escape(str(row.get('title','')))}</h2><div class='meta'>{html.escape(str(row.get('connected_id','')))} · {html.escape(str(row.get('scene_family','')))}</div><ol>{lines}</ol></article>")
    return "<!doctype html><html><head><meta charset='utf-8'><title>Unit03 Layer2 Pronoun Coverage Supplement</title><style>@page{size:A4 landscape;margin:8mm}body{font-family:Arial,sans-serif;margin:0}.page{display:grid;grid-template-columns:1fr 1fr;gap:6mm}.card{break-inside:avoid;border:1px solid #aaa;border-radius:6px;padding:4mm;margin-bottom:5mm}.card h2{font-size:13pt;margin:0 0 1mm}.meta{font-size:8pt;color:#666}.card li{font-size:11pt;line-height:1.45}</style></head><body><main class='page'>" + "".join(cards) + "</main></body></html>"

def materialize(*, base_layer2_path: Path, atomic_pool_path: Path, output_dir: Path, contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    payload, qa = build_supplement(base_layer2_path=base_layer2_path, atomic_pool_path=atomic_pool_path, contract_path=contract_path)
    contract = _load(contract_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=contract["level_scope"],
        source_bindings={
            "base_layer2_data_sha256": payload["base_attestation"]["layer2_data_sha256"],
            "atomic_pool_sha256": payload["base_attestation"]["atomic_pool_sha256"],
            "unit03_production_acceptance_manifest": "ulga/contracts/a1fs_v1_unit03_production_acceptance_manifest.json"
        }
    )
    approved = policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[{"validator_id": qa["validator_id"], "status": "PASS", "receipt_sha256": qa["receipt_sha256"]}],
        decision_ref="U03_LAYER2_PRONOUN_COVERAGE_SUPPLEMENT_DETERMINISTIC_ADMISSION",
        producer_id=TASK_ID
    )
    projection_payload = {
        "skill": "SPEAKING",
        "prompt": "Read, shadow, and speak the connected pronoun-focus cards. Keep the named or shown referent clear.",
        "response_mode": "CONNECTED_ORAL_PRACTICE",
        "support_level": "GUIDED_TO_REDUCED_SUPPORT",
        "initiative_level": "CONTROLLED_PRACTICE",
        "scoring_contract": {"mode": "PRACTICE_ONLY_NO_MASTERY", "target": "SUBJECT_PRONOUN_REFERENCE"},
        "evidence_level": "PRACTICE_EVIDENCE_ONLY",
        "source_bindings": approved["source_bindings"],
        "content_identity": {"unit_id": UNIT_ID, "task_id": TASK_ID, "supplement": "LAYER2_YOU_WE_IT_APPEND_ONLY"},
        "supplement_records": payload["supplement_records"]
    }
    projection = policy_artifact.build_four_skill_projection(
        approved,
        skill="SPEAKING",
        projection_payload=projection_payload,
        producer_id=TASK_ID
    )
    paths = {
        "candidate": output_dir / "Unit03_Connected_Speaking_Layer2_PronounCoverage_Supplement_Candidate.json",
        "approved": output_dir / "Unit03_Connected_Speaking_Layer2_PronounCoverage_Supplement_Approved.json",
        "projection": output_dir / "Unit03_Connected_Speaking_Layer2_PronounCoverage_Supplement_Speaking.json",
        "qa": output_dir / "Unit03_Connected_Speaking_Layer2_PronounCoverage_Supplement_QA.json",
        "html": output_dir / "Unit03_Connected_Speaking_Layer2_PronounCoverage_Supplement_A4.html"
    }
    _write(paths["candidate"], candidate)
    _write(paths["approved"], approved)
    _write(paths["projection"], projection)
    _write(paths["qa"], qa)
    paths["html"].write_text(render_html(payload["supplement_records"]), encoding="utf-8")
    return {"status": qa["validation_status"], "outputs": {k: str(v) for k, v in paths.items()}, "qa": qa}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-layer2-data", type=Path, required=True)
    parser.add_argument("--atomic-pool", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    result = materialize(base_layer2_path=args.base_layer2_data, atomic_pool_path=args.atomic_pool, output_dir=args.output_dir, contract_path=args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
