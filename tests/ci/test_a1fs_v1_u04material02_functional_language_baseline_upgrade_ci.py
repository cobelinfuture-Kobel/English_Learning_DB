from pathlib import Path
import json
import zipfile

from product.a1fs_v1_2_1 import u04material02_unit04_functional_language_baseline_upgrade as m


def test_unit04_functional_language_baseline_upgrade_contract():
    report = m.build_unit04_material_package_functional_upgrade()
    assert report["status"] == m.STATUS
    assert report["schema_version"] == "a1fs.v1.u04.material_package_baseline.v2"
    assert report["supersedes_task_id"]
    assert report["inventory"]["current360_episode_count"] == 360
    assert report["inventory"]["q08_communicative_function_authority_count"] == 6
    assert report["inventory"]["functional_move_count"] == 12
    assert report["inventory"]["functional_chunk_count"] == 24
    assert report["inventory"]["dialogue_skeleton_count"] == 5
    assert report["inventory"]["production_ladder_count"] == 2
    assert report["inventory"]["current360_productive_route_count"] == 360
    assert report["inventory"]["current360_episode_specific_instantiated_dialogue_count"] == 0
    assert report["functional_bridge_summary"]["episodes_with_q08_semantic_routes"] == 360
    assert report["functional_bridge_summary"]["episodes_with_functional_routes"] == 360
    assert report["functional_bridge_summary"]["episodes_with_q05_frame_routes"] == 360
    assert report["functional_bridge_summary"]["episodes_with_personal_transfer"] == 360
    assert report["functional_bridge_summary"]["episodes_with_ket_seed_routes"] == 360
    assert report["functional_bridge_summary"]["current360_passage_rewrite_count"] == 0
    assert report["scope"]["q08_semantic_communicative_function_authority_preserved"] is True
    assert report["scope"]["parallel_communicative_function_authority_created"] is False
    assert report["scope"]["parallel_baseline_created"] is False
    assert report["scope"]["current360_regenerated"] is False
    assert report["scope"]["episode_specific_spoken_dialogue_materialized"] is False
    assert report["remaining_productive_gap"] == "EPISODE_SPECIFIC_NATURAL_SPOKEN_REALIZATION_NOT_YET_MATERIALIZED"
    assert len(report["current360_productive_routes"]) == 360


def test_unit04_functional_language_baseline_upgrade_zip_is_reproducible(tmp_path: Path):
    a = m.materialize_unit04_material_package_functional_upgrade(output_root=tmp_path / "a")
    b = m.materialize_unit04_material_package_functional_upgrade(output_root=tmp_path / "b")
    assert a["zip_sha256"] == b["zip_sha256"]
    z = Path(a["zip_path"])
    assert z.name == "Unit04_Material_Package.zip"
    with zipfile.ZipFile(z) as f:
        names = set(f.namelist())
        required = {
            "01_AUTHORITY/a1fs_v1_u04_q08_communicative_function_authority.json",
            "01_AUTHORITY/a1fs_v1_u04_fl01_functional_language_core.json",
            "08_CURRENT360/Unit04_Current360_Effective360.json",
            "11_MANIFEST/Unit04_Material_Package_Manifest.json",
            "12_FUNCTIONAL_LANGUAGE/Unit04_Q08_Communicative_Function_Authority.json",
            "12_FUNCTIONAL_LANGUAGE/Unit04_Functional_Language_Surface_Core.json",
            "12_FUNCTIONAL_LANGUAGE/Unit04_Current360_Productive_Routes_360.json",
            "12_FUNCTIONAL_LANGUAGE/Unit04_Current360_Productive_Bridge_Summary.json",
        }
        assert required <= names
        manifest = json.loads(f.read("11_MANIFEST/Unit04_Material_Package_Manifest.json"))
        assert manifest["status"] == m.STATUS
        assert manifest["inventory"]["q08_communicative_function_authority_count"] == 6
        assert manifest["inventory"]["functional_chunk_count"] == 24
        assert manifest["inventory"]["current360_productive_route_count"] == 360
        assert manifest["scope"]["parallel_communicative_function_authority_created"] is False
        assert manifest["scope"]["parallel_baseline_created"] is False
        routes = json.loads(f.read("12_FUNCTIONAL_LANGUAGE/Unit04_Current360_Productive_Routes_360.json"))
        assert len(routes) == 360
        assert len({row["episode_id"] for row in routes}) == 360
        assert all(len(row["q08_communicative_function_routes"]) == 6 for row in routes)
