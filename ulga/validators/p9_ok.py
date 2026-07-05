from __future__ import annotations


def check_ok(row):
    errors = []
    if row.get("schema_version") != "p9_ok.v1":
        errors.append("schema")
    if not row.get("qa_id"):
        errors.append("id")
    if row.get("q", 0) <= 0:
        errors.append("q")
    if row.get("q") != row.get("k"):
        errors.append("align")
    if row.get("local_only") is not True:
        errors.append("local")
    if row.get("public_ready") is not False:
        errors.append("public")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}
