#!/usr/bin/env python3
"""Apply the focused R8 hash-bound EXACT_OPTION compatibility patch.

Temporary operator script. It only edits the existing local reconciliation runner
and its focused regression test. It must be removed before merge.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "ulga/builders/run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local.py"
TEST = ROOT / "tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}:expected_one_match:actual={count}")
    return text.replace(old, new, 1)


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    pattern = re.compile(
        r"def _stage_feature_context_compatibility\(.*?\n\ndef _discover_current\(",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("runner_compatibility_function_not_found")

    replacement = '''def _stage_feature_context_compatibility(
    chains: list[dict[str, Path]],
    *,
    staging_root: Path,
) -> tuple[list[dict[str, Path]], dict[str, int]]:
    """Reuse only hash-bound M08 learner-visible context/options in a staged consumer."""
    staging_root.mkdir(parents=True, exist_ok=True)
    staged: list[dict[str, Path]] = []
    counts: Counter[str] = Counter()

    for index, chain in enumerate(chains, start=1):
        bank = _read(chain["source_bank_path"])
        consumer = _read(chain["consumer_path"])
        if bank is None or consumer is None:
            raise LocalRunnerError("learner_contract_compatibility_source_unreadable")

        bank_hash = m08.sha256_value(bank)
        bank_items = {
            str(row.get("item_id")): row
            for row in bank.get("items", [])
            if isinstance(row, Mapping) and isinstance(row.get("item_id"), str)
        }
        projected = deepcopy(consumer)
        feature_join_count = 0
        context_backfill_count = 0
        source_context_missing_count = 0
        existing_context_preserved_count = 0
        context_conflict_count = 0
        option_join_count = 0
        option_backfill_count = 0
        source_options_missing_count = 0
        existing_options_preserved_count = 0
        options_conflict_count = 0
        option_scoring_mismatch_count = 0

        for asset in projected.get("asset_records", []):
            if not isinstance(asset, Mapping):
                continue
            payload = asset.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if payload.get("m12_session_bank_sha256") != bank_hash:
                continue
            item_id = payload.get("m12_item_id")
            if not isinstance(item_id, str):
                continue
            source_item = bank_items.get(item_id)
            if not isinstance(source_item, Mapping):
                continue
            try:
                derived = m6.derive_contract(asset)
            except (KeyError, TypeError, ValueError):
                continue

            source_contract = source_item.get("learner_contract")
            source_contract = source_contract if isinstance(source_contract, Mapping) else {}
            mode = str(derived.get("scoring_mode") or "")

            if mode == "FEATURE_RUBRIC":
                feature_join_count += 1
                source_context = source_contract.get("context")
                existing_context = population._context(payload)
                if existing_context:
                    existing_context_preserved_count += 1
                    if _nonempty(source_context) and existing_context != source_context:
                        context_conflict_count += 1
                    continue
                if not _nonempty(source_context):
                    source_context_missing_count += 1
                    continue
                payload["context"] = deepcopy(source_context)
                payload["compatibility_context_binding"] = {
                    "mode": "M08_HASH_BOUND_LEARNER_CONTEXT_REUSE",
                    "source_session_bank_sha256": bank_hash,
                    "source_item_id": item_id,
                    "source_context_sha256": m08.sha256_value(source_context),
                    "canonical_m2_modified": False,
                }
                asset["content_digest"] = population.digest(payload)
                context_backfill_count += 1
                continue

            if mode != "EXACT_OPTION":
                continue

            option_join_count += 1
            raw_source_options = source_contract.get("options")
            source_options = (
                [row.strip() for row in raw_source_options]
                if isinstance(raw_source_options, list)
                and all(isinstance(row, str) and row.strip() for row in raw_source_options)
                else []
            )
            source_options_valid = (
                len(source_options) >= 2
                and len(source_options) == len(set(source_options))
                and source_contract.get("response_mode") == "select_one"
            )
            accepted = [
                row.strip()
                for row in derived.get("accepted_texts", [])
                if isinstance(row, str) and row.strip()
            ]
            existing_options = population._options(payload)

            if existing_options:
                existing_options_preserved_count += 1
                if source_options_valid and existing_options != source_options:
                    options_conflict_count += 1
                if not accepted or any(answer not in existing_options for answer in accepted):
                    option_scoring_mismatch_count += 1
                continue

            if not source_options_valid:
                source_options_missing_count += 1
                continue
            if not accepted or any(answer not in source_options for answer in accepted):
                option_scoring_mismatch_count += 1
                continue

            payload["options"] = deepcopy(source_options)
            payload["compatibility_options_binding"] = {
                "mode": "M08_HASH_BOUND_LEARNER_OPTIONS_REUSE",
                "source_session_bank_sha256": bank_hash,
                "source_item_id": item_id,
                "source_options_sha256": m08.sha256_value(source_options),
                "canonical_m2_modified": False,
            }
            asset["content_digest"] = population.digest(payload)
            option_backfill_count += 1

        if context_conflict_count:
            raise LocalRunnerError("feature_context_source_m2_conflict")
        if options_conflict_count:
            raise LocalRunnerError("exact_option_source_m2_conflict")
        if option_scoring_mismatch_count:
            raise LocalRunnerError("exact_option_source_scoring_mismatch")

        projected["compatibility_projection"] = {
            "mode": "M08_HASH_BOUND_LEARNER_CONTRACT_BACKFILL",
            "source_consumer_sha256": legacy.file_sha(chain["consumer_path"]),
            "source_session_bank_sha256": bank_hash,
            "feature_rubric_exact_join_count": feature_join_count,
            "context_backfill_count": context_backfill_count,
            "source_context_missing_count": source_context_missing_count,
            "existing_context_preserved_count": existing_context_preserved_count,
            "exact_option_exact_join_count": option_join_count,
            "option_backfill_count": option_backfill_count,
            "source_options_missing_count": source_options_missing_count,
            "existing_options_preserved_count": existing_options_preserved_count,
            "canonical_m2_modified": False,
            "new_context_created": False,
            "new_options_created": False,
        }
        staged_path = staging_root / f"compatibility_consumer_{index:03d}.private.json"
        _write(staged_path, projected)
        staged_chain = dict(chain)
        staged_chain["consumer_path"] = staged_path
        staged.append(staged_chain)

        counts["compatibility_consumer_count"] += 1
        counts["compatibility_feature_rubric_exact_join_count"] += feature_join_count
        counts["compatibility_context_backfill_count"] += context_backfill_count
        counts["compatibility_source_context_missing_count"] += source_context_missing_count
        counts["compatibility_existing_context_preserved_count"] += existing_context_preserved_count
        counts["compatibility_context_conflict_count"] += context_conflict_count
        counts["compatibility_exact_option_exact_join_count"] += option_join_count
        counts["compatibility_option_backfill_count"] += option_backfill_count
        counts["compatibility_source_options_missing_count"] += source_options_missing_count
        counts["compatibility_existing_options_preserved_count"] += existing_options_preserved_count
        counts["compatibility_options_conflict_count"] += options_conflict_count
        counts["compatibility_option_scoring_mismatch_count"] += option_scoring_mismatch_count

    for key in (
        "compatibility_consumer_count",
        "compatibility_feature_rubric_exact_join_count",
        "compatibility_context_backfill_count",
        "compatibility_source_context_missing_count",
        "compatibility_existing_context_preserved_count",
        "compatibility_context_conflict_count",
        "compatibility_exact_option_exact_join_count",
        "compatibility_option_backfill_count",
        "compatibility_source_options_missing_count",
        "compatibility_existing_options_preserved_count",
        "compatibility_options_conflict_count",
        "compatibility_option_scoring_mismatch_count",
    ):
        counts.setdefault(key, 0)
    return staged, dict(counts)


def _discover_current('''
    text = text[: match.start()] + replacement + text[match.end() :]

    text = text.replace(
        '"new_context_created": False,\n            "canonical_m2_modified": False,',
        '"new_context_created": False,\n            "new_options_created": False,\n            "canonical_m2_modified": False,',
    )
    text = text.replace(
        '"new_evidence_created": False,\n                "mastery_claimed": False,',
        '"new_evidence_created": False,\n                "new_context_created": False,\n                "new_options_created": False,\n                "canonical_m2_modified": False,\n                "mastery_claimed": False,',
    )
    RUNNER.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    anchor = '\n\ndef _expand_source_bank_to_formal_m08_size(fixture: dict) -> None:\n'
    if anchor not in text:
        raise RuntimeError("test_helper_anchor_not_found")
    helper = r'''

def _prepare_hash_bound_source_options_case(
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
    exact_count = 0
    for row in bank["items"]:
        scoring = row.get("private_scoring_contract", {})
        if scoring.get("scoring_mode") != "EXACT_OPTION":
            continue
        exact_count += 1
        learner = row.setdefault("learner_contract", {})
        learner["response_mode"] = "select_one"
        accepted = list(scoring.get("accepted_texts", []))
        if include_source_options:
            learner["options"] = accepted + [f"Visible distractor {exact_count}"]
        else:
            learner.pop("options", None)
    assert exact_count > 0
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
    ledger_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    consumer = json.loads(fixture["consumer_path"].read_text(encoding="utf-8"))
    consumer["source_graph_sha256"] = runner.legacy.file_sha(fixture["graph_path"])
    for asset in consumer["asset_records"]:
        payload = asset["payload"]
        payload["domain_hint"] = "school classroom lesson teacher student"
        try:
            derived = runner.m6.derive_contract(asset)
        except (KeyError, TypeError, ValueError):
            derived = {}
        if derived.get("scoring_mode") == "EXACT_OPTION":
            for key in ("options", "choices", "answer_options", "answer_choices"):
                payload.pop(key, None)
        if isinstance(payload.get("m12_item_id"), str):
            payload["m12_session_bank_sha256"] = bank_hash
    fixture["consumer_path"].write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return exact_count
'''
    text = text.replace(anchor, helper + anchor, 1)

    test_anchor = '\n\ndef test_runner_blocks_multiple_distinct_exact_production_identities(fixture: dict) -> None:\n'
    if test_anchor not in text:
        raise RuntimeError("test_case_anchor_not_found")
    cases = r'''

def test_runner_backfills_hash_bound_m08_options_without_mutating_canonical_m2(fixture: dict) -> None:
    exact_count = _prepare_hash_bound_source_options_case(
        fixture,
        include_source_options=True,
    )
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS, report
    counts = report["discovery_counts"]
    assert counts["compatibility_exact_option_exact_join_count"] == exact_count
    assert counts["compatibility_option_backfill_count"] == exact_count
    assert counts["compatibility_source_options_missing_count"] == 0
    assert counts["compatibility_options_conflict_count"] == 0
    assert counts["compatibility_option_scoring_mismatch_count"] == 0
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert "Visible distractor" not in json.dumps(report, ensure_ascii=False)


def test_runner_does_not_invent_missing_exact_option_choices(fixture: dict) -> None:
    exact_count = _prepare_hash_bound_source_options_case(
        fixture,
        include_source_options=False,
    )
    original_consumer = fixture["consumer_path"].read_bytes()
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.BLOCKED
    counts = report["discovery_counts"]
    assert counts["compatibility_exact_option_exact_join_count"] == exact_count
    assert counts["compatibility_option_backfill_count"] == 0
    assert counts["compatibility_source_options_missing_count"] == exact_count
    assert fixture["consumer_path"].read_bytes() == original_consumer
    assert report["claim_boundaries"]["new_options_created"] is False
    assert report["claim_boundaries"]["canonical_m2_modified"] is False
'''
    text = text.replace(test_anchor, cases + test_anchor, 1)
    TEST.write_text(text, encoding="utf-8")


def main() -> None:
    patch_runner()
    patch_test()


if __name__ == "__main__":
    main()
