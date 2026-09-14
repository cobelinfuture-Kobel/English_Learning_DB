from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from builders.ket_s4_image_codec import canonical_rgb_png, pixel_box, png_sha256
from builders.ket_s4_structural import EXPECTED_IMAGE_COUNT, asset_rows
from validators.validate_ket_data_s4_image_assets import STATUS, validate_structural


def _png_chunk_types(data: bytes) -> list[bytes]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    pos = 8; kinds = []
    while pos < len(data):
        size = struct.unpack(">I", data[pos:pos + 4])[0]; kinds.append(data[pos + 4:pos + 8]); pos += 12 + size
    assert pos == len(data)
    return kinds


def test_ket_data_s4_structural_image_inventory_from_frozen_s1_and_m03():
    r = validate_structural()
    assert r["status"] == STATUS
    assert r["image_asset_count"] == EXPECTED_IMAGE_COUNT == 1572
    assert r["first_image_asset_id"] == "KET_IMG_000001"
    assert r["last_image_asset_id"] == "KET_IMG_001572"
    assert r["new_image_identity_count"] == 0
    assert r["question_binding"] == "PAGE_LEVEL_CONSERVATIVE"
    assert r["crop_index_base"] == 1
    assert r["copyright_boundary"] == "PASS"
    assert r["private_hash_materialization"] == "READY_NOT_REQUIRED_FOR_PUBLIC_CI"


def test_ket_data_s4_shared_image_contract_uses_question_refs_array_not_duplicate_image_ids():
    s1 = {"s": "ket.data.page_media_segmentation.s1.v1", "ic": {"image_id": "KET_IMG_{global_image_seq:06d}"},
        "ss": [["KET_SRC_000001", "drive-1", "one.pdf", 0, 1, "OK"]],
        "ps": [["KET_SRC_000001_P001", 0, 1, 100, 100, 0, [[], [], [], [], [], [[10, 20, 30, 40]] * 1572, []], 1, None, [], 0]]}
    rows = asset_rows(s1, [
        {"item_id": "KET_ITEM_000001", "page_ids": ["KET_SRC_000001_P001"]},
        {"item_id": "KET_ITEM_000002", "page_ids": ["KET_SRC_000001_P001"]},
    ])
    assert rows[0]["question_refs"] == ["KET_ITEM_000001", "KET_ITEM_000002"]
    assert rows[0]["crop_index"] == 1
    assert rows[-1]["image_asset_id"] == "KET_IMG_001572"


def test_ket_data_s4_canonical_png_is_metadata_free_and_byte_deterministic():
    rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
    a = canonical_rgb_png(rgb, 2, 2); b = canonical_rgb_png(rgb, 2, 2)
    assert a == b
    assert _png_chunk_types(a) == [b"IHDR", b"IDAT", b"IEND"]
    assert png_sha256(a) == "sha256:" + hashlib.sha256(a).hexdigest()
    assert png_sha256(a) == "sha256:d268586051b64827ed456d804e07a48de48145ac2c7f9b7b5b79c12964551b40"


def test_ket_data_s4_bbox_rounding_is_outward_after_page_to_pixel_mapping():
    assert pixel_box([10.2, 20.1, 30.2, 40.1], [100, 100], 200, 200) == (20, 40, 61, 81)


def test_ket_data_s4_repo_keeps_copyrighted_exact_image_bytes_out_of_data_tree():
    root = Path(__file__).resolve().parents[2]; ket = root / "data" / "ket"
    forbidden = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
    assert [p for p in ket.rglob("*") if p.is_file() and p.suffix.lower() in forbidden] == []
