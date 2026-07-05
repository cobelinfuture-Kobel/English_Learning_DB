from __future__ import annotations

import json

from tools.r2_local import json_refs, levels, resolve_ref, root, rows, shape

BAD = ("schema", "contract", "::", "page_unit[", "passage_unit[")


def ok_text(value):
    if not isinstance(value, str):
        return False
    text = value.strip()
    low = text.lower()
    if len(text) < 3:
        return False
    if "\\" in text or "/" in text or low.endswith((".json", ".pdf", ".mp3", ".txt")):
        return False
    if any(mark in low for mark in BAD) or low.startswith("raz_") or low.endswith((".v1", ".v2")):
        return False
    return " " in text or any(mark in text for mark in ".?!")


def texts(value, limit=5):
    out = []

    def add(item):
        if ok_text(item) and item.strip() not in out:
            out.append(item.strip())

    def walk(node):
        if len(out) >= limit:
            return
        if isinstance(node, dict):
            for child in node.values():
                if isinstance(child, str):
                    add(child)
                else:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return out[:limit]


def linked(base, value, limit=5):
    out = []
    for ref in json_refs(value):
        path = resolve_ref(base, ref)
        if not path:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for text in texts(data, limit=limit):
            if text not in out:
                out.append(text)
            if len(out) >= limit:
                return out
    return out


def prefer(row):
    return "bridge/reading_authority/" in row["path"].replace("\\", "/")


def pack(value=None, limit=10):
    base = root(value)
    items = []
    for row in rows(base, limit=limit):
        link = linked(base, row["data"], limit=3)
        direct = texts(row["data"], limit=3)
        picked = link if prefer(row) and link else direct or link
        q = " / ".join(picked) if picked else row["path"]
        items.append({"q": q[:240], "a": "review", "source": row["path"]})
    return {"root": str(base), "root_exists": base.exists(), "levels": levels(base), "items": items, "local_only": True, "read_only": True}


def probe(value=None, limit=5):
    base = root(value)
    return [
        {"path": row["path"], "shape": shape(row["data"]), "refs": json_refs(row["data"], limit=5), "texts": texts(row["data"]), "linked_texts": linked(base, row["data"])}
        for row in rows(base, limit=limit)
    ]
