from __future__ import annotations


def check_card(card):
    errors = []
    if card.get("schema_version") != "p8_card.v1":
        errors.append({"code": "P8_ERR_SCHEMA", "path": "schema_version"})
    if not card.get("page_id"):
        errors.append({"code": "P8_ERR_ID", "path": "page_id"})
    if not card.get("title"):
        errors.append({"code": "P8_ERR_TITLE", "path": "title"})
    if not card.get("items"):
        errors.append({"code": "P8_ERR_ITEMS", "path": "items"})
    if not card.get("keys"):
        errors.append({"code": "P8_ERR_KEYS", "path": "keys"})
    if card.get("local_only") is not True:
        errors.append({"code": "P8_ERR_LOCAL", "path": "local_only"})
    if card.get("public_ready") is not False:
        errors.append({"code": "P8_ERR_PUBLIC", "path": "public_ready"})
    return {"validator_status": "PASS" if not errors else "FAIL", "errors": errors}
