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
    assert report["inventory"]["current360_episode_specific_functional_selection_count"] == 0
    assert report["inventory"]["current360_episode_specific_instantiated_dialogue_count"] == 0

    summary = report["functional_bridge_summary"]
    assert summary["episodes_with_q05_frame_routes"] == 360
    assert summary["episodes_pending_gpt5_6_functional_selection"] == 360
    assert summary["minimum_selected_functional_chunks_per_episode"] == 0
    assert summary["episodes_with_selected_q08_functions"] == 0
    assert summary["episodes_with_selected_functional_chunks"] == 0
    assert summary["episodes_with_selected_dialogue_skeletons"] == 0
    assert summary["episodes_with_selected_production_ladders"] == 0
    assert summary["episodes_with_selected_ket_seed_routes"] == 0
    assert summary["current360_passage_rewrite_count"] == 0
    assert summary["python_selected_functional_language_count"] == 0

    assert report["scope"]["q08_semantic_communicative_function_authority_preserved"] is True
    assert report["scope"]["functional_language_is_optional_per_episode"] is True
    assert report["scope"]["functional_language_selection_authority"] == "GPT5_6_EPISODE_SEMANTIC_REVIEW"
    assert report["scope"]["functional_language_forced_per_episode"] is False
    assert report["scope"]["minimum_functional_chunks_per_episode"] == 0
    assert report["scope"]["parallel_communicative_function_authority_created"] is False
    assert report["scope"]["parallel_baseline_created"] is False
    assert report["scope"]["current360_regenerated"] is False
    assert report["scope"]["episode_specific_functional_selection_materialized"] is False
    assert report["scope"]["episode_specific_spoken_dialogue_materialized"] is False
    assert report["remaining_productive_gap"] == "GPT5_6_EPISODE_SPECIFIC_FUNCTIONAL_SELECTION_AND_NATURAL_SPOKEN_REALIZATION_NOT_YET_MATERIALIZED"

    routes = report["current360_productive_routes"]
    assert len(routes) == 360
    assert all(row["functional_chunk_refs"] == [] for row in routes)
    assert all(row["q08_communicative_function_refs"] == [] for row in routes)
    assert all(row["dialogue_skeleton_refs"] == [] for row in routes)
    assert all(row["functional_selection_status"] == "PENDING_GPT5_6_EPISODE_SEMANTIC_REVIEW" for row in routes)


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
        assert manifest["scope"]["functional_language_is_optional_per_episode"] is True
        assert manifest["scope"]["functional_language_forced_per_episode"] is False
        assert manifest["scope"]["minimum_functional_chunks_per_episode"] == 0
        assert manifest["scope"]["parallel_communicative_function_authority_created"] is False
        assert manifest["scope"]["parallel_baseline_created"] is False
        routes = json.loads(f.read("12_FUNCTIONAL_LANGUAGE/Unit04_Current360_Productive_Routes_360.json"))
        assert len(routes) == 360
        assert len({row["episode_id"] for row in routes}) == 360
        assert all(row["functional_chunk_refs"] == [] for row in routes)
        assert all(row["q08_communicative_function_refs"] == [] for row in routes)
        assert all(row["dialogue_skeleton_refs"] == [] for row in routes)
