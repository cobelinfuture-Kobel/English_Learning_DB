from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_validation.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_raz_level_discovery as discovery  # noqa: E402
from ulga.query import raz_reusable_content_seed_query_layer as query_layer  # noqa: E402


def fail(message: str) -> bool:
    print(f"FAIL: {message}")
    return False


def main() -> int:
    print("Validating RAZ Level Discovery...")
    records, summary = discovery.build_and_write_artifacts()

    for record in records:
        level = record.get("level")
        normalized = record.get("normalized_level")
        status = record.get("status")
        evidence = record.get("source_evidence", {})

        if normalized is None:
            if status != discovery.INVALID_FORMAT:
                return 1 if fail(f"{level}: invalid level must use status {discovery.INVALID_FORMAT}") is False else 1
        elif discovery.is_valid_level_code(normalized) is False:
            return 1 if fail(f"{level}: normalized level must be a valid single-letter code") is False else 1

        if record.get("authority_status") != "candidate_only":
            return 1 if fail(f"{level}: authority_status must remain candidate_only") is False else 1
        if record.get("promotion_allowed") is not False:
            return 1 if fail(f"{level}: promotion_allowed must remain false") is False else 1

        if status == discovery.READY_FOR_SENTENCE_PIPELINE and evidence.get("sentence_candidate_count", 0) <= 0:
            return 1 if fail(f"{level}: ready sentence level missing sentence candidates") is False else 1
        if status == discovery.READY_FOR_PAGE_UNIT_PIPELINE and (
            evidence.get("sentence_candidate_count", 0) <= 0 or evidence.get("page_unit_count", 0) <= 0
        ):
            return 1 if fail(f"{level}: ready page-unit level missing required evidence") is False else 1
        if status == discovery.READY_FOR_REUSE_UNIT_PIPELINE and (
            evidence.get("sentence_candidate_count", 0) <= 0
            or evidence.get("page_unit_count", 0) <= 0
            or evidence.get("reuse_unit_count", 0) <= 0
        ):
            return 1 if fail(f"{level}: ready reuse-unit level missing required evidence") is False else 1

        if status in {discovery.SKIPPED_NO_DATA, discovery.MISSING_REQUIRED_INPUT, discovery.INVALID_FORMAT} and not record.get("skip_reasons"):
            return 1 if fail(f"{level}: skipped or invalid level must provide skip reasons") is False else 1

        if evidence.get("timeline_json_count", 0) == 0 and "timeline_json" not in record.get("missing_artifacts", []):
            return 1 if fail(f"{level}: missing timeline must be reported") is False else 1

    counted_total = (
        summary.get("ready_level_count", 0)
        + summary.get("skipped_level_count", 0)
        + summary.get("partial_level_count", 0)
        + summary.get("invalid_level_count", 0)
        + summary.get("missing_required_input_count", 0)
    )
    if counted_total != summary.get("total_detected_levels"):
        return 1 if fail("summary counts do not add up to total_detected_levels") is False else 1

    if "C/D/E/F" in Path(discovery.__file__).read_text(encoding="utf-8"):
        return 1 if fail("new discovery module must not contain C/D/E/F-only hardcoding") is False else 1

    for card in query_layer.load_seed_cards(include_text=False):
        if card.get("qa", {}).get("authority_status") != "candidate_only":
            return 1 if fail(f"seed card {card.get('seed_id')} is not candidate_only") is False else 1

    validation_report = {
        "status": "PASS",
        "inventory_path": str(discovery.INVENTORY_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        "summary_path": str(discovery.SUMMARY_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        "total_detected_levels": summary["total_detected_levels"],
        "levels_by_status": summary["levels_by_status"],
    }
    VALIDATION_REPORT_PATH.write_text(json.dumps(validation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: RAZ Level Discovery validator succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
