from __future__ import annotations
from typing import Any, Mapping
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders.a1fs_v1_u02sa01r1.constants import DECISION_REF
from ulga.builders.a1fs_v1_u02sa01r1.engine import digest
from ulga.validators.a1fs_v1_u02sa01r1_validation.payload import validate_payload
from ulga.validators.a1fs_v1_u02sa01r1_validation.privacy import private_fields as _private_fields
VALIDATOR_ID = "validate_a1fs_v1_u02sa01r1_dynamic_authority_sentence_production_v2"

def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors=[]
    try: policy_artifact.verify_artifact_digest(candidate)
    except Exception as exc: errors.append(f"CANDIDATE_DIGEST:{exc}")
    if candidate.get("artifact_role")!="CANDIDATE_JSON": errors.append("CANDIDATE_ROLE_INVALID")
    errors.extend(validate_payload(candidate.get("payload",{})))
    core={"validator_id":VALIDATOR_ID,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors,"candidate_artifact_sha256":candidate.get("artifact_sha256")}
    if errors: raise ValueError(";".join(errors))
    return {"validator_id":VALIDATOR_ID,"status":"PASS","receipt_sha256":digest(core)}

def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors=[]
    try: policy_artifact.verify_artifact_digest(candidate); policy_artifact.verify_artifact_digest(approved)
    except Exception as exc: errors.append(f"ARTIFACT_DIGEST:{exc}")
    if approved.get("artifact_role")!="APPROVED_CANONICAL_JSON": errors.append("APPROVED_ROLE_INVALID")
    if approved.get("admission",{}).get("decision_ref")!=DECISION_REF: errors.append("DECISION_REF_INVALID")
    if approved.get("payload")!=candidate.get("payload"): errors.append("APPROVED_PAYLOAD_DRIFT")
    errors.extend(validate_payload(approved.get("payload",{})))
    return {"validator_id":VALIDATOR_ID,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors}
