from __future__ import annotations

from pathlib import Path

from builders.build_ket_data_s5_image_semantic_representation import materialize
from validators.validate_ket_data_s5_image_semantic_representation import STATUS, validate

ROOT = Path(__file__).resolve().parents[2]


def test_ket_data_s5_full_identity_and_semantic_contract():
    r = validate(ROOT)
    assert r["status"] == STATUS
    assert r["image_asset_count"] == 1572
    assert r["scene_structured_count"] == 15
    assert r["non_scene_visual_count"] == 1557
    assert r["s4_identity_lineage"] is True
    assert r["new_image_identity_count"] == 0


def test_ket_data_s5_scene_grounding_and_non_scene_fail_closed():
    m = materialize(ROOT); by = {x["image_asset_id"]: x for x in m["assets"]}
    meeting = by["KET_IMG_001056"]
    assert meeting["scene_family"] == "WORK" and meeting["setting"] == "MEETING_ROOM"
    assert {"laptop", "papers", "table"}.issubset(meeting["objects"])
    assert {"subject": "laptop", "relation": "on", "object": "table"} in meeting["relations"]
    house = by["KET_IMG_001068"]
    assert house["scene_family"] == "HOUSING" and house["setting"] == "RESIDENTIAL_EXTERIOR"
    assert {"subject": "people", "relation": "in_front_of", "object": "house"} in house["relations"]
    page = by["KET_IMG_000001"]
    assert page["semantic_status"] == "NON_SCENE_VISUAL" and page["visual_content_type"] == "DOCUMENT_PAGE"
    assert page["scene_family"] is None and page["participants"] == page["objects"] == page["actions"] == page["relations"] == []


def test_ket_data_s5_content_type_and_growth_contract():
    m = materialize(ROOT); by = {x["image_asset_id"]: x for x in m["assets"]}
    assert by["KET_IMG_000607"]["visual_content_type"] == "BRAND_LOGO"
    assert by["KET_IMG_000983"]["visual_content_type"] == "QR_CODE"
    assert by["KET_IMG_001030"]["visual_content_type"] == "NOTICE_OR_SIGN"
    assert by["KET_IMG_001446"]["visual_content_type"] == "DOCUMENT_PAGE"
    assert m["semantic_contract"]["schema_extension_targets"] == ["people", "appearance", "actions", "sequence", "emotion", "weather", "quantity", "comparison", "cause", "event", "interaction"]
