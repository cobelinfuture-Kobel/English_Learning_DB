#!/usr/bin/env python3
"""Admit Unit01 RAZ-grounded scene assets and project them to the existing three-skill bank."""
from __future__ import annotations
import argparse, hashlib, json, os, re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as upstream
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as qb

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01D_Unit01MicroScenePassageDialogueAdmission_ThreeSkillProjectionAndUnit02ReusableHandoff"
SCHEMA_VERSION = "a1fs.v1.razq01d.unit01_content_admission_handoff.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_UNIT01_CONTENT_ADMISSION_HANDOFF"
UNIT_ID, UNIT_SEQUENCE, TARGET_UNIT02_SEQUENCE = upstream.UNIT_ID, 1, 2
APPROVED_CONTRACT_SHA256 = upstream.APPROVED_CONTRACT_SHA256
DECISION_REF = "OPERATOR_APPROVAL:2026-07-30:RAZQ01D"
INSPECTION_REF = "OPERATOR_HANDSHAKE:2026-07-30:UNIT01_SCENE_THREE_SKILL"
OUTPUT_PRIVATE = Path("ulga/private/a1fs_v1_razq01d_unit01_admitted_content.private.json")
OUTPUT_SAFE = Path("ulga/reports/a1fs_v1_razq01d_unit01_admission_handoff_readback.json")
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01D_LocalPrivateAdmissionMaterializationAndCoverageRecheck"
CONTENT_KINDS = ("MICRO_SCENE", "SHORT_PASSAGE", "SHORT_DIALOGUE")
SKILLS = ("READING", "WRITING", "SPEAKING")
REVIEW_DIMENSIONS = ("GRAMMAR_SAFETY","VOCABULARY_SAFETY","SEMANTIC_NATURALNESS","A1_ANSWERABILITY","SCENE_DISTINCTNESS","THREE_SKILL_AFFORDANCE")
FUTURE_ROLES = ("PREREQUISITE","CARRY_OVER","RECOMBINATION","TRANSFER","SCHEDULED_REVIEW","REMEDIATION","ASSESSMENT_SUPPORT")
REUSE_GATES = ("PREREQUISITE_UNLOCKED","LEVEL_SCOPE_ALLOWED","NEW_GRAMMAR_COMPATIBILITY_PASS","NO_UNINTRODUCED_GRAMMAR","SEMANTIC_COMPATIBILITY_PASS","SCENE_DEDUPLICATION_PASS","REUSE_REASON_RECORDED")
FAMILY_IDS = frozenset(str(row[0]) for row in qb.FAMILIES)
FAMILY_MAP = {
    "READING": ("U01-PF04-FIRST-MENTION-CONTEXT","U01-PF05-KNOWN-REFERENCE-CONTEXT","U01-PF08-TRANSFER-FIRST-MENTION"),
    "WRITING": ("U01-PF07-WORD-ORDER","U01-PF09-TRANSFER-KNOWN-REFERENCE"),
    "SPEAKING": ("U01-PF10-SPEAK-NOUN",),
}
FINDINGS = (
    ("FIXED_CONTEXT_COUNT_TOO_LOW","U01QB01 contains exactly five hard-coded context labels."),
    ("RAZQ01C_NOT_CONSUMED_BY_U01QB01","U01QB01 does not import or consume RAZQ01C."),
    ("U01E_SHORT_TEXT_THREE_SKILL_PRESENT","Existing U01E short texts feed Reading, Writing and Speaking."),
    ("U01QB01_FULL_TEXT_THREE_SKILL_NOT_PRESENT","The 288-item pool uses labels rather than shared passage assets."),
    ("FUNCTIONAL_DIALOGUE_LABEL_WITHOUT_TURN_STRUCTURE","The existing toy-shop context has no speaker turns."),
)
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.I)

class AdmissionBuildError(ValueError): pass

def canonical(v: Any) -> str: return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":"))
def digest(v: Any) -> str: return hashlib.sha256(canonical(v).encode()).hexdigest()
def norm(v: Any) -> str:
    if isinstance(v, Mapping): return " ".join(norm(x) for x in v.values())
    if isinstance(v, list): return " ".join(norm(x) for x in v)
    return " ".join(WORD_RE.findall(str(v).casefold().replace("’","'")))
def load(path: Path) -> dict[str, Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise AdmissionBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value,dict): raise AdmissionBuildError(f"OBJECT_REQUIRED:{path}")
    return value
def write(path: Path, value: Mapping[str,Any], private: bool=False) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(dict(value),ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,path)
    if private:
        try: path.chmod(0o600)
        except OSError: pass

def validate_upstream(report: Mapping[str,Any]) -> list[dict[str,Any]]:
    scope=report.get("scope") or {}
    if report.get("task_id")!=upstream.TASK_ID or report.get("status")!=upstream.PASS_STATUS: raise AdmissionBuildError("RAZQ01C_IDENTITY_INVALID")
    if scope.get("allowed_units")!=[UNIT_ID] or scope.get("canonical_promotion") is not False or scope.get("a2_status")!="LOCKED": raise AdmissionBuildError("RAZQ01C_SCOPE_INVALID")
    rows=report.get("selected_candidates")
    if not isinstance(rows,list) or not rows: raise AdmissionBuildError("RAZQ01C_SELECTED_CANDIDATES_REQUIRED")
    ids=[str(r.get("source_record_id") or "") for r in rows]
    if "" in ids or len(ids)!=len(set(ids)): raise AdmissionBuildError("RAZQ01C_SOURCE_ID_INVALID")
    return deepcopy(rows)

def validate_decision(d: Mapping[str,Any], c: Mapping[str,Any]) -> None:
    if d.get("source_record_id")!=c.get("source_record_id") or d.get("semantic_identity")!=c.get("semantic_identity"): raise AdmissionBuildError("DECISION_IDENTITY_MISMATCH")
    if d.get("decision_ref")!=DECISION_REF or d.get("review_status") not in {"APPROVED","REJECTED"}: raise AdmissionBuildError("DECISION_STATUS_OR_REF_INVALID")
    checks=d.get("review_dimensions") or {}
    if set(checks)!=set(REVIEW_DIMENSIONS): raise AdmissionBuildError("REVIEW_DIMENSIONS_INCOMPLETE")
    if d["review_status"]=="APPROVED":
        if c.get("selection_class")=="REJECT" or d.get("content_kind") not in CONTENT_KINDS: raise AdmissionBuildError("APPROVAL_KIND_INVALID")
        if any(checks[k]!="PASS" for k in REVIEW_DIMENSIONS) or d.get("template_only") is not False: raise AdmissionBuildError("APPROVAL_GATES_NOT_PASS")
    elif not d.get("rejection_reason_codes"): raise AdmissionBuildError("REJECTION_REASON_REQUIRED")

def content_parts(d: Mapping[str,Any]) -> tuple[list[str],list[dict[str,str]]]:
    kind=str(d["content_kind"]); sentences=[str(x).strip() for x in d.get("adapted_sentences") or [] if str(x).strip()]
    turns=[{"speaker_id":str(x.get("speaker_id") or ""),"utterance":str(x.get("utterance") or "").strip()} for x in d.get("dialogue_turns") or [] if isinstance(x,Mapping)]
    if kind=="MICRO_SCENE" and not (1<=len(sentences)<=3 and not turns): raise AdmissionBuildError("MICRO_SCENE_STRUCTURE_INVALID")
    if kind=="SHORT_PASSAGE" and not (2<=len(sentences)<=6 and not turns): raise AdmissionBuildError("SHORT_PASSAGE_STRUCTURE_INVALID")
    if kind=="SHORT_DIALOGUE":
        speakers={x["speaker_id"] for x in turns if x["speaker_id"]}
        if sentences or not 2<=len(turns)<=6 or len(speakers)<2 or any(not x["speaker_id"] or not x["utterance"] for x in turns): raise AdmissionBuildError("SHORT_DIALOGUE_STRUCTURE_INVALID")
    return sentences,turns

def asset_id(kind: str, semantic: str) -> str:
    prefix={"MICRO_SCENE":"MS","SHORT_PASSAGE":"SP","SHORT_DIALOGUE":"DLG"}[kind]
    return f"U01-{prefix}-{hashlib.sha256(f'{kind}|{semantic}'.encode()).hexdigest()[:12].upper()}"

def patterns(c: Mapping[str,Any]) -> list[str]:
    out={qb.PATTERN_NOUN}
    if c.get("active_adjective_hits") or c.get("adjective_noun_phrases"): out.add(qb.PATTERN_ADJECTIVE)
    if c.get("very_adjective_noun_phrases"): out.add(qb.PATTERN_VERY)
    return sorted(out)

def build_asset(c: Mapping[str,Any], d: Mapping[str,Any], contract: Mapping[str,Any]) -> dict[str,Any]:
    sentences,turns=content_parts(d); raw=str(c.get("text_excerpt") or "")
    if not norm(sentences or turns) or norm(sentences or turns)==norm(raw): raise AdmissionBuildError("RAW_RAZ_TEXT_COPY_OR_EMPTY_ADAPTATION")
    scene=deepcopy(d.get("scene_profile") or {})
    required={"setting","participants","objects","actions","information_structure","communicative_function_ids"}
    if set(scene)!=required: raise AdmissionBuildError("SCENE_PROFILE_FIELDS_INVALID")
    scene["distinct_scene_signature"]=digest(scene)
    kind=str(d["content_kind"]); aid=asset_id(kind,str(c["semantic_identity"])); pats=patterns(c)
    vocab_rows=list(contract["vocabulary_contract"]["active_vocabulary"])+list(contract["vocabulary_contract"]["active_adjectives"])
    wanted=set(c.get("active_noun_hits") or [])|set(c.get("active_adjective_hits") or [])
    vocab_ids=sorted(str(r["evp_sense_id"]) for r in vocab_rows if r["lemma"] in wanted)
    projections=[]
    for skill in SKILLS:
        families=list(FAMILY_MAP[skill])
        if skill=="SPEAKING" and qb.PATTERN_ADJECTIVE in pats: families.append("U01-PF11-SPEAK-ADJ-NOUN")
        if skill=="SPEAKING" and qb.PATTERN_VERY in pats: families.append("U01-PF12-SPEAK-VERY-ADJ-NOUN")
        if not set(families).issubset(FAMILY_IDS): raise AdmissionBuildError("QUESTION_BANK_FAMILY_MISSING")
        projections.append({"projection_id":f"{aid}-{skill}","content_asset_id":aid,"skill":skill,"existing_question_bank_id":qb.BANK_ID,"existing_question_bank_version":qb.BANK_VERSION,"existing_family_ids":sorted(families),"projection_mode":"REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK","projection_status":"READY_FOR_EXISTING_QB_MATERIALIZATION","task_modes":(["SHORT_TEXT_DETAIL","ARTICLE_REFERENCE"] if skill=="READING" else ["GUIDED_SENTENCE","CONTEXTUAL_WRITING"] if skill=="WRITING" else ["ROLE_PLAY","ORAL_RETELL"] if kind=="SHORT_DIALOGUE" else ["ORAL_RETELL"])})
    payload={"sentences":sentences,"dialogue_turns":turns}
    speakers=sorted({x["speaker_id"] for x in turns})
    return {
        "content_asset_id":aid,"content_kind":kind,"title":str(d.get("title") or aid),"introduced_unit_id":UNIT_ID,"introduced_unit_sequence":1,
        "source_lineage":{"source_authority":"RAZ_READING_AUTHORITY","source_record_id":str(c["source_record_id"]),"semantic_identity":str(c["semantic_identity"]),"source_level":c.get("source_level"),"source_type":c.get("source_type"),"original_excerpt_sha256":hashlib.sha256(raw.encode()).hexdigest(),"original_excerpt_private":True,"adaptation_mode":str(d.get("adaptation_mode") or ""),"adaptation_reason_codes":sorted(str(x) for x in d.get("adaptation_reason_codes") or []),"derived_from_task_id":upstream.TASK_ID},
        "content":payload,"content_sha256":digest(payload),
        "target_alignment":{"grammar_target_ids":pats,"egp_row_ids":sorted(list(contract["grammar_contract"]["core_focus_egp_row_ids"])+list(contract["grammar_contract"]["guided_extension_egp_row_ids"])),"vocabulary_asset_ids":vocab_ids,"chunk_asset_ids":[],"sentence_frame_ids":sorted(str(x) for x in c.get("matched_sentence_frame_ids") or []),"theme_id":d.get("theme_id"),"situation_family_id":d.get("situation_family_id"),"micro_situation_id":d.get("micro_situation_id"),"communicative_function_ids":sorted(str(x) for x in scene["communicative_function_ids"])},
        "scene_profile":scene,
        "dialogue_profile":{"is_real_dialogue":kind=="SHORT_DIALOGUE","speaker_count":len(speakers),"turn_count":len(turns),"speaker_ids":speakers,"adjacency_pair_types":sorted(str(x) for x in d.get("adjacency_pair_types") or []),"role_play_supported":kind=="SHORT_DIALOGUE"},
        "skill_projections":projections,
        "admission":{"review_status":"APPROVED","decision_ref":DECISION_REF,"review_dimensions":deepcopy(d["review_dimensions"]),"selection_class":c["selection_class"],"selection_reasons":deepcopy(c.get("selection_reasons") or []),"canonical_admission":True,"template_only":False},
        "later_unit_reuse":{"reusable_in_later_units":True,"reuse_identity_mode":"REFERENCE_EXISTING_CONTENT_ASSET_ID","copy_on_reuse":False,"eligible_future_unit_roles":list(FUTURE_ROLES),"reuse_gates":list(REUSE_GATES)},
        "unit02_reusable_handoff":{"target_unit_sequence":2,"source_content_asset_id":aid,"candidate_role":"CARRY_OVER","binding_status":"AVAILABLE_NOT_BOUND","unit02_modified":False,"required_when_bound":["target_unit_id","target_unit_role","new_grammar_target_ids","reuse_reason","compatibility_gate_status"]},
    }

def safe_asset(a: Mapping[str,Any]) -> dict[str,Any]:
    out=deepcopy(dict(a)); out.pop("content",None); return out

def build_admission(selection_report: Mapping[str,Any], decisions: Mapping[str,Any], contract: Mapping[str,Any]|None=None) -> tuple[dict[str,Any],dict[str,Any]]:
    contract=deepcopy(dict(contract or contract_builder.build_contract())); contract_builder.verify_contract_digest(contract)
    if contract.get("contract_sha256")!=APPROVED_CONTRACT_SHA256: raise AdmissionBuildError("UNIT01_CONTRACT_DIGEST_INVALID")
    candidates=validate_upstream(selection_report); reviewable=[r for r in candidates if r.get("selection_class")!="REJECT"]
    rows=decisions.get("decisions")
    if not isinstance(rows,list): raise AdmissionBuildError("DECISIONS_ARRAY_REQUIRED")
    by_id={str(r.get("source_record_id") or ""):r for r in rows if isinstance(r,Mapping)}
    if "" in by_id or len(by_id)!=len(rows) or set(by_id)!={str(r["source_record_id"]) for r in reviewable}: raise AdmissionBuildError("COMPLETE_REVIEWABLE_CANDIDATE_DECISIONS_REQUIRED")
    assets=[]; ledger=[]
    for c in reviewable:
        d=by_id[str(c["source_record_id"])]; validate_decision(d,c)
        ledger.append({"source_record_id":c["source_record_id"],"semantic_identity":c["semantic_identity"],"review_status":d["review_status"],"decision_ref":d["decision_ref"],"content_kind":d.get("content_kind"),"rejection_reason_codes":sorted(str(x) for x in d.get("rejection_reason_codes") or [])})
        if d["review_status"]=="APPROVED": assets.append(build_asset(c,d,contract))
    kinds=Counter(a["content_kind"] for a in assets)
    if not assets or any(kinds[k]<1 for k in CONTENT_KINDS): raise AdmissionBuildError("ALL_CONTENT_KINDS_REQUIRED_FOR_ACCEPTANCE")
    signatures=[a["scene_profile"]["distinct_scene_signature"] for a in assets]
    if len(signatures)!=len(set(signatures)): raise AdmissionBuildError("SCENE_SIGNATURE_DUPLICATE")
    core={
        "schema_version":SCHEMA_VERSION,"program_id":PROGRAM_ID,"task_id":TASK_ID,"status":PASS_STATUS,
        "scope":{"allowed_units":[UNIT_ID],"unit02_to_unit24_modified":False,"a2_status":"LOCKED","listening_status":"DEFERRED","second_question_bank_created":False,"raw_raz_text_learner_facing_copy_allowed":False},
        "inputs":{"upstream_task_id":upstream.TASK_ID,"approved_contract_sha256":APPROVED_CONTRACT_SHA256,"existing_question_bank_id":qb.BANK_ID,"existing_question_bank_version":qb.BANK_VERSION,"decision_ref":DECISION_REF},
        "inspection_record":{"inspection_ref":INSPECTION_REF,"findings":[{"finding_code":c,"observed_status":"CONFIRMED","evidence":e} for c,e in FINDINGS],"resolution":"ADMIT_RAZ_GROUNDED_CONTENT_AND_REFERENCE_EXISTING_THREE_SKILL_QB","unit02_reuse_fields_recorded":True},
        "review_ledger":ledger,"content_assets":assets,
        "coverage_readback":{"reviewable_candidate_count":len(reviewable),"approved_content_asset_count":len(assets),"rejected_candidate_count":sum(r["review_status"]=="REJECTED" for r in ledger),"distinct_micro_scene_count":kinds["MICRO_SCENE"],"distinct_short_passage_count":kinds["SHORT_PASSAGE"],"distinct_dialogue_count":kinds["SHORT_DIALOGUE"],"raz_grounded_content_count":len(assets),"project_authored_rewrite_count":sum(a["source_lineage"]["adaptation_mode"]=="PROJECT_AUTHORED_REWRITE" for a in assets),"reading_projection_count":len(assets),"writing_projection_count":len(assets),"speaking_projection_count":len(assets),"three_skill_shared_content_count":len(assets),"template_only_content_count":0,"unit02_reusable_asset_count":len(assets)},
        "boundaries":{"existing_question_bank_referenced":True,"existing_question_bank_modified":False,"parallel_question_bank_created":False,"unit02_modified":False,"audio_enabled":False,"speaking_capture_enabled":False,"mastery_claimed":False},
        "next_short_step":NEXT_SHORT_STEP,
    }
    core["package_sha256"]=digest(core)
    safe=deepcopy(core); safe["content_assets"]=[safe_asset(a) for a in assets]; safe["private_package_sha256"]=core["package_sha256"]; safe.pop("package_sha256")
    safe["readback_sha256"]=digest(safe)
    return core,safe

def run(selection_report_path: Path, decisions_path: Path, private_output_path: Path=OUTPUT_PRIVATE, safe_output_path: Path=OUTPUT_SAFE) -> tuple[dict[str,Any],dict[str,Any]]:
    private,safe=build_admission(load(selection_report_path),load(decisions_path)); write(private_output_path,private,True); write(safe_output_path,safe); return private,safe

def main(argv: Sequence[str]|None=None) -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--selection-report",type=Path,required=True); p.add_argument("--decisions",type=Path,required=True); p.add_argument("--private-output",type=Path,default=OUTPUT_PRIVATE); p.add_argument("--safe-output",type=Path,default=OUTPUT_SAFE); a=p.parse_args(argv)
    try: private,safe=run(a.selection_report.resolve(),a.decisions.resolve(),a.private_output.resolve(),a.safe_output.resolve())
    except (AdmissionBuildError,ValueError,KeyError,TypeError) as exc: print("STATUS=FAIL_A1FS_V1_RAZQ01D"); print(f"ERROR={exc}"); return 1
    c=safe["coverage_readback"]; print(f"STATUS={private['status']}"); print(f"APPROVED_CONTENT_ASSETS={c['approved_content_asset_count']}"); print(f"THREE_SKILL_SHARED={c['three_skill_shared_content_count']}"); print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}"); return 0
if __name__=="__main__": raise SystemExit(main())
