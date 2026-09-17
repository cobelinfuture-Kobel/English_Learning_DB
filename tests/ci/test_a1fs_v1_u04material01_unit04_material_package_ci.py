from pathlib import Path
import json, zipfile

from product.a1fs_v1_2_1 import u04material01_unit04_material_package as m


def test_unit04_material_package_baseline_contract(tmp_path: Path):
    r = m.build_unit04_material_package_baseline()
    assert r["status"] == m.STATUS and r["unit_number"] == 4
    assert r["scope"] == {
        "unit04_only": True,
        "unit01_03_asset_backfill": "DEFERRED",
        "unit05_started": False,
        "current360_regenerated": False,
        "a2_a2plus_unlocked": False,
    }
    assert r["inventory"]["q03_relation_count"] == 8
    assert r["inventory"]["unit04_material_chunk_surface_count"] == 45
    assert r["inventory"]["unit04_new_exact_frame_count"] == 8
    assert r["inventory"]["unit04_sentence_asset_count"] == 96
    assert r["inventory"]["unit04_scene_binding_count"] == 96
    assert r["inventory"]["current360_episode_count"] == 360
    assert r["binding_summary"]["episode_count"] == 360
    assert r["binding_summary"]["episodes_with_grammar_refs"] == 360
    assert r["binding_summary"]["episodes_with_route_refs"] == 360
    assert r["binding_summary"]["binding_policy"] == "EXACT_OR_AUTHORITY_DECLARED_ONLY_NO_SEMANTIC_GUESSING"
    assert len(r["current360_asset_binding"]) == 360
    assert len({x["episode_id"] for x in r["current360_asset_binding"]}) == 360
    assert r["payload_sha256"]


def test_unit04_material_package_zip_reproducible(tmp_path: Path):
    a = m.materialize_unit04_material_package(output_root=tmp_path / "a")
    b = m.materialize_unit04_material_package(output_root=tmp_path / "b")
    assert a["zip_sha256"] == b["zip_sha256"]
    z = Path(a["zip_path"])
    assert z.is_file() and z.with_suffix(z.suffix + ".sha256").is_file()
    with zipfile.ZipFile(z) as f:
        names = set(f.namelist())
        required = {
            "11_MANIFEST/Unit04_Material_Package_Manifest.json",
            "05_SENTENCE_ASSETS/Unit04_Sentence_Assets_96.json",
            "07_SCENE_SEMANTIC_FACTS/Unit04_Q07_Scene_Bindings_96.json",
            "08_CURRENT360/Unit04_Current360_Effective360.json",
            "09_CURRENT360_ASSET_BINDING/Unit04_Current360_Asset_Binding.json",
        }
        assert required <= names
        manifest = json.loads(f.read("11_MANIFEST/Unit04_Material_Package_Manifest.json"))
        assert manifest["package_hash_policy"] == "ZIP_SHA256_IS_SIDECAR_ONLY_TO_AVOID_RECURSIVE_SELF_HASH"
