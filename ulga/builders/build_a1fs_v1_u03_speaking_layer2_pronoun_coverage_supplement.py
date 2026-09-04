#!/usr/bin/env python3
"""Append-only Unit03 Layer2 C-I supplement for missing You/We/It coverage.

The accepted 200-set / 1,270-utterance LexicalFullFix artifact is read-only.
New cards must reuse the formal Layer2 families:
- We  -> Part C Sentence Chaining
- It  -> Part E Show and Tell
- You -> Part H Interaction / Role-play
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
TASK_ID = "A1FS-V1-U03SPK-L2-PCOV_AppendOnlyConnectedCIPronounCoverage"
REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement_contract.json"

FAMILY_C = "C_SENTENCE_CHAINING"
FAMILY_E = "E_SHOW_AND_TELL"
FAMILY_H = "H_INTERACTION_ROLEPLAY"
SAFE_IT_NOUNS = {"book", "pen", "player", "apple", "bag", "box", "room"}
IT_ATTRIBUTE_TEXTS = (
    "It is small.", "It is big.", "It is red.",
    "It is blue.", "It is new.", "It is old.",
)
SCENE_KEYWORDS = {
    "SCHOOL_CLASSROOM_LEARNING": {"school", "class", "classroom", "teacher", "question", "answer", "sentence", "page", "book", "pen", "pencil", "desk"},
    "COMMUNICATION_WRITING": {"write", "letter", "message", "note", "word", "sentence", "page", "pen", "pencil"},
    "SPORTS_PLAY": {"play", "football", "basketball", "ball", "game"},
    "MUSIC_DANCE": {"music", "listen", "cd", "guitar", "dance"},
    "MEDIA_ENTERTAINMENT_TECH": {"film", "movie", "dvd", "camera", "computer", "game"},
    "FAMILY_PEOPLE_SOCIAL": {"family", "friend", "friends", "invite", "meet", "home"},
    "TOWN_PUBLIC_PLACES": {"town", "park", "library", "station", "street"},
    "TRANSPORT_TRAVEL": {"train", "station", "road", "travel"},
    "HOME_BEDROOM_LIVING": {"home", "bedroom", "living", "room", "bed"},
    "SHOP_MONEY_SERVICES": {"shop", "money", "shirt", "coat", "bag"},
    "PARK_GARDEN_NATURE": {"park", "garden", "flower", "tree"},
    "PETS_FARM_ZOO": {"pet", "cat", "dog", "animal", "zoo", "farm"},
}


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


def _body(text: str, pronoun: str) -> str:
    return re.sub(rf"^{pronoun}\s+", "", text.strip(), count=1, flags=re.I).lower()


def _direct_atomic(row: Mapping[str, Any], pronoun: str) -> bool:
    text = str(row.get("text", "")).strip()
    return (
        str(row.get("subject_pronoun", "")).lower() == pronoun
        and row.get("semantic_admission_class") == "APPROVE"
        and row.get("reference_mode") == "DIRECT"
        and re.match(rf"^{pronoun.capitalize()}\b", text) is not None
    )


def _shared_i_you_we_rows(
    atomic_rows: Sequence[Mapping[str, Any]],
    *,
    base_surfaces: set[str],
    needed: int,
) -> dict[str, list[dict[str, Any]]]:
    by_pronoun: dict[str, dict[str, dict[str, Any]]] = {"i": {}, "you": {}, "we": {}}
    for pronoun in by_pronoun:
        for row in atomic_rows:
            if not _direct_atomic(row, pronoun):
                continue
            text = str(row.get("text", "")).strip()
            if text in base_surfaces:
                continue
            by_pronoun[pronoun].setdefault(_body(text, pronoun), dict(row))

    shared = set(by_pronoun["i"]) & set(by_pronoun["you"]) & set(by_pronoun["we"])
    _require(len(shared) >= needed, f"insufficient_shared_i_you_we_direct_capacity:{len(shared)}<{needed}")

    def topic_key(body: str) -> tuple[str, str]:
        tokens = set(re.findall(r"[a-z]+", body))
        best = "ZZ_GENERIC"
        best_score = 0
        for scene, words in SCENE_KEYWORDS.items():
            score = len(tokens & words)
            if score > best_score:
                best, best_score = scene, score
        return best, body

    selected = sorted(shared, key=topic_key)[:needed]
    return {pronoun: [by_pronoun[pronoun][body] for body in selected] for pronoun in by_pronoun}


def _donors(base_rows: Sequence[Mapping[str, Any]], family: str) -> list[dict[str, Any]]:
    rows = [
        dict(x) for x in base_rows
        if str(x.get("family", "")) == family and x.get("q10_source_item_id")
    ]
    _require(bool(rows), f"accepted_layer2_donor_required:{family}")
    return rows


def _best_donor(donors: Sequence[Mapping[str, Any]], texts: Sequence[str], index: int) -> dict[str, Any]:
    tokens = set(re.findall(r"[a-z]+", " ".join(texts).lower()))
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for donor_index, donor in enumerate(donors):
        scene = str(donor.get("scene_family", ""))
        loc_tokens = set(re.findall(r"[a-z]+", str(donor.get("scene_location", "")).lower()))
        score = len(tokens & SCENE_KEYWORDS.get(scene, set())) * 3 + len(tokens & loc_tokens)
        ranked.append((score, -donor_index, dict(donor)))
    max_score = max(score for score, _, _ in ranked)
    if max_score <= 0:
        return dict(donors[index % len(donors)])
    candidates = [row for score, _, row in ranked if score == max_score]
    return candidates[index % len(candidates)]


def _lineage_fields(donor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scene_family": donor.get("scene_family"),
        "scene_location": donor.get("scene_location"),
        "q10_source_item_id": donor.get("q10_source_item_id"),
        "source_layer2_connected_id": donor.get("connected_id"),
    }


def _make_we_c_cards(
    we_rows: Sequence[Mapping[str, Any]],
    donors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _require(len(we_rows) >= 48, "we_rows_48_required")
    cards: list[dict[str, Any]] = []
    for idx in range(8):
        group = [dict(x) for x in we_rows[idx * 6:(idx + 1) * 6]]
        texts = [str(x["text"]).strip() for x in group]
        donor = _best_donor(donors, texts, idx)
        cards.append({
            "connected_id": f"U03-CONN-SUP-C-WE-{idx + 1:03d}",
            "family": FAMILY_C,
            "title": f"Sentence Chain · We {idx + 1:02d}",
            "purpose": "Keep We as one stable group subject across a six-sentence connected practice chain.",
            **_lineage_fields(donor),
            "target_subject_pronoun": "we",
            "atomic_source_ids": [x["atomic_id"] for x in group],
            "lexical_source_sentence_ids": [x.get("source_sentence_id") for x in group if x.get("source_sentence_id")],
            "support_note": "Part C append-only supplement. Six exact approved DIRECT We atomics are practised as one group-reference chain inside an accepted Unit03 scene.",
            "utterances": texts,
        })
    return cards


def _make_you_h_cards(
    you_rows: Sequence[Mapping[str, Any]],
    i_rows: Sequence[Mapping[str, Any]],
    donors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    _require(len(you_rows) >= 48 and len(i_rows) >= 48, "you_i_rows_48_required")
    cards: list[dict[str, Any]] = []
    for idx in range(12):
        you_group = [dict(x) for x in you_rows[idx * 4:(idx + 1) * 4]]
        i_group = [dict(x) for x in i_rows[idx * 4:(idx + 1) * 4]]
        turns: list[dict[str, str]] = []
        ids: list[str] = []
        lexical_ids: list[str] = []
        for you_row, i_row in zip(you_group, i_group):
            _require(_body(str(you_row["text"]), "you") == _body(str(i_row["text"]), "i"), "you_i_body_pair_mismatch")
            turns.extend([
                {"speaker": "A", "text": str(you_row["text"]).strip()},
                {"speaker": "B", "text": str(i_row["text"]).strip()},
            ])
            ids.extend([str(you_row["atomic_id"]), str(i_row["atomic_id"])])
            lexical_ids.extend(
                str(x) for x in (you_row.get("source_sentence_id"), i_row.get("source_sentence_id")) if x
            )
        texts = [x["text"] for x in turns]
        donor = _best_donor(donors, texts, idx)
        cards.append({
            "connected_id": f"U03-CONN-SUP-H-YOU-{idx + 1:03d}",
            "family": FAMILY_H,
            "title": f"Partner Reference · You / I {idx + 1:02d}",
            "purpose": "Practise speaker-reference switching: A addresses You and B answers with the matching I statement.",
            **_lineage_fields(donor),
            "target_subject_pronoun": "you",
            "atomic_source_ids": ids,
            "lexical_source_sentence_ids": lexical_ids,
            "support_note": "Part H append-only interaction. A/B turns alternate; each You statement and matching I response are exact approved DIRECT Unit03 atomics with the same predicate body.",
            "turns": turns,
            "utterances": texts,
        })
    return cards


def _atomic_by_text(atomic_rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in atomic_rows:
        text = str(row.get("text", "")).strip()
        if text and text not in out:
            out[text] = dict(row)
    return out


def _safe_it_identity_from_donor(
    donor: Mapping[str, Any],
    atomic_texts: Mapping[str, Mapping[str, Any]],
) -> tuple[str, dict[str, Any], str] | None:
    utterances = _utterances(donor)
    if not utterances:
        return None
    match = re.match(r"^This is (a|an) (.+)\.$", utterances[0], flags=re.I)
    if not match:
        return None
    phrase = match.group(2)
    tokens = re.findall(r"[a-z]+", phrase.lower())
    noun = tokens[-1] if tokens else ""
    if noun not in SAFE_IT_NOUNS:
        return None
    identity = f"It is {match.group(1)} {phrase}."
    atom = atomic_texts.get(identity)
    if not atom:
        return None
    if (
        str(atom.get("subject_pronoun", "")).lower() != "it"
        or atom.get("semantic_admission_class") not in {"APPROVE", "CONTEXT_BOUND_APPROVE"}
        or atom.get("reference_mode") != "REFERENCE_BOUND"
    ):
        return None
    return utterances[0], dict(atom), noun


def _it_attr_pairs(noun: str, phrase: str) -> list[tuple[str, str]]:
    lower = phrase.lower()
    if noun == "apple":
        pairs = [("It is small.", "It is red."), ("It is red.", "It is old."), ("It is small.", "It is old.")]
    elif noun == "box":
        pairs = [("It is big.", "It is red."), ("It is small.", "It is blue."), ("It is big.", "It is new.")]
    elif noun == "room":
        pairs = [("It is big.", "It is new."), ("It is small.", "It is old."), ("It is big.", "It is old.")]
    elif noun == "player":
        pairs = [("It is new.", "It is red."), ("It is old.", "It is blue."), ("It is new.", "It is blue.")]
    else:
        pairs = [("It is red.", "It is new."), ("It is blue.", "It is old."), ("It is red.", "It is old."), ("It is blue.", "It is new.")]

    def contradictory(pair: tuple[str, str]) -> bool:
        joined = " ".join(pair).lower()
        if " red " in f" {lower} " and "blue." in joined:
            return True
        if " blue " in f" {lower} " and "red." in joined:
            return True
        if " new " in f" {lower} " and "old." in joined:
            return True
        if " old " in f" {lower} " and "new." in joined:
            return True
        if " big " in f" {lower} " and "small." in joined:
            return True
        if " small " in f" {lower} " and "big." in joined:
            return True
        return False

    filtered = [pair for pair in pairs if not contradictory(pair)]
    return filtered or pairs[:1]


def _make_it_e_cards(
    atomic_rows: Sequence[Mapping[str, Any]],
    donors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    atomic_texts = _atomic_by_text(atomic_rows)
    attr_atoms = {
        text: dict(atomic_texts[text])
        for text in IT_ATTRIBUTE_TEXTS
        if text in atomic_texts
        and str(atomic_texts[text].get("subject_pronoun", "")).lower() == "it"
        and atomic_texts[text].get("semantic_admission_class") in {"APPROVE", "CONTEXT_BOUND_APPROVE"}
        and atomic_texts[text].get("reference_mode") == "REFERENCE_BOUND"
    }
    candidates: list[tuple[dict[str, Any], str, dict[str, Any], str]] = []
    for donor in donors:
        if "Object" not in str(donor.get("title", "")):
            continue
        resolved = _safe_it_identity_from_donor(donor, atomic_texts)
        if resolved is None:
            continue
        antecedent, identity_atom, noun = resolved
        candidates.append((dict(donor), antecedent, identity_atom, noun))
    _require(bool(candidates), "accepted_singular_e_object_donor_with_reference_bound_identity_required")

    cards: list[dict[str, Any]] = []
    attempts = 0
    while len(cards) < 14 and attempts < 200:
        donor, antecedent, identity_atom, noun = candidates[attempts % len(candidates)]
        phrase_match = re.match(r"^This is (?:a|an) (.+)\.$", antecedent, flags=re.I)
        _require(phrase_match is not None, "it_antecedent_phrase_required")
        phrase = phrase_match.group(1)
        pairs = _it_attr_pairs(noun, phrase)
        pair = pairs[(attempts // len(candidates)) % len(pairs)]
        attempts += 1
        if not all(text in attr_atoms for text in pair):
            continue

        donor_support = [
            text for text in _utterances(donor)[1:]
            if not re.match(r"^\s*It\b", text) and text != antecedent
        ]
        if len(donor_support) < 2:
            continue
        support = donor_support[:2]
        target_atoms = [dict(identity_atom), dict(attr_atoms[pair[0]]), dict(attr_atoms[pair[1]])]
        texts = [antecedent, *[str(x["text"]).strip() for x in target_atoms], *support]
        index = len(cards)
        cards.append({
            "connected_id": f"U03-CONN-SUP-E-IT-{index + 1:03d}",
            "family": FAMILY_E,
            "title": f"Show and Tell · Object Reference · It {index + 1:02d}",
            "purpose": "Name one singular non-human object, keep that referent active, and describe it with It.",
            **_lineage_fields(donor),
            "target_subject_pronoun": "it",
            "atomic_source_ids": [str(x["atomic_id"]) for x in target_atoms],
            "lexical_source_sentence_ids": [
                str(x.get("source_sentence_id")) for x in target_atoms if x.get("source_sentence_id")
            ],
            "source_layer2_support_utterances": support,
            "support_note": "Part E append-only Show and Tell. The first row establishes the object; rows 2-4 are exact approved REFERENCE_BOUND It atomics; rows 5-6 are copied from the accepted E-object donor.",
            "antecedent": {
                "utterance_index": 0,
                "text": antecedent,
                "referent_type": "SINGULAR_NONHUMAN",
                "noun": noun,
                "source_atomic_id": identity_atom["atomic_id"],
                "derivation": "THIS_IS_ANTECEDENT_FROM_APPROVED_IT_IDENTITY_ATOMIC",
            },
            "utterances": texts,
        })
    _require(len(cards) == 14, f"insufficient_natural_it_e_card_capacity:{len(cards)}<14")
    return cards


def build_supplement(
    *,
    base_layer2_path: Path,
    atomic_pool_path: Path,
    contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _load(contract_path)
    _require(_sha(base_layer2_path) == contract["base_sources"]["layer2_data_sha256"], "base_layer2_sha256_mismatch")
    _require(_sha(atomic_pool_path) == contract["base_sources"]["atomic_pool_sha256"], "atomic_pool_sha256_mismatch")

    base_rows = _rows(_load(base_layer2_path))
    atomic_rows = _rows(_load(atomic_pool_path))
    _require(len(base_rows) == int(contract["base_sources"]["base_connected_sets"]), "base_connected_set_count_mismatch")
    _require(sum(len(_utterances(x)) for x in base_rows) == int(contract["base_sources"]["base_utterances"]), "base_utterance_count_mismatch")

    base_surfaces = {text for row in base_rows for text in _utterances(row)}
    shared = _shared_i_you_we_rows(atomic_rows, base_surfaces=base_surfaces, needed=48)

    supplement_records = [
        *_make_we_c_cards(shared["we"], _donors(base_rows, FAMILY_C)),
        *_make_it_e_cards(atomic_rows, _donors(base_rows, FAMILY_E)),
        *_make_you_h_cards(shared["you"], shared["i"], _donors(base_rows, FAMILY_H)),
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
            "base_utterance_count": sum(len(_utterances(x)) for x in base_rows),
        },
        "supplement_records": supplement_records,
        "a2_unlocked": False,
    }
    qa = supplement_validator.validate_payload(
        payload, base_rows=base_rows, atomic_rows=atomic_rows, contract=contract
    )
    return payload, qa


PART_TITLES = {
    FAMILY_C: "Part C · Sentence Chaining",
    FAMILY_E: "Part E · Show and Tell",
    FAMILY_H: "Part H · Interaction / Role-play",
}


def render_html(records: Sequence[Mapping[str, Any]]) -> str:
    ordered: list[dict[str, Any]] = []
    for family in (FAMILY_C, FAMILY_E, FAMILY_H):
        ordered.extend(dict(x) for x in records if x.get("family") == family)

    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for family in (FAMILY_C, FAMILY_E, FAMILY_H):
        rows = [x for x in ordered if x.get("family") == family]
        per_page = 2 if family == FAMILY_H else 4
        for start in range(0, len(rows), per_page):
            groups.append((family, rows[start:start + per_page]))

    total_pages = len(groups)
    pages: list[str] = []
    for page_no, (family, rows) in enumerate(groups, start=1):
        cards = []
        for row in rows:
            turn_speakers = [str(x.get("speaker", "")) for x in row.get("turns", []) if isinstance(x, Mapping)]
            line_html = []
            for idx, text in enumerate(_utterances(row), start=1):
                speaker = ""
                if family == FAMILY_H and idx <= len(turn_speakers):
                    speaker = f"<span class='speaker'>{html.escape(turn_speakers[idx-1])}:</span> "
                line_html.append(
                    "<div class='row'>"
                    f"<div class='num'>{idx}</div>"
                    f"<div class='sentence'>{speaker}{html.escape(text)}</div>"
                    "<div class='checks'>R<span class='check'></span>S<span class='check'></span>M<span class='check'></span></div>"
                    "</div>"
                )
            min_height = "172mm" if family == FAMILY_H else "83mm"
            cards.append(
                f"<div class='card' style='min-height:{min_height}'>"
                "<div class='card-head'><div>"
                f"<div class='card-title'>{html.escape(str(row.get('title','')))}</div>"
                f"<div class='card-meta'>{html.escape(str(row.get('connected_id','')))} · {html.escape(str(row.get('scene_family','')))}</div>"
                "</div><div class='rounds'>R Read · S Shadow · M Memory</div></div>"
                + "".join(line_html)
                + "</div>"
            )
        pages.append(
            "<section class='page'>"
            "<div class='header'><div>"
            f"<div class='title'>Unit 03 · Connected Speaking · {PART_TITLES[family]}</div>"
            "<div class='subtitle'>Pronoun Coverage FullFix · append-only C-I supplement using accepted Unit03 Layer2 scenes and admitted atomic sentences.</div>"
            f"</div><div class='page-no'>Page {page_no} / {total_pages}</div></div>"
            f"<div class='grid'>{''.join(cards)}</div>"
            "<div class='footer'><div>Layer 2 · High chunk repetition + high lexical variation</div><div>R Read · S Shadow · M Memory</div></div>"
            "</section>"
        )
    return """<!doctype html><html><head><meta charset='utf-8'>
<title>Unit03 Connected Speaking Layer2 Pronoun Coverage FullFix</title>
<style>
@page{size:A4 landscape;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#111}
.page{width:297mm;height:210mm;padding:8mm 10mm 7mm;page-break-after:always;display:flex;flex-direction:column}
.header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid #777;padding-bottom:2.5mm;margin-bottom:4mm}
.title{font-size:15pt;font-weight:700}.subtitle{font-size:8.5pt;color:#555;margin-top:1mm}.page-no{font-size:9pt}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:5mm;flex:1;align-content:start}
.card{border:1px solid #aaa;border-radius:4px;padding:3.2mm;break-inside:avoid}.card-head{display:flex;justify-content:space-between;margin-bottom:2mm}
.card-title{font-size:11pt;font-weight:700}.card-meta,.rounds{font-size:7.5pt;color:#666}.row{display:grid;grid-template-columns:7mm 1fr 34mm;gap:1.5mm;align-items:center;border-top:1px solid #eee;padding:1.5mm 0}
.num{font-size:8pt;color:#666}.sentence{font-size:10pt;line-height:1.2}.speaker{font-weight:700}.checks{font-size:7.5pt;white-space:nowrap}
.check{display:inline-block;width:3mm;height:3mm;border:1px solid #777;margin:0 1.5mm .2mm .8mm;vertical-align:middle}
.footer{display:flex;justify-content:space-between;border-top:1px solid #aaa;padding-top:2mm;margin-top:3mm;font-size:7.5pt;color:#666}
</style></head><body>""" + "".join(pages) + "</body></html>"


def materialize(
    *,
    base_layer2_path: Path,
    atomic_pool_path: Path,
    output_dir: Path,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    payload, qa = build_supplement(
        base_layer2_path=base_layer2_path,
        atomic_pool_path=atomic_pool_path,
        contract_path=contract_path,
    )
    contract = _load(contract_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=contract["level_scope"],
        source_bindings={
            "base_layer2_data_sha256": payload["base_attestation"]["layer2_data_sha256"],
            "atomic_pool_sha256": payload["base_attestation"]["atomic_pool_sha256"],
            "unit03_production_acceptance_manifest": "ulga/contracts/a1fs_v1_unit03_production_acceptance_manifest.json",
        },
    )
    approved = policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[{
            "validator_id": qa["validator_id"],
            "status": "PASS",
            "receipt_sha256": qa["receipt_sha256"],
        }],
        decision_ref="U03_LAYER2_C_I_PRONOUN_COVERAGE_FULLFIX_DETERMINISTIC_ADMISSION",
        producer_id=TASK_ID,
    )
    projection_payload = {
        "skill": "SPEAKING",
        "prompt": "Read, shadow, and speak the connected C-I cards. Keep speaker and object reference clear.",
        "response_mode": "CONNECTED_ORAL_PRACTICE",
        "support_level": "GUIDED_TO_REDUCED_SUPPORT",
        "initiative_level": "CONTROLLED_PRACTICE",
        "scoring_contract": {"mode": "PRACTICE_ONLY_NO_MASTERY", "target": "SUBJECT_PRONOUN_REFERENCE"},
        "evidence_level": "PRACTICE_EVIDENCE_ONLY",
        "source_bindings": approved["source_bindings"],
        "content_identity": {
            "unit_id": UNIT_ID,
            "task_id": TASK_ID,
            "supplement": "LAYER2_C_I_YOU_WE_IT_APPEND_ONLY",
        },
        "supplement_records": payload["supplement_records"],
    }
    projection = policy_artifact.build_four_skill_projection(
        approved,
        skill="SPEAKING",
        projection_payload=projection_payload,
        producer_id=TASK_ID,
    )
    paths = {
        "candidate": output_dir / "Unit03_Connected_Speaking_C-I_PronounCoverageFullFix_Candidate.json",
        "approved": output_dir / "Unit03_Connected_Speaking_C-I_PronounCoverageFullFix_Approved.json",
        "projection": output_dir / "Unit03_Connected_Speaking_C-I_PronounCoverageFullFix_Speaking.json",
        "qa": output_dir / "Unit03_Connected_Speaking_C-I_PronounCoverageFullFix_QA.json",
        "html": output_dir / "Unit03_Connected_Speaking_C-I_PronounCoverageFullFix_A4.html",
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
    result = materialize(
        base_layer2_path=args.base_layer2_data,
        atomic_pool_path=args.atomic_pool,
        output_dir=args.output_dir,
        contract_path=args.contract,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
