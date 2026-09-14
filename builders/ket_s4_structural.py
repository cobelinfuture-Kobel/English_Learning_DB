from __future__ import annotations

import base64
import hashlib
import json
import lzma
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from builders.ket_s4_image_codec import HASH_TARGET, PNG_ENCODING, RENDER_DPI, RENDER_ENGINE, RENDER_ENGINE_VERSION

TASK_ID = "KET_Data_S4_ImageAssetExtraction"
SCHEMA = "ket.data.s4.image_asset_manifest.v1"
S1_XZ_SHA256 = "b557257b09693a65069e42885c4cbe76347a27e5f54c8090b9b94646252d6a04"
S1_JSON_SHA256 = "b915a0af67a57ae8b6b2b3ac7f16d8f2a6466b18bd6a3b41f50d6aa02a232480"
EXPECTED_IMAGE_COUNT = 1572
STORAGE_ROLE = "PRIVATE_REFERENCE_ASSET"
REUSE_STATUS = "REFERENCE_ONLY"
QUESTION_BINDING = "PAGE_LEVEL_CONSERVATIVE"
CROP_INDEX_BASE = 1

class S4Error(ValueError): pass

def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])

def _load_s1(root=None) -> dict:
    base = _root(root) / "data" / "ket"
    text = "".join((base / f"ket_page_media_segmentation.json.xz.b64.part{i}").read_text("ascii").strip() for i in (0, 1))
    xz = base64.b64decode(text, validate=True)
    if hashlib.sha256(xz).hexdigest() != S1_XZ_SHA256: raise S4Error("S1_XZ_SHA256_DRIFT")
    raw = lzma.decompress(xz, format=lzma.FORMAT_XZ)
    if hashlib.sha256(raw).hexdigest() != S1_JSON_SHA256: raise S4Error("S1_JSON_SHA256_DRIFT")
    return json.loads(raw)

def _items(root=None) -> list[dict]:
    from validators.validate_ket_data_s1r2_m03_full_corpus_lineage import materialize
    return materialize(_root(root))["resolved_items"]

def asset_rows(s1: dict, items: Iterable[dict]) -> list[dict]:
    if s1.get("s") != "ket.data.page_media_segmentation.s1.v1": raise S4Error("S1_SCHEMA")
    if s1.get("ic", {}).get("image_id") != "KET_IMG_{global_image_seq:06d}": raise S4Error("S1_IMAGE_ID_CONTRACT")
    page_items = defaultdict(set)
    for item in items:
        iid = item.get("item_id")
        if not isinstance(iid, str) or not iid.startswith("KET_ITEM_"): raise S4Error("M03_ITEM_ID")
        for pid in item.get("page_ids") or []: page_items[pid].add(iid)
    sources, out = s1["ss"], []
    for row in s1["ps"]:
        pid, si, pn, pw, ph, _tm, regions, istart, _qstart, _labels, _bits = row
        sid, drive, name = sources[si][0:3]; boxes = regions[5]
        if bool(boxes) != (istart is not None): raise S4Error(f"S1_IMAGE_START:{pid}")
        for off, bbox in enumerate(boxes):
            seq = istart + off
            out.append({"image_asset_id": f"KET_IMG_{seq:06d}", "source_id": sid, "page_ref": pid,
                "question_refs": sorted(page_items.get(pid, set())), "crop_index": off + 1,
                "image_hash": None, "storage_role": STORAGE_ROLE, "reuse_status": REUSE_STATUS,
                "binding_precision": QUESTION_BINDING, "source_bbox": bbox, "source_page_size": [pw, ph],
                "source_page_number": pn, "drive_file_id": drive, "source_file_name": name})
    out.sort(key=lambda a: int(a["image_asset_id"].split("_")[-1]))
    if [a["image_asset_id"] for a in out] != [f"KET_IMG_{i:06d}" for i in range(1, EXPECTED_IMAGE_COUNT + 1)]: raise S4Error("IMAGE_ID_SEQUENCE")
    return out

def build_structural_inventory(root=None) -> dict:
    assets = asset_rows(_load_s1(root), _items(root))
    return {"schema": SCHEMA, "task_id": TASK_ID, "contract_source": "KET_S4.txt", "materialization_mode": "STRUCTURAL_INDEX",
        "authority": {"s1_image_identity_authority": "FROZEN_S1_SEGMENTATION", "item_page_lineage_authority": "KET_DATA_S1R2_M03", "new_image_id_allocation_allowed": False, "question_binding": QUESTION_BINDING, "crop_index_base": 1},
        "canonical_crop_hash_contract": {"render_dpi": RENDER_DPI, "render_engine": RENDER_ENGINE, "render_engine_version": RENDER_ENGINE_VERSION, "bbox_rounding": "OUTWARD_AFTER_MAPPING_S1_PAGE_COORDS_TO_RENDERED_PIXELS", "pixel_mode": "RGB", "file_format": "PNG", "metadata": "STRIPPED", "png_encoding": PNG_ENCODING, "hash_algorithm": "SHA-256", "hash_target": HASH_TARGET},
        "copyright_boundary": {"raw_image_bytes_in_github": False, "copyrighted_exact_crops_in_github": False, "private_storage_required": True},
        "image_asset_count": len(assets), "assets": assets}
