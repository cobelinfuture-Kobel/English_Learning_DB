import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators import validate_reading_practice_items as item_validator

ITEMS_PATH = BASE_DIR / "ulga" / "graph" / "reading_practice_items.json"
ITEMS_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_practice_items_summary.json"
PACKAGE_PATH = BASE_DIR / "ulga" / "graph" / "reading_practice_package.json"
PACKAGE_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_practice_package_summary.json"

PACKAGE_SCHEMA_VERSION = "READING_PRACTICE_PACKAGE_CANDIDATE_V1"
PACKAGE_SUMMARY_SCHEMA_VERSION = "READING_PRACTICE_PACKAGE_SUMMARY_V1"
BUILDER_TASK = "RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation"

APPROVED_QUESTION_TYPES = {
    "literal_who",
    "literal_what",
    "literal_where",
    "true_false",
    "sentence_ordering",
    "cloze_vocabulary",
}


def empty_items_payload():
    return {
        "schema_version": "READING_PRACTICE_ITEMS_CANDIDATE_OUTPUT_V1",
        "item_schema_version": "READING_PRACTICE_ITEM_V1",
        "builder_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
        "source_policy": {
            "offline_static_only": True,
            "generated_source_content_allowed": False,
            "authority_promotion": False,
            "candidate_only_preserved": True,
            "learner_facing": False,
        },
        "generation_policy": {
            "approved_question_types": sorted(APPROVED_QUESTION_TYPES),
            "validator_status_emitted": "not_run",
            "max_items_per_question_type": 0,
        },
        "items": [],
        "summary": {
            "schema_version": "READING_PRACTICE_ITEMS_CANDIDATE_SUMMARY_V1",
            "status": "PASS_WITH_WARNINGS",
            "builder_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
            "total_items": 0,
            "warnings": ["missing_or_empty_s17_generated_items"],
        },
    }


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def item_is_packagable(item):
    if not isinstance(item, dict):
        return False
    if item.get("question_type") not in APPROVED_QUESTION_TYPES:
        return False
    lifecycle = item.get("lifecycle") if isinstance(item.get("lifecycle"), dict) else {}
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    prompt = item.get("prompt") if isinstance(item.get("prompt"), dict) else {}
    answer_model = item.get("answer_model") if isinstance(item.get("answer_model"), dict) else {}
    if lifecycle.get("authority_status") != "candidate_only":
        return False
    if lifecycle.get("promotion_status") != "not_promoted":
        return False
    if lifecycle.get("learner_facing") is not False:
        return False
    if source.get("generated_content") is not False:
        return False
    if source.get("promotion_status") != "not_promoted":
        return False
    if not evidence.get("evidence_text") or not evidence.get("evidence_sentences"):
        return False
    if not prompt.get("stem") or not prompt.get("instructions"):
        return False
    if not answer_model.get("answer_type"):
        return False
    return True


def package_item(item, sequence_number):
    return {
        "package_item_id": f"READING_PACKAGE_ITEM_{sequence_number:06d}",
        "item_id": item["item_id"],
        "question_type": item["question_type"],
        "skill": item["skill"],
        "level": item["level"],
        "source": item["source"],
        "evidence": item["evidence"],
        "prompt": item["prompt"],
        "answer_model": item["answer_model"],
        "tags": item.get("tags", {}),
        "validation": item.get("validation", {}),
        "lifecycle": item["lifecycle"],
    }


def build_summary(package_items, validation_result, warnings, max_items):
    by_question_type = Counter(item["question_type"] for item in package_items)
    by_source_level = Counter(item["source"].get("source_level") for item in package_items)
    status = "PASS_WITH_WARNINGS" if warnings else "PASS"
    if validation_result.get("status") == "FAIL":
        status = "FAIL"
    return {
        "schema_version": PACKAGE_SUMMARY_SCHEMA_VERSION,
        "status": status,
        "builder_task": BUILDER_TASK,
        "total_package_items": len(package_items),
        "max_items": max_items,
        "by_question_type": dict(sorted(by_question_type.items())),
        "by_source_level": dict(sorted(by_source_level.items())),
        "candidate_only_count": sum(1 for item in package_items if item["lifecycle"].get("authority_status") == "candidate_only"),
        "promoted_count": sum(1 for item in package_items if item["lifecycle"].get("promotion_status") == "promoted"),
        "learner_facing_count": sum(1 for item in package_items if item["lifecycle"].get("learner_facing") is True),
        "validation_gate_status": validation_result.get("status"),
        "warnings": sorted(dict.fromkeys(warnings)),
    }


def build_package(items_payload=None, items_summary=None, max_items=20, write_outputs=True, output_path=PACKAGE_PATH, summary_path=PACKAGE_SUMMARY_PATH):
    if items_payload is None:
        items_payload = read_json(ITEMS_PATH) if ITEMS_PATH.exists() else empty_items_payload()
    if items_summary is None and ITEMS_SUMMARY_PATH.exists():
        items_summary = read_json(ITEMS_SUMMARY_PATH)
    if items_summary is None and isinstance(items_payload, dict):
        items_summary = items_payload.get("summary")

    validation_result = item_validator.validate_payload(items_payload, items_summary)
    warnings = []
    package_items = []

    if validation_result.get("status") == "FAIL":
        warnings.append("validation_gate_failed_no_items_packaged")
    else:
        for item in items_payload.get("items", []) if isinstance(items_payload, dict) else []:
            if item_is_packagable(item):
                package_items.append(package_item(item, len(package_items) + 1))
            if len(package_items) >= max_items:
                break

    if not package_items:
        warnings.append("no_items_packaged")

    summary = build_summary(package_items, validation_result, warnings, max_items)
    payload = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "builder_task": BUILDER_TASK,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_policy": {
            "candidate_only_preserved": True,
            "authority_promotion": False,
            "learner_facing": False,
            "runtime_integration": False,
        },
        "validation_gate": validation_result,
        "package": {
            "package_id": "READING_PRACTICE_PACKAGE_S19_000001",
            "status": "candidate_package_generated" if package_items else "empty_candidate_package",
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "learner_facing": False,
            "item_count": len(package_items),
            "items": package_items,
            "answer_key": [
                {
                    "item_id": item["item_id"],
                    "question_type": item["question_type"],
                    "answer_model": item["answer_model"],
                }
                for item in package_items
            ],
        },
        "summary": summary,
    }

    if write_outputs:
        write_json(output_path, payload)
        write_json(summary_path, summary)
    return payload


def parse_args():
    parser = argparse.ArgumentParser(description="Build candidate Reading practice package from S17/S18 candidate items.")
    parser.add_argument("--items", default=str(ITEMS_PATH))
    parser.add_argument("--items-summary", default=str(ITEMS_SUMMARY_PATH))
    parser.add_argument("--output", default=str(PACKAGE_PATH))
    parser.add_argument("--summary", default=str(PACKAGE_SUMMARY_PATH))
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    items_path = Path(args.items)
    summary_path = Path(args.items_summary)
    items_payload = read_json(items_path) if items_path.exists() else empty_items_payload()
    items_summary = read_json(summary_path) if summary_path.exists() else items_payload.get("summary")
    payload = build_package(
        items_payload=items_payload,
        items_summary=items_summary,
        max_items=max(0, args.max_items),
        write_outputs=not args.no_write,
        output_path=Path(args.output),
        summary_path=Path(args.summary),
    )
    print(f"Status: {payload['summary']['status']}")
    print(f"Package items: {payload['summary']['total_package_items']}")
    return 0 if payload["summary"]["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
