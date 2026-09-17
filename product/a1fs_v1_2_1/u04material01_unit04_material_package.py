from __future__ import annotations

import csv, hashlib, json, re, shutil, zipfile
from collections import Counter
from pathlib import Path

from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as neb360

TASK_ID = "A1FS-V1-U04MATERIAL01_Unit04MaterialPackageBaseline"
STATUS = "PASS_A1FS_V1_U04MATERIAL01_UNIT04_MATERIAL_PACKAGE_BASELINE"
REVISION = "UNIT04_BASELINE_CURRENT360_ASSET_LINEAGE_V1"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit04 handoff materializer over approved Q01-Q07 authorities and Current360; "
    "it does not author, rewrite, promote, or regenerate learner-facing English."
)

Q01 = "ulga/contracts/a1fs_v1_u04_q01_place_prepositions_scope_admission.json"
Q02 = "ulga/contracts/a1fs_v1_u04_q02_vocabulary_authority.json"
Q03 = "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q04 = "ulga/contracts/a1fs_v1_u04_q04_place_chunk_authority.json"
Q05 = "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
Q06 = "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07 = "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
EXPECTED = {
    Q01: "CURRENT_UNIT_Q01_AUTHORITY_ADMITTED",
    Q02: "PASS_Q02_UNIT04_VOCABULARY_AND_EXACT_SURFACE_ADMISSION",
    Q03: "PASS_Q03_UNIT04_PLACE_RELATION_FORM_MEANING_AUTHORITY",
    Q04: "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP",
    Q05: "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY",
    Q06: "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION",
    Q07: "PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING",
}
DIRS = (
    "01_AUTHORITY", "02_GRAMMAR", "03_VOCABULARY", "04_CHUNKS", "05_SENTENCE_ASSETS",
    "06_CORE_SENTENCES", "07_SCENE_SEMANTIC_FACTS", "08_CURRENT360",
    "09_CURRENT360_ASSET_BINDING", "10_REFERENCE_LINEAGE", "11_MANIFEST",
)

class Unit04MaterialPackageError(ValueError):
    pass


def _root(repo_root=None):
    return Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]


def _json(path: Path):
    if not path.is_file():
        raise Unit04MaterialPackageError(f"missing:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Unit04MaterialPackageError(f"not_object:{path}")
    return value


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _has(text, surface):
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, re.I))


def _sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _authorities(root):
    out = {}
    for rel, status in EXPECTED.items():
        value = _json(root / rel)
        if value.get("status") != status:
            raise Unit04MaterialPackageError(f"status_drift:{rel}:{value.get('status')}")
        if int(value.get("unit_number", 4)) != 4:
            raise Unit04MaterialPackageError(f"unit_drift:{rel}")
        out[rel] = value
    return out


def _vocab(q02):
    out = []
    for row in q02["place_preposition_surface_authority"]["static_place_target_surfaces"]:
        out.append({
            "asset_class": "UNIT04_TARGET_PREPOSITION_SURFACE",
            "surface": row["surface"],
            "authority_status": row["unit04_status"],
            "level": row.get("level"),
            "guideword": row.get("guideword"),
            "source": Q02,
        })
    pool = q02["life_skill_place_carrier_pool"]
    prior = set(pool["provenance"]["prior_reuse_24"])
    ext = {x["surface"]: x for x in pool["provenance"]["yle_active_eligible_extensions"]}
    for domain, surfaces in pool["domains"].items():
        for surface in surfaces:
            meta = ext.get(surface, {})
            out.append({
                "asset_class": "UNIT04_LIFE_PLACE_CARRIER",
                "surface": surface,
                "domain": domain,
                "authority_status": "PRIOR_REUSE" if surface in prior else meta.get("unit04_status", "ACTIVE_ELIGIBLE"),
                "yle_stage": meta.get("yle_stage"),
                "evp_level": meta.get("evp_level"),
                "source": Q02,
            })
    return out


def _chunks(q04):
    out = []
    for g in q04["target_relation_chunk_groups"]:
        for role, key in (("PRIOR_EXACT_REUSE", "prior_exact_reuse"), ("UNIT04_NEW_TARGET_SURFACE", "new_surfaces")):
            for surface in g.get(key, []):
                out.append({
                    "authority_local_ref": f"U04-Q04::{_norm(surface).replace(' ', '_')}",
                    "surface": surface,
                    "relation_surface": g["relation_surface"],
                    "relation_id": g["relation_id"],
                    "role": role,
                    "source": Q04,
                })
    for g in q04.get("yle_safe_support_chunk_groups", []):
        for surface in g.get("new_surfaces", []):
            out.append({
                "authority_local_ref": f"U04-Q04::{_norm(surface).replace(' ', '_')}",
                "surface": surface,
                "relation_surface": g["support_pattern"],
                "relation_id": None,
                "role": "UNIT04_YLE_SAFE_SUPPORT_SURFACE",
                "parent_canonical_chunk_id": g.get("parent_canonical_chunk_id"),
                "source": Q04,
            })
    return out


def _frames(q05):
    prior = q05["prior_frame_baseline"]
    out = [{**x, "material_status": "PRIOR_REUSE", "source": Q05} for x in prior.get("reused_unit04_target_frames", [])]
    for key, status in (("generic_place_fallback", "PRIOR_REUSE_FALLBACK"), ("additional_reusable_scaffold", "PRIOR_REUSE_SCAFFOLD")):
        if isinstance(prior.get(key), dict):
            out.append({**prior[key], "material_status": status, "source": Q05})
    out += [{**x, "material_status": "UNIT04_NEW_EXACT_FRAME", "source": Q05} for x in q05.get("unit04_new_exact_frames", [])]
    return out


def _bindings(episodes, vocab, chunks, q03, q05, q06, q07):
    rels = {x["surface"]: x for x in q03.get("relations", [])}
    routes = {
        **q05["q06_primary_generation_routing"].get("target_relations", {}),
        **q05["q06_primary_generation_routing"].get("support_relations", {}),
    }
    q06_text = {x["normalized_text"]: x for x in q06.get("assets", [])}
    q07_sent = {x["bound_sentence_id"]: x for x in q07.get("micro_scenes", [])}
    rows, counts = [], Counter()
    for ep in episodes:
        passage = str(ep["passage"])
        declared = [x.strip() for x in str(ep["target_relations"]).split(",") if x.strip()]
        grammar = [{"surface": s, "relation_id": rels[s].get("relation_id"), "authority": Q03} for s in declared if s in rels]
        vr = [{"surface": x["surface"], "authority_local_role": x["asset_class"], "authority": Q02} for x in vocab if _has(passage, x["surface"])]
        cr = [{"surface": x["surface"], "authority_local_ref": x["authority_local_ref"], "parent_canonical_chunk_id": x.get("parent_canonical_chunk_id"), "authority": Q04} for x in chunks if _has(passage, x["surface"])]
        sr, corer, scener = [], [], []
        for sent in _sentences(passage):
            hit = q06_text.get(_norm(sent))
            if not hit:
                continue
            sid = hit["sentence_id"]
            sr.append({"sentence_id": sid, "text": hit["text"], "authority": Q06})
            if hit.get("pattern_id"):
                corer.append({"frame_id": hit["pattern_id"], "binding_basis": "EXACT_Q06_SENTENCE_PATTERN_ID", "authority": Q05})
            scene = q07_sent.get(sid)
            if scene:
                scener.append({"scene_ref_id": scene["scene_ref_id"], "bound_sentence_id": sid, "authority": Q07})
        fr = [{"relation_surface": s, "frame_id": routes[s], "binding_basis": "Q05_AUTHORIZED_ROUTE_FOR_DECLARED_RELATION", "authority": Q05} for s in declared if s in routes]
        for key, value in (("grammar", grammar), ("vocab", vr), ("chunk", cr), ("sentence", sr), ("core", corer), ("scene", scener), ("route", fr)):
            if value:
                counts[f"episodes_with_{key}_refs"] += 1
        rows.append({
            "episode_id": ep["episode_id"],
            "neb_micro_scene_id": ep["micro_scene_id"],
            "life_domain": ep["life_domain"],
            "governed_scene_family": ep["governed_scene_family"],
            "target_relations": declared,
            "grammar_refs": grammar,
            "vocabulary_refs": vr,
            "chunk_refs": cr,
            "sentence_refs": sr,
            "core_sentence_refs": corer,
            "core_sentence_frame_routes": fr,
            "scene_refs": scener,
            "source_fact_lineage": ep["source_fact_lineage"],
            "passage": passage,
            "unbound_policy": {
                "prior_unit_assets": "U01_U03_ASSET_BACKFILL_DEFERRED",
                "semantic_similarity_binding": "PROHIBITED",
                "missing_exact_ref": "KEEP_UNBOUND_DO_NOT_GUESS",
            },
        })
    summary = {
        "episode_count": len(rows),
        **counts,
        "episodes_without_exact_q06_sentence_refs": len(rows) - counts["episodes_with_sentence_refs"],
        "episodes_without_exact_q07_scene_refs": len(rows) - counts["episodes_with_scene_refs"],
        "binding_policy": "EXACT_OR_AUTHORITY_DECLARED_ONLY_NO_SEMANTIC_GUESSING",
        "unit01_03_asset_backfill": "DEFERRED",
    }
    return rows, summary


def build_unit04_material_package_baseline(repo_root=None):
    root = _root(repo_root)
    a = _authorities(root)
    q01, q02, q03, q04, q05, q06, q07 = (a[Q01], a[Q02], a[Q03], a[Q04], a[Q05], a[Q06], a[Q07])
    current = neb360.build_unit04_neb02_natural_episode_bank_360(root)
    if current.get("status") != neb360.STATUS:
        raise Unit04MaterialPackageError("current360_status_drift")
    episodes = [dict(x) for x in current.get("effective_episodes", [])]
    vocab, chunks, frames = _vocab(q02), _chunks(q04), _frames(q05)
    bindings, summary = _bindings(episodes, vocab, chunks, q03, q05, q06, q07)
    if len(episodes) != 360 or len(chunks) != 45 or len(q06.get("assets", [])) != 96 or len(q07.get("micro_scenes", [])) != 96:
        raise Unit04MaterialPackageError("inventory_count_drift")
    if summary.get("episodes_with_grammar_refs") != 360 or summary.get("episodes_with_route_refs") != 360:
        raise Unit04MaterialPackageError("binding_coverage_drift")
    refs = [{"path": rel, "sha256": _sha(root / rel), "status": a[rel]["status"]} for rel in EXPECTED]
    payload = {
        "schema_version": "a1fs.v1.u04.material_package_baseline.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "unit_number": 4,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "baseline_role": "FIRST_COMPLETE_SUCCESSOR_HANDOFF_BASELINE_FROM_UNIT04_FORWARD",
        "scope": {"unit04_only": True, "unit01_03_asset_backfill": "DEFERRED", "unit05_started": False, "current360_regenerated": False, "a2_a2plus_unlocked": False},
        "inventory": {
            "grammar_target": q01.get("grammar_target"),
            "q03_relation_count": len(q03.get("relations", [])),
            "unit04_vocabulary_inventory_count": len(vocab),
            "unit04_material_chunk_surface_count": len(chunks),
            "unit04_new_exact_frame_count": len(q05.get("unit04_new_exact_frames", [])),
            "unit04_sentence_asset_count": len(q06.get("assets", [])),
            "unit04_scene_binding_count": len(q07.get("micro_scenes", [])),
            "current360_episode_count": len(episodes),
        },
        "binding_summary": summary,
        "source_refs": refs,
        "grammar": {
            "q01_scope": {"status": q01.get("status"), "grammar_target": q01.get("grammar_target"), "canonical_mapping": q01.get("canonical_mapping")},
            "q03_form_meaning": {"status": q03.get("status"), "form_contract": q03.get("form_contract"), "relations": q03.get("relations")},
        },
        "vocabulary": vocab,
        "chunks": chunks,
        "core_sentence_frames": frames,
        "sentence_assets": q06.get("assets", []),
        "scene_semantic_facts": q07.get("micro_scenes", []),
        "current360": episodes,
        "current360_asset_binding": bindings,
    }
    payload["payload_sha256"] = _digest(payload)
    return payload


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _zip(source, target):
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(x for x in source.rglob("*") if x.is_file()):
            info = zipfile.ZipInfo(p.relative_to(source).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = _sha(target)
    target.with_suffix(target.suffix + ".sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    return digest


def materialize_unit04_material_package(repo_root=None, output_root=None):
    root = _root(repo_root)
    p = build_unit04_material_package_baseline(root)
    out = Path(output_root).resolve() if output_root else root / "build" / "unit04_material_package"
    pkg = out / "Unit04_Material_Package"
    if pkg.exists():
        shutil.rmtree(pkg)
    for d in DIRS:
        (pkg / d).mkdir(parents=True, exist_ok=True)
    for rel in EXPECTED:
        shutil.copy2(root / rel, pkg / "01_AUTHORITY" / Path(rel).name)
    _write_json(pkg / "02_GRAMMAR" / "Unit04_Grammar_Authority.json", p["grammar"])
    _write_json(pkg / "03_VOCABULARY" / "Unit04_Vocabulary_Inventory.json", p["vocabulary"])
    _write_csv(pkg / "03_VOCABULARY" / "Unit04_Vocabulary_Inventory.csv", p["vocabulary"], ["asset_class", "surface", "domain", "authority_status", "level", "guideword", "yle_stage", "evp_level", "source"])
    _write_json(pkg / "04_CHUNKS" / "Unit04_Chunk_Inventory.json", p["chunks"])
    _write_csv(pkg / "04_CHUNKS" / "Unit04_Chunk_Inventory.csv", p["chunks"], ["authority_local_ref", "surface", "relation_surface", "relation_id", "role", "parent_canonical_chunk_id", "source"])
    _write_json(pkg / "05_SENTENCE_ASSETS" / "Unit04_Sentence_Assets_96.json", p["sentence_assets"])
    _write_csv(pkg / "05_SENTENCE_ASSETS" / "Unit04_Sentence_Assets_96.csv", p["sentence_assets"], ["sentence_id", "text", "relation_surface", "relation_id", "place_chunk_surface", "subject_np_surface", "subject_lemma", "pattern_id", "generation_role", "canonical_admission_status"])
    _write_json(pkg / "06_CORE_SENTENCES" / "Unit04_Core_Sentence_Frames.json", p["core_sentence_frames"])
    _write_json(pkg / "07_SCENE_SEMANTIC_FACTS" / "Unit04_Q07_Scene_Bindings_96.json", p["scene_semantic_facts"])
    _write_json(pkg / "08_CURRENT360" / "Unit04_Current360_Effective360.json", p["current360"])
    _write_csv(pkg / "08_CURRENT360" / "Unit04_Current360_Effective360.csv", p["current360"], ["episode_id", "micro_scene_id", "life_domain", "governed_scene_family", "discourse_family", "five_w_one_h", "target_relations", "support_language", "review_status", "source_fact_lineage", "boundary_action", "passage"])
    _write_json(pkg / "09_CURRENT360_ASSET_BINDING" / "Unit04_Current360_Asset_Binding.json", p["current360_asset_binding"])
    _write_json(pkg / "09_CURRENT360_ASSET_BINDING" / "Binding_Summary.json", p["binding_summary"])
    _write_json(pkg / "10_REFERENCE_LINEAGE" / "Source_Refs.json", p["source_refs"])
    manifest = {k: p[k] for k in ("schema_version", "task_id", "status", "revision", "unit_number", "unit_id", "baseline_role", "scope", "inventory", "binding_summary", "source_refs", "payload_sha256")}
    manifest["package_hash_policy"] = "ZIP_SHA256_IS_SIDECAR_ONLY_TO_AVOID_RECURSIVE_SELF_HASH"
    _write_json(pkg / "11_MANIFEST" / "Unit04_Material_Package_Manifest.json", manifest)
    target = out / "Unit04_Material_Package.zip"
    target.unlink(missing_ok=True)
    return {"status": STATUS, "package_root": str(pkg), "zip_path": str(target), "zip_sha256": _zip(pkg, target), "manifest": manifest}


def main():
    print(json.dumps(materialize_unit04_material_package(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
