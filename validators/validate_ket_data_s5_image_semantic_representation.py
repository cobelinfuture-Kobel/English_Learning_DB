from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from builders.build_ket_data_s5_image_semantic_representation import EXPECTED_IMAGE_COUNT, OUTPUT_SCHEMA, TASK_ID, materialize

STATUS = "PASS_KET_DATA_S5_IMAGE_SEMANTIC_REPRESENTATION"
S4_PRIVATE_MANIFEST_SHA256 = "fdd2bb28140545ba0c640323cb7032e48fb177cea72e998f4f5810618484b598"
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REL_KEYS = {"subject", "relation", "object"}
FUTURE_DIMENSIONS = ["people", "appearance", "actions", "sequence", "emotion", "weather", "quantity", "comparison", "cause", "event", "interaction"]


class S5Error(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _payload(row: dict) -> dict:
    return {k: row[k] for k in ("semantic_status", "visual_content_type", "scene_family", "setting", "participants", "objects", "actions", "relations")}


def validate(root=None, *, structural_override_path=None, s4_private_manifest_path=None) -> dict:
    root = _root(root)
    out = materialize(root, structural_override_path=structural_override_path)
    errors = []
    assets = out.get("assets") or []
    expected_ids = [f"KET_IMG_{i:06d}" for i in range(1, EXPECTED_IMAGE_COUNT + 1)]
    if out.get("schema") != OUTPUT_SCHEMA or out.get("task_id") != TASK_ID:
        errors.append("TOP_CONTRACT")
    if [x.get("image_asset_id") for x in assets] != expected_ids:
        errors.append("IMAGE_ID_SEQUENCE")
    pred = out.get("s4_predecessor") or {}
    if pred.get("private_manifest_sha256") != S4_PRIVATE_MANIFEST_SHA256 or pred.get("new_image_identity_allocation_allowed") is not False:
        errors.append("S4_PREDECESSOR")
    if (out.get("semantic_contract") or {}).get("schema_extension_targets") != FUTURE_DIMENSIONS:
        errors.append("EXTENSION_TARGETS")

    status_counts = Counter(); type_counts = Counter()
    for row in assets:
        iid = row.get("image_asset_id"); status = row.get("semantic_status"); ctype = row.get("visual_content_type")
        if status not in {"SCENE_STRUCTURED", "NON_SCENE_VISUAL"}: errors.append(f"STATUS:{iid}")
        if not isinstance(ctype, str) or not ctype: errors.append(f"CONTENT_TYPE:{iid}")
        status_counts[status] += 1; type_counts[ctype] += 1
        parts, objs, acts, rels = row.get("participants"), row.get("objects"), row.get("actions"), row.get("relations")
        if not all(isinstance(x, list) for x in (parts, objs, acts, rels)):
            errors.append(f"LIST_FIELDS:{iid}"); continue
        for rel in rels:
            if not isinstance(rel, dict) or set(rel) != REL_KEYS or any(not isinstance(rel[k], str) or not rel[k] for k in REL_KEYS): errors.append(f"RELATION:{iid}")
        if status == "SCENE_STRUCTURED":
            if ctype != "PHOTO_SCENE" or not row.get("scene_family") or not row.get("setting") or not parts or not acts or not rels:
                errors.append(f"SCENE_MINIMUM:{iid}")
        else:
            if row.get("scene_family") is not None or row.get("setting") is not None or parts or objs or acts or rels:
                errors.append(f"NON_SCENE_HALLUCINATION:{iid}")

    private_hash_binding = None; duplicate_conflicts = 0; unique_hashes = None
    if s4_private_manifest_path:
        p = Path(s4_private_manifest_path)
        if hashlib.sha256(p.read_bytes()).hexdigest() != S4_PRIVATE_MANIFEST_SHA256:
            errors.append("S4_PRIVATE_MANIFEST_SHA256")
        else:
            pm = json.loads(p.read_text(encoding="utf-8")); pa = pm.get("assets") or []
            pmap = {x.get("image_asset_id"): x.get("image_hash") for x in pa}
            if len(pa) != EXPECTED_IMAGE_COUNT or set(pmap) != set(expected_ids): errors.append("S4_PRIVATE_ID_SET")
            contract = json.loads((root / "data" / "ket" / "ket_s5_image_semantic_representation.json").read_text(encoding="utf-8"))
            for scene in contract.get("scene_annotations") or []:
                if not HASH_RE.fullmatch(scene.get("source_image_hash") or "") or pmap.get(scene["image_asset_id"]) != scene.get("source_image_hash"):
                    errors.append("SCENE_SOURCE_HASH:" + scene.get("image_asset_id", "?"))
            rows = {x["image_asset_id"]: x for x in assets}; by_hash = defaultdict(list)
            for iid, h in pmap.items(): by_hash[h].append(iid)
            for h, ids in by_hash.items():
                if len(ids) > 1:
                    base = _payload(rows[ids[0]])
                    if any(_payload(rows[i]) != base for i in ids[1:]):
                        duplicate_conflicts += 1; errors.append("DUPLICATE_PIXEL_SEMANTIC_CONFLICT:" + h)
            private_hash_binding = True
            unique_hashes = len(by_hash)

    if out.get("summary") != {
        "image_asset_count": len(assets), "scene_structured_count": status_counts["SCENE_STRUCTURED"], "non_scene_visual_count": status_counts["NON_SCENE_VISUAL"],
        "content_type_counts": dict(sorted(type_counts.items())), "duplicate_pixel_semantic_conflict_count": 0, "new_image_identity_count": 0,
    }:
        errors.append("SUMMARY")
    if status_counts["SCENE_STRUCTURED"] != 15: errors.append("SCENE_COUNT")
    if errors: raise S5Error("\n".join(errors[:100]))
    return {
        "task_id": TASK_ID, "status": STATUS, "image_asset_count": len(assets), "scene_structured_count": status_counts["SCENE_STRUCTURED"],
        "non_scene_visual_count": status_counts["NON_SCENE_VISUAL"], "s4_identity_lineage": True, "s4_private_hash_binding": private_hash_binding,
        "unique_source_image_hash_count": unique_hashes, "duplicate_pixel_semantic_conflict_count": duplicate_conflicts, "new_image_identity_count": 0,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--structural-override"); ap.add_argument("--s4-private-manifest")
    ns = ap.parse_args(); print(json.dumps(validate(structural_override_path=ns.structural_override, s4_private_manifest_path=ns.s4_private_manifest), ensure_ascii=False, indent=2))
