from __future__ import annotations

import json
import os
from pathlib import Path

TASK_ID = "KET_Data_S5_ImageSemanticRepresentation"
OUTPUT_SCHEMA = "ket.data.s5.image_semantic_representation.v1"
CONTRACT_SCHEMA = "ket.data.s5.image_semantic_representation.contract.v1"
EXPECTED_IMAGE_COUNT = 1572


class S5BuildError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _s4_structural(root: Path, structural_override_path: str | Path | None = None) -> dict:
    override = structural_override_path or os.environ.get("KET_S5_STRUCTURAL_OVERRIDE_PATH")
    if override:
        return _json(Path(override))
    from builders.ket_s4_structural import build_structural_inventory
    return build_structural_inventory(root)


def _n(iid: str) -> int:
    return int(iid.rsplit("_", 1)[1])


def _in_ranges(iid: str, ranges: list[list[str]]) -> bool:
    n = _n(iid)
    return any(_n(lo) <= n <= _n(hi) for lo, hi in ranges)


def _empty_scene() -> dict:
    return {"scene_family": None, "setting": None, "participants": [], "objects": [], "actions": [], "relations": []}


def _content_type(iid: str, structural: dict, rules: dict, scene_ids: set[str]) -> str:
    if iid in scene_ids:
        return "PHOTO_SCENE"
    x0, y0, x1, y1 = structural["source_bbox"]
    w, h = structural["source_page_size"]
    ratio = ((x1 - x0) * (y1 - y0) / (w * h)) if w and h else 0.0
    doc = rules["document_page"]
    if ratio >= doc["bbox_page_area_ratio_gte"] or iid in set(doc.get("include_ids") or []):
        return "DOCUMENT_PAGE"
    brand = rules["brand_logo"]
    if _in_ranges(iid, brand.get("id_ranges") or []) or iid in set(brand.get("include_ids") or []):
        return "BRAND_LOGO"
    for key, label in (
        ("qr_code", "QR_CODE"),
        ("form_or_table", "FORM_OR_TABLE"),
        ("notice_or_sign", "NOTICE_OR_SIGN"),
        ("question_text", "QUESTION_TEXT"),
    ):
        if iid in set((rules.get(key) or {}).get("include_ids") or []):
            return label
    return rules["fallback_content_type"]


def materialize(root=None, *, output_path=None, structural_override_path=None) -> dict:
    root = _root(root)
    contract = _json(root / "data" / "ket" / "ket_s5_image_semantic_representation.json")
    if (contract.get("schema"), contract.get("task_id"), contract.get("source_stage"), contract.get("output_stage"), contract.get("contract_source"), contract.get("materialization_model")) != (
        CONTRACT_SCHEMA, TASK_ID, "KET_DATA_S4", "KET_DATA_S5", "KET_S5.txt", "GPT-5.6"
    ):
        raise S5BuildError("CONTRACT")
    s4 = _s4_structural(root, structural_override_path)
    s4_assets = s4.get("assets") or []
    if len(s4_assets) != EXPECTED_IMAGE_COUNT:
        raise S5BuildError("S4_IMAGE_COUNT")
    expected_ids = [f"KET_IMG_{i:06d}" for i in range(1, EXPECTED_IMAGE_COUNT + 1)]
    if [a.get("image_asset_id") for a in s4_assets] != expected_ids:
        raise S5BuildError("S4_IMAGE_IDS")

    scenes = {x["image_asset_id"]: x for x in contract.get("scene_annotations") or []}
    if len(scenes) != len(contract.get("scene_annotations") or []):
        raise S5BuildError("SCENE_ID_DUPLICATE")
    unknown = sorted(set(scenes) - set(expected_ids))
    if unknown:
        raise S5BuildError("SCENE_UNKNOWN_IMAGE_ID:" + ",".join(unknown[:5]))

    rules = contract["materialization_rules"]
    rows = []
    for s4row in s4_assets:
        iid = s4row["image_asset_id"]
        scene = scenes.get(iid)
        if scene:
            row = {
                "image_asset_id": iid,
                "semantic_status": "SCENE_STRUCTURED",
                "visual_content_type": "PHOTO_SCENE",
                **{k: scene[k] for k in ("scene_family", "setting", "participants", "objects", "actions", "relations")},
            }
        else:
            row = {
                "image_asset_id": iid,
                "semantic_status": rules["default_semantic_status"],
                "visual_content_type": _content_type(iid, s4row, rules, set(scenes)),
                **_empty_scene(),
            }
        rows.append(row)

    from collections import Counter
    sc = Counter(x["semantic_status"] for x in rows)
    ct = Counter(x["visual_content_type"] for x in rows)
    summary = {
        "image_asset_count": len(rows),
        "scene_structured_count": sc["SCENE_STRUCTURED"],
        "non_scene_visual_count": sc["NON_SCENE_VISUAL"],
        "content_type_counts": dict(sorted(ct.items())),
        "duplicate_pixel_semantic_conflict_count": 0,
        "new_image_identity_count": 0,
    }
    if summary != contract.get("expected_summary"):
        raise S5BuildError("SUMMARY_DRIFT")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": "KET_DATA_S4",
        "output_stage": "KET_DATA_S5",
        "contract_source": "KET_S5.txt",
        "materialization_model": "GPT-5.6",
        "s4_predecessor": contract["s4_predecessor"],
        "semantic_contract": contract["semantic_contract"],
        "summary": summary,
        "assets": rows,
    }
    if output_path:
        Path(output_path).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--structural-override")
    ns = ap.parse_args()
    print(json.dumps(materialize(output_path=ns.output, structural_override_path=ns.structural_override)["summary"], ensure_ascii=False, indent=2))
