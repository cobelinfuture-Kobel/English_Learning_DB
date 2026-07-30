#!/usr/bin/env python3
"""Validate RAZQ01D Unit01 content admission and Unit02 reusable handoff."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff as b

PASS_STATUS="PASS_A1FS_V1_RAZQ01D_UNIT01_CONTENT_ADMISSION_HANDOFF_VALIDATION"
class AdmissionValidationError(ValueError): pass
def fail(code: str)->None: raise AdmissionValidationError(code)

def validate_package(private: Mapping[str,Any], safe: Mapping[str,Any])->dict[str,Any]:
    if private.get("task_id")!=b.TASK_ID or private.get("status")!=b.PASS_STATUS: fail("identity_invalid")
    scope=private.get("scope") or {}
    if scope.get("allowed_units")!=[b.UNIT_ID] or scope.get("unit02_to_unit24_modified") is not False or scope.get("second_question_bank_created") is not False: fail("scope_invalid")
    raw={k:deepcopy(v) for k,v in private.items() if k!="package_sha256"}
    if private.get("package_sha256")!=b.digest(raw): fail("private_hash_invalid")
    raw_safe={k:deepcopy(v) for k,v in safe.items() if k!="readback_sha256"}
    if safe.get("readback_sha256")!=b.digest(raw_safe) or safe.get("private_package_sha256")!=private.get("package_sha256"): fail("safe_hash_invalid")
    assets=private.get("content_assets") or []; safe_assets=safe.get("content_assets") or []
    if not assets or len(assets)!=len(safe_assets): fail("assets_missing")
    if {a.get("content_kind") for a in assets}!=set(b.CONTENT_KINDS): fail("content_kinds_incomplete")
    ids=[a.get("content_asset_id") for a in assets]; sigs=[(a.get("scene_profile") or {}).get("distinct_scene_signature") for a in assets]
    if None in ids or len(ids)!=len(set(ids)) or None in sigs or len(sigs)!=len(set(sigs)): fail("identity_or_scene_duplicate")
    for a,s in zip(assets,safe_assets):
        if "content" in s or s.get("content_asset_id")!=a.get("content_asset_id"): fail("safe_content_leak")
        if a.get("content_sha256")!=b.digest(a.get("content") or {}): fail("content_hash_invalid")
        if (a.get("admission") or {}).get("template_only") is not False: fail("template_only_forbidden")
        reuse=a.get("later_unit_reuse") or {}; handoff=a.get("unit02_reusable_handoff") or {}
        if reuse.get("copy_on_reuse") is not False or reuse.get("reuse_identity_mode")!="REFERENCE_EXISTING_CONTENT_ASSET_ID": fail("reuse_contract_invalid")
        if handoff.get("target_unit_sequence")!=2 or handoff.get("binding_status")!="AVAILABLE_NOT_BOUND" or handoff.get("unit02_modified") is not False: fail("unit02_handoff_invalid")
        projections=a.get("skill_projections") or []
        if {p.get("skill") for p in projections}!=set(b.SKILLS): fail("three_skill_projection_invalid")
        for p in projections:
            if p.get("existing_question_bank_id")!=b.qb.BANK_ID or p.get("projection_mode")!="REFERENCE_EXISTING_FAMILY_IDS_NO_SECOND_BANK": fail("question_bank_projection_invalid")
            families=set(p.get("existing_family_ids") or [])
            if not families or not families.issubset(b.FAMILY_IDS): fail("question_bank_family_invalid")
        dlg=a.get("dialogue_profile") or {}
        if a.get("content_kind")=="SHORT_DIALOGUE":
            if dlg.get("is_real_dialogue") is not True or int(dlg.get("speaker_count") or 0)<2 or int(dlg.get("turn_count") or 0)<2 or dlg.get("role_play_supported") is not True: fail("dialogue_invalid")
        elif dlg.get("is_real_dialogue") is not False: fail("nondialogue_invalid")
    c=private.get("coverage_readback") or {}; count=len(assets)
    for key in ("approved_content_asset_count","reading_projection_count","writing_projection_count","speaking_projection_count","three_skill_shared_content_count","unit02_reusable_asset_count"):
        if c.get(key)!=count: fail(f"coverage_invalid:{key}")
    if c.get("template_only_content_count")!=0: fail("template_only_count_invalid")
    findings={(x.get("finding_code")) for x in (private.get("inspection_record") or {}).get("findings",[])}
    if findings!={code for code,_ in b.FINDINGS}: fail("inspection_findings_incomplete")
    bounds=private.get("boundaries") or {}
    if bounds.get("existing_question_bank_referenced") is not True or bounds.get("existing_question_bank_modified") is not False or bounds.get("parallel_question_bank_created") is not False or bounds.get("unit02_modified") is not False: fail("authority_boundary_invalid")
    return {"validation_status":PASS_STATUS,"content_asset_count":count,"content_kind_counts":{k:sum(a["content_kind"]==k for a in assets) for k in b.CONTENT_KINDS},"three_skill_shared_content_count":count,"unit02_reusable_asset_count":count,"private_package_sha256":private["package_sha256"],"safe_readback_sha256":safe["readback_sha256"]}
