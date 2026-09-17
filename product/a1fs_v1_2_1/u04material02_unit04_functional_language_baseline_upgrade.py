from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from product.a1fs_v1_2_1 import u04material01_unit04_material_package as base
from product.a1fs_v1_2_1 import u04fl01_current360_productive_bridge as fl

TASK_ID = "A1FS-V1-U04MATERIAL02_Unit04FunctionalLanguageBaselineUpgrade"
STATUS = "PASS_A1FS_V1_U04MATERIAL02_FUNCTIONAL_LANGUAGE_BASELINE_UPGRADE"
REVISION = "UNIT04_BASELINE_CURRENT360_FUNCTIONAL_LANGUAGE_V2"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Successor materializer over the merged Unit04 baseline, Q08 semantic authority, and U04FL01 "
    "functional-language surface bridge. It adds assets to the same Unit04_Material_Package output; "
    "it does not author or rewrite learner-facing English and does not create a parallel baseline."
)

FUNCTIONAL_DIR = "12_FUNCTIONAL_LANGUAGE"
FUNCTIONAL_CORE_PATH = fl.FUNCTIONAL_CORE_PATH
Q08_PATH = fl.Q08_PATH


class Unit04MaterialPackageFunctionalUpgradeError(ValueError):
    pass


def _root(repo_root=None) -> Path:
    return Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_unit04_material_package_functional_upgrade(repo_root=None):
    root = _root(repo_root)
    baseline = base.build_unit04_material_package_baseline(root)
    bridge = fl.build_unit04_current360_productive_bridge(root)
    if baseline.get("status") != base.STATUS:
        raise Unit04MaterialPackageFunctionalUpgradeError("baseline_status_drift")
    if bridge.get("status") != fl.STATUS:
        raise Unit04MaterialPackageFunctionalUpgradeError("functional_bridge_status_drift")

    baseline_passages = {row["episode_id"]: str(row["passage"]) for row in baseline["current360"]}
    route_rows = bridge["episode_productive_routes"]
    if len(baseline_passages) != 360 or len(route_rows) != 360:
        raise Unit04MaterialPackageFunctionalUpgradeError("current360_count_drift")
    for row in route_rows:
        passage = baseline_passages.get(row["episode_id"])
        if passage is None:
            raise Unit04MaterialPackageFunctionalUpgradeError(
                f"episode_missing_from_baseline:{row['episode_id']}"
            )
        if _sha_text(passage) != row["passage_sha256"]:
            raise Unit04MaterialPackageFunctionalUpgradeError(
                f"current360_passage_hash_drift:{row['episode_id']}"
            )

    core_path = root / FUNCTIONAL_CORE_PATH
    q08_path = root / Q08_PATH
    core = base._json(core_path)
    q08 = base._json(q08_path)
    if q08.get("status") != fl.Q08_STATUS:
        raise Unit04MaterialPackageFunctionalUpgradeError("q08_status_drift")

    source_refs = list(baseline["source_refs"])
    for rel, value in ((Q08_PATH, q08), (FUNCTIONAL_CORE_PATH, core)):
        if not any(row["path"] == rel for row in source_refs):
            source_refs.append({"path": rel, "sha256": base._sha(root / rel), "status": value["status"]})

    inventory = dict(baseline["inventory"])
    inventory.update(
        {
            "q08_communicative_function_authority_count": bridge["summary"]["q08_communicative_function_authority_count"],
            "functional_move_count": bridge["summary"]["functional_move_count"],
            "functional_chunk_count": bridge["summary"]["functional_chunk_authority_count"],
            "dialogue_skeleton_count": bridge["summary"]["dialogue_skeleton_count"],
            "production_ladder_count": bridge["summary"]["production_ladder_count"],
            "current360_productive_route_count": len(route_rows),
            "current360_episode_specific_instantiated_dialogue_count": bridge["summary"]["episode_specific_instantiated_dialogue_count"],
        }
    )

    scope = dict(baseline["scope"])
    scope.update(
        {
            "q08_semantic_communicative_function_authority_preserved": True,
            "functional_language_surface_core_materialized": True,
            "current360_productive_bridge_materialized": True,
            "current360_passage_rewrite_count": 0,
            "parallel_communicative_function_authority_created": False,
            "parallel_baseline_created": False,
            "episode_specific_spoken_dialogue_materialized": False,
        }
    )

    return {
        "schema_version": "a1fs.v1.u04.material_package_baseline.v2",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": baseline["unit_id"],
        "baseline_role": baseline["baseline_role"],
        "supersedes_task_id": base.TASK_ID,
        "scope": scope,
        "inventory": inventory,
        "binding_summary": baseline["binding_summary"],
        "functional_bridge_summary": bridge["summary"],
        "source_refs": source_refs,
        "q08_communicative_function_authority": q08,
        "functional_language_core": bridge["functional_language_core"],
        "current360_productive_routes": route_rows,
        "base_payload_sha256": baseline["payload_sha256"],
        "remaining_productive_gap": "EPISODE_SPECIFIC_NATURAL_SPOKEN_REALIZATION_NOT_YET_MATERIALIZED",
    }


def materialize_unit04_material_package_functional_upgrade(repo_root=None, output_root=None):
    root = _root(repo_root)
    upgraded = build_unit04_material_package_functional_upgrade(root)
    out = Path(output_root).resolve() if output_root else root / "build" / "unit04_material_package"

    baseline_result = base.materialize_unit04_material_package(root, out)
    pkg = Path(baseline_result["package_root"])
    functional_dir = pkg / FUNCTIONAL_DIR
    functional_dir.mkdir(parents=True, exist_ok=True)

    core_source = root / FUNCTIONAL_CORE_PATH
    q08_source = root / Q08_PATH
    shutil.copy2(q08_source, pkg / "01_AUTHORITY" / q08_source.name)
    shutil.copy2(core_source, pkg / "01_AUTHORITY" / core_source.name)
    base._write_json(
        functional_dir / "Unit04_Q08_Communicative_Function_Authority.json",
        upgraded["q08_communicative_function_authority"],
    )
    base._write_json(
        functional_dir / "Unit04_Functional_Language_Surface_Core.json",
        upgraded["functional_language_core"],
    )
    base._write_json(
        functional_dir / "Unit04_Current360_Productive_Routes_360.json",
        upgraded["current360_productive_routes"],
    )
    base._write_json(
        functional_dir / "Unit04_Current360_Productive_Bridge_Summary.json",
        upgraded["functional_bridge_summary"],
    )
    base._write_json(pkg / "10_REFERENCE_LINEAGE" / "Source_Refs.json", upgraded["source_refs"])

    manifest = {
        key: upgraded[key]
        for key in (
            "schema_version", "task_id", "status", "revision", "unit_number", "unit_id",
            "baseline_role", "supersedes_task_id", "scope", "inventory", "binding_summary",
            "functional_bridge_summary", "source_refs", "base_payload_sha256", "remaining_productive_gap",
        )
    }
    manifest["package_hash_policy"] = "ZIP_SHA256_IS_SIDECAR_ONLY_TO_AVOID_RECURSIVE_SELF_HASH"
    manifest["payload_sha256"] = base._digest(manifest)
    base._write_json(pkg / "11_MANIFEST" / "Unit04_Material_Package_Manifest.json", manifest)

    target = out / "Unit04_Material_Package.zip"
    target.unlink(missing_ok=True)
    target.with_suffix(target.suffix + ".sha256").unlink(missing_ok=True)
    digest = base._zip(pkg, target)
    return {
        "status": STATUS,
        "package_root": str(pkg),
        "zip_path": str(target),
        "zip_sha256": digest,
        "manifest": manifest,
    }


def main():
    print(json.dumps(materialize_unit04_material_package_functional_upgrade(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
