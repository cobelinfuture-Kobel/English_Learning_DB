#!/usr/bin/env python3
"""Apply the final focused R8 EXACT_OPTION production and regression fix.

Temporary operator script. It edits only the production population builder and the
existing focused regression tests. It must be removed before merge.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_TEST = ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py"
PRODUCTION = ROOT / "ulga/builders/build_a1fs_v1_r3r4_authority_reviewed_production_population.py"
PRODUCTION_TEST = ROOT / "tests/ulga/test_a1fs_v1_r3r4_authority_reviewed_production_population.py"


def patch_fixture_helper() -> None:
    text = RUNNER_TEST.read_text(encoding="utf-8")
    pattern = re.compile(
        r"def _prepare_hash_bound_source_options_case\(.*?\n\ndef _expand_source_bank_to_formal_m08_size\(",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("exact_option_fixture_helper_not_found")

    replacement = r'''def _prepare_hash_bound_source_options_case(
    fixture: dict,
    *,
    include_source_options: bool,
) -> int:
    fixture["current_bank_path"].unlink()
    fixture["current_supply_path"].unlink()

    graph = json.loads(fixture["graph_path"].read_text(encoding="utf-8"))
    graph["a2_lock_contract"]["state"] = "LOCKED_BY_DESIGN"
    fixture["graph_path"].write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    bank = json.loads(fixture["source_bank_path"].read_text(encoding="utf-8"))
    for row in bank["items"]:
        scoring = row.get("private_scoring_contract", {})
        if scoring.get("scoring_mode") == "FEATURE_RUBRIC":
            learner = row.setdefault("learner_contract", {})
            learner["prompt"] = "Write for the visible school situation."
            learner["response_mode"] = "short_text"
            learner["context"] = {"source_context": "A visible fixture context."}

    target = bank["items"][0]
    target_item_id = str(target["item_id"])
    previous_scoring = target.get("private_scoring_contract", {})
    accepted = list(previous_scoring.get("accepted_texts", [])) or ["answer 1"]
    exact_contract = {
        "scoring_mode": "EXACT_OPTION",
        "response_type": "string",
        "accepted_texts": accepted,
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }
    target["private_scoring_contract"] = deepcopy(exact_contract)
    learner = target.setdefault("learner_contract", {})
    learner["prompt"] = "Choose the visible answer."
    learner["response_mode"] = "select_one"
    learner.pop("context", None)
    if include_source_options:
        learner["options"] = accepted + ["Visible distractor 1"]
    else:
        learner.pop("options", None)

    bank["items_sha256"] = m08.sha256_value(bank["items"])
    fixture["source_bank_path"].write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bank_hash = m08.sha256_value(bank)

    registry_path = fixture["resolved_root"] / "cumulative_attempt_registry.private.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["session_bank_sha256"] = bank_hash
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    ledger_path = fixture["resolved_root"] / "cumulative_progress_ledger.private.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["session_bank_sha256"] = bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    for entry in ledger["entries"]:
        if entry.get("item_id") == target_item_id:
            entry["scoring_mode"] = "EXACT_OPTION"
    ledger["entries_sha256"] = m08.sha256_value(ledger["entries"])
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    consumer = json.loads(fixture["consumer_path"].read_text(encoding="utf-8"))
    consumer["source_graph_sha256"] = runner.legacy.file_sha(fixture["graph_path"])
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["domain_hint"] = "school classroom lesson teacher student"
        if payload.get("m12_item_id") == target_item_id:
            payload["private_scoring_contract"] = deepcopy(exact_contract)
            for key in ("options", "choices", "answer_options", "answer_choices"):
                payload.pop(key, None)
        if isinstance(payload.get("m12_item_id"), str):
            payload["m12_session_bank_sha256"] = bank_hash
        asset["content_digest"] = runner.population.digest(payload)
    fixture["consumer_path"].write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 1


def _expand_source_bank_to_formal_m08_size('''
    text = text[: match.start()] + replacement + text[match.end() :]
    RUNNER_TEST.write_text(text, encoding="utf-8")


def patch_production_contract() -> None:
    text = PRODUCTION.read_text(encoding="utf-8")
    old = '        scoring = {"scoring_mode": mode, "response_type": "string", "accepted_texts": accepted, "human_review_fallback": False}\n'
    new = '''        scoring = {
            "scoring_mode": mode,
            "response_type": "string",
            "accepted_texts": accepted,
            "case_insensitive": bool(derived.get("case_insensitive", True)),
            "punctuation_tolerance": bool(derived.get("punctuation_tolerance", True)),
            "human_review_fallback": False,
        }
'''
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"exact_option_scoring_contract_match_count:{text.count(old)}")
    PRODUCTION.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_production_regression() -> None:
    text = PRODUCTION_TEST.read_text(encoding="utf-8")
    old = '''    bank = json.loads((output / population.BANK_OUTPUT).read_text())
    assert bank["item_count"] == 2
    population.safe_scan(report)
'''
    new = '''    bank = json.loads((output / population.BANK_OUTPUT).read_text())
    assert bank["item_count"] == 2
    for item in bank["items"]:
        scoring = item["private_scoring_contract"]
        assert scoring["scoring_mode"] == "EXACT_OPTION"
        assert scoring["case_insensitive"] is True
        assert scoring["punctuation_tolerance"] is True
    population.safe_scan(report)
'''
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"production_regression_anchor_match_count:{text.count(old)}")
    PRODUCTION_TEST.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    patch_fixture_helper()
    patch_production_contract()
    patch_production_regression()


if __name__ == "__main__":
    main()
