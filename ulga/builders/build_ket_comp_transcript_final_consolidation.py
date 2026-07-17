from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

TASK_ID = "KET_COMP_TRANSCRIPT_FINAL_CONSOLIDATION_V1"
SOURCE_ROLE = "third_party_teacher_delivery_reference"
AUTHORITY = "non_authoritative"
PARSER_VERSION = "ket_comp_transcript_parser_v1.1.0"
FILE_NAMES = {
    "registry": "transcript_source_registry.json",
    "content": "transcript_content_units.jsonl",
    "reuse": "transcript_reuse_candidates.json",
    "admission": "transcript_admission_decisions.json",
}


def _json_dump(value: Any, *, compact: bool = False) -> str:
    if compact:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def load_manifest(path: Path) -> dict[str, Any]:
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("schema") != "ket.comp.source_manifest.index.v1":
        raise ValueError("unsupported source manifest index schema")
    base = path.parent
    batch_value = json.loads((base / index["batch_file"]).read_text(encoding="utf-8"))
    if batch_value.get("schema") != "ket.comp.batch_manifest.v1":
        raise ValueError("unsupported batch manifest schema")
    sources: list[list[Any]] = []
    for name in index["source_parts"]:
        part = json.loads((base / name).read_text(encoding="utf-8"))
        if part.get("schema") != "ket.comp.source_manifest.part.v1":
            raise ValueError(f"unsupported source manifest part: {name}")
        sources.extend(part["sources"])
    return {"schema": "ket.comp.source_manifest.v1", "expected": index["expected"], "batches": batch_value["batches"], "sources": sources}


def _source_record(row: list[Any]) -> dict[str, Any]:
    (
        number, filename, textbook_page, unit_id, lesson_role,
        size_bytes, character_count, line_count, source_sha256,
        batch_id, batch_filename, batch_sha256, section_sha256,
        section_start, section_end, title, content_roles, evidence_items, risk_flags,
    ) = row
    transcript_id = f"P{number:03d}"
    return {
        "transcript_id": transcript_id,
        "source_filename": filename,
        "source_transcript_number": number,
        "textbook_page": textbook_page,
        "unit_id": unit_id,
        "lesson_role": lesson_role,
        "source_role": SOURCE_ROLE,
        "authority_status": AUTHORITY,
        "canonical_promotion_allowed": False,
        "instructional_pattern_reuse_allowed": True,
        "read_status": "complete",
        "extraction_status": "content_extracted",
        "source_size_bytes": size_bytes,
        "source_character_count": character_count,
        "source_line_count": line_count,
        "source_sha256": source_sha256,
        "parser_version": PARSER_VERSION,
        "processing_batch_id": batch_id,
        "processing_batch_filename": batch_filename,
        "processing_batch_sha256": batch_sha256,
        "processing_batch_section_sha256": section_sha256,
        "batch_section_start_line": section_start,
        "batch_section_end_line": section_end,
        "content_unit_id": f"KET_COMP_CU_{transcript_id}_LESSON_BUNDLE",
        "reuse_candidate_id": f"KET_COMP_REUSE_{transcript_id}_DELIVERY_PATTERN",
        "admission_decision_id": f"KET_COMP_ADMISSION_{transcript_id}",
        "title": title,
        "content_roles": content_roles,
        "evidence_items": evidence_items,
        "risk_flags": risk_flags,
    }


def _target_systems(roles: list[str]) -> list[str]:
    mapping = {
        "grammar": "grammar_candidate_layer",
        "vocabulary": "vocabulary_candidate_layer",
        "reading": "ket_reading",
        "listening": "ket_listening",
        "speaking": "ket_speaking",
        "writing": "ket_writing",
        "pronunciation": "pronunciation_candidate_layer",
        "teacher_delivery": "teacher_delivery",
        "review": "review_mastery_layer",
        "error_taxonomy": "error_diagnosis",
        "remediation": "remediation",
    }
    targets = [mapping[x] for x in roles if x in mapping]
    return sorted(set(targets + ["lesson_planner", "teacher_delivery"]))


def build(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    sources = [_source_record(row) for row in manifest["sources"]]
    sources.sort(key=lambda row: row["source_transcript_number"])
    expected_start, expected_end = manifest["expected"]

    registry_sources = []
    content_units = []
    reuse_candidates = []
    admission_decisions = []
    for source in sources:
        registry_sources.append({key: value for key, value in source.items() if key not in {
            "title", "content_roles", "evidence_items", "risk_flags"
        }})
        transcript_id = source["transcript_id"]
        content_unit_id = source["content_unit_id"]
        content_units.append({
            "content_unit_id": content_unit_id,
            "transcript_id": transcript_id,
            "textbook_page": source["textbook_page"],
            "unit_id": source["unit_id"],
            "lesson_role": source["lesson_role"],
            "content_type": "lesson_content_bundle",
            "title": source["title"],
            "content_roles": source["content_roles"],
            "evidence_items": source["evidence_items"],
            "risk_flags": source["risk_flags"],
            "source_span": {
                "start_line": 1,
                "end_line": source["source_line_count"],
                "evidence_sha256": source["source_sha256"],
                "coverage_mode": "full_transcript_read",
            },
            "batch_evidence": {
                "batch_id": source["processing_batch_id"],
                "batch_filename": source["processing_batch_filename"],
                "start_line": source["batch_section_start_line"],
                "end_line": source["batch_section_end_line"],
                "section_sha256": source["processing_batch_section_sha256"],
            },
            "authority_status": AUTHORITY,
            "canonical_promotion_allowed": False,
        })
        target_systems = _target_systems(source["content_roles"])
        reuse_candidates.append({
            "reuse_candidate_id": source["reuse_candidate_id"],
            "source_content_unit_ids": [content_unit_id],
            "transcript_id": transcript_id,
            "candidate_type": "instructional_pattern_bundle",
            "content_roles": source["content_roles"],
            "target_systems": target_systems,
            "reuse_status": "approved_with_constraints",
            "constraints": [
                "non_authoritative_source",
                "canonical_promotion_forbidden",
                "audio_image_and_exam_claims_require_independent_verification",
            ] + (["risk_flags_present"] if source["risk_flags"] else []),
        })
        admission_decisions.append({
            "admission_id": source["admission_decision_id"],
            "subject_type": "content_unit",
            "subject_id": content_unit_id,
            "transcript_id": transcript_id,
            "decisions": {
                "teacher_delivery": "approved",
                "lesson_planner": "approved_with_constraints",
                "reuse_candidate_layer": "approved_with_constraints",
                "canonical_grammar_authority": "denied",
                "canonical_vocabulary_authority": "denied",
                "external_fact_layer": "denied_until_verified",
                "assessment_contract": "denied_until_verified",
                "human_pilot": "not_ready",
            },
            "requirements": [
                "retain_source_lineage",
                "map_language_items_to_canonical_authorities",
                "validate_audio_image_answer_keys_and_current_exam_format",
            ],
        })

    admission_decisions.extend([
        {
            "admission_id": "KET_COMP_ADMISSION_FALSE_CORRECTION_HOPE_WILL",
            "subject_type": "source_claim",
            "subject_id": "P093_FALSE_HOPE_WILL_CORRECTION",
            "transcript_id": "P093",
            "decisions": {"teacher_delivery": "rejected", "error_taxonomy": "approved", "canonical_grammar_authority": "denied"},
            "reason": "The source incorrectly labels 'I hope we will have...' as ungrammatical.",
        },
        {
            "admission_id": "KET_COMP_ADMISSION_KET_ZHONGKAO_EQUIVALENCE",
            "subject_type": "source_claim",
            "subject_id": "P102_KET_ZHONGKAO_EQUIVALENCE",
            "transcript_id": "P102",
            "decisions": {"reference_only": "approved", "exam_equivalence_layer": "denied", "canonical_knowledge": "denied"},
            "reason": "Different constructs, curricula, age groups and regional scoring prevent direct equivalence.",
        },
    ])

    registry = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_source_registry.v1",
        "expected_source_range": [expected_start, expected_end],
        "expected_source_count": expected_end - expected_start + 1,
        "source_count": len(registry_sources),
        "batch_count": len(manifest["batches"]),
        "batch_inventory": manifest["batches"],
        "sources": registry_sources,
        "claim_boundaries": {"source_role": SOURCE_ROLE, "authority_status": AUTHORITY, "canonical_promotion_allowed": False},
    }
    reuse = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_reuse_candidates.v1",
        "candidate_count": len(reuse_candidates),
        "candidates": reuse_candidates,
    }
    admission = {
        "task_id": TASK_ID,
        "schema_version": "ket.comp.transcript_admission_decisions.v1",
        "global_policy": {"source_role": SOURCE_ROLE, "canonical_promotion_allowed": False},
        "decision_count": len(admission_decisions),
        "decisions": admission_decisions,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        FILE_NAMES["registry"]: _json_dump(registry),
        FILE_NAMES["content"]: "".join(_json_dump(row, compact=True) for row in content_units),
        FILE_NAMES["reuse"]: _json_dump(reuse),
        FILE_NAMES["admission"]: _json_dump(admission),
    }
    hashes = {}
    for filename, text in outputs.items():
        (output_dir / filename).write_text(text, encoding="utf-8")
        hashes[filename] = _sha256_text(text)
    return {
        "task_id": TASK_ID,
        "source_count": len(sources),
        "content_unit_count": len(content_units),
        "reuse_candidate_count": len(reuse_candidates),
        "admission_decision_count": len(admission_decisions),
        "output_hashes": hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
