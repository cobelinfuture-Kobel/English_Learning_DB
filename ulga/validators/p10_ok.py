from __future__ import annotations


def check_ok(row):
    errors = []
    if row.get("schema_version") != "p10_ok.v1":
        errors.append("schema")
    if not row.get("release_id"):
        errors.append("id")
    if not row.get("guide"):
        errors.append("guide")
    if not row.get("sample"):
        errors.append("sample")
    if row.get("local_user") is not True:
        errors.append("user")
    if row.get("public_ready") is not False:
        errors.append("public")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}
