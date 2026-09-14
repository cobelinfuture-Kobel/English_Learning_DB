from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from builders.ket_s4_image_codec import HASH_TARGET, PNG_ENCODING, RENDER_DPI, RENDER_ENGINE, RENDER_ENGINE_VERSION
from builders.ket_s4_structural import CROP_INDEX_BASE, EXPECTED_IMAGE_COUNT, QUESTION_BINDING, REUSE_STATUS, SCHEMA, STORAGE_ROLE, TASK_ID, S4Error, build_structural_inventory

STATUS = "PASS_KET_DATA_S4_IMAGE_ASSET_EXTRACTION_CONTRACT"
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def validate_structural(root: str | Path | None = None) -> dict:
    m = build_structural_inventory(root); assets = m.get("assets") or []; e = []
    if (m.get("schema"), m.get("task_id"), m.get("contract_source"), m.get("materialization_mode")) != (SCHEMA, TASK_ID, "KET_S4.txt", "STRUCTURAL_INDEX"): e.append("TOP_CONTRACT")
    ids = [a.get("image_asset_id") for a in assets]
    if len(assets) != EXPECTED_IMAGE_COUNT or ids != [f"KET_IMG_{i:06d}" for i in range(1, EXPECTED_IMAGE_COUNT + 1)]: e.append("IMAGE_IDENTITIES")
    page_indexes = defaultdict(list); refs_all = set(); bound = multi = 0
    for a in assets:
        iid, sid, page, refs = a.get("image_asset_id"), a.get("source_id"), a.get("page_ref"), a.get("question_refs")
        if not isinstance(sid, str) or not re.fullmatch(r"KET_SRC_\d{6}", sid): e.append(f"SOURCE:{iid}")
        if not isinstance(page, str) or not page.startswith(f"{sid}_P"): e.append(f"PAGE:{iid}")
        if not isinstance(refs, list) or refs != sorted(set(refs)): e.append(f"REFS:{iid}")
        else:
            bound += bool(refs); multi += len(refs) > 1
            for ref in refs:
                if not re.fullmatch(r"KET_ITEM_\d{6}", ref): e.append(f"REF_ID:{iid}")
                refs_all.add(ref)
        if (a.get("binding_precision"), a.get("storage_role"), a.get("reuse_status"), a.get("image_hash")) != (QUESTION_BINDING, STORAGE_ROLE, REUSE_STATUS, None): e.append(f"ASSET_CONTRACT:{iid}")
        ci = a.get("crop_index")
        if not isinstance(ci, int) or ci < CROP_INDEX_BASE: e.append(f"CROP:{iid}")
        else: page_indexes[page].append(ci)
    if any(v != list(range(CROP_INDEX_BASE, CROP_INDEX_BASE + len(v))) for v in page_indexes.values()): e.append("CROP_SEQUENCE")
    expected_hash = {"render_dpi": RENDER_DPI, "render_engine": RENDER_ENGINE, "render_engine_version": RENDER_ENGINE_VERSION, "bbox_rounding": "OUTWARD_AFTER_MAPPING_S1_PAGE_COORDS_TO_RENDERED_PIXELS", "pixel_mode": "RGB", "file_format": "PNG", "metadata": "STRIPPED", "png_encoding": PNG_ENCODING, "hash_algorithm": "SHA-256", "hash_target": HASH_TARGET}
    if m.get("canonical_crop_hash_contract") != expected_hash: e.append("HASH_CONTRACT")
    if m.get("copyright_boundary") != {"raw_image_bytes_in_github": False, "copyrighted_exact_crops_in_github": False, "private_storage_required": True}: e.append("COPYRIGHT")
    if e: raise S4Error("\n".join(e[:100]))
    return {"task_id": TASK_ID, "status": STATUS, "image_asset_count": len(assets), "first_image_asset_id": ids[0], "last_image_asset_id": ids[-1], "question_bound_image_count": bound, "multi_question_page_binding_image_count": multi, "distinct_question_ref_count": len(refs_all), "new_image_identity_count": 0, "question_binding": QUESTION_BINDING, "crop_index_base": CROP_INDEX_BASE, "copyright_boundary": "PASS", "private_hash_materialization": "READY_NOT_REQUIRED_FOR_PUBLIC_CI"}


def validate_private_manifest(manifest: dict, root: str | Path | None = None) -> dict:
    structural = {a["image_asset_id"]: a for a in build_structural_inventory(root)["assets"]}; assets = manifest.get("assets") or []; e = []; seen = set()
    if manifest.get("materialization_mode") != "PRIVATE_FULL" or len(assets) != EXPECTED_IMAGE_COUNT: e.append("PRIVATE_TOP")
    for a in assets:
        iid = a.get("image_asset_id"); expected = structural.get(iid)
        if iid in seen or expected is None: e.append(f"PRIVATE_ID:{iid}"); continue
        seen.add(iid)
        for k in ("source_id", "page_ref", "question_refs", "crop_index", "storage_role", "reuse_status", "binding_precision"):
            if a.get(k) != expected.get(k): e.append(f"LINEAGE:{iid}:{k}")
        if not HASH_RE.fullmatch(a.get("image_hash") or ""): e.append(f"HASH:{iid}")
    if set(structural) != seen: e.append("PRIVATE_ID_SET")
    if e: raise S4Error("\n".join(e[:100]))
    return {"task_id": TASK_ID, "status": "PASS_KET_DATA_S4_PRIVATE_IMAGE_ASSET_MATERIALIZATION", "image_asset_count": len(assets), "hash_count": len(assets), "lineage_match": True, "raw_image_bytes_in_manifest": False}


if __name__ == "__main__": print(json.dumps(validate_structural(), ensure_ascii=False, indent=2))
