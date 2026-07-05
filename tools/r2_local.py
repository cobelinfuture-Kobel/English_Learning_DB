from __future__ import annotations

import json
import os
from pathlib import Path

HOST = "127.0.0.1"
ENV = "RV1_RAZ_ROOT"
TEXT_KEYS = (
    "source_text",
    "text",
    "sentence",
    "question_text",
    "title",
    "book_title",
    "name",
)


def root(value=None):
    if value:
        return Path(value).expanduser().resolve()
    if os.environ.get(ENV):
        return Path(os.environ[ENV]).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "raz_output_jsons"


def levels(value=None):
    base = root(value)
    if not base.exists():
        return []
    return sorted({p.name for p in base.rglob("Level_*") if p.is_dir()})


def looks_like_path(text):
    lowered = text.lower()
    return "\\" in text or "/" in text or lowered.endswith((".json", ".pdf", ".mp3", ".txt"))


def looks_like_text(text):
    clean = text.strip()
    if len(clean) < 3 or looks_like_path(clean):
        return False
    if " " in clean:
        return True
    return any(mark in clean for mark in ".?!")


def extract_text(value, limit=8):
    found = []
    generic = []

    def add(value, target):
        if isinstance(value, str) and looks_like_text(value) and value not in target:
            target.append(value.strip())

    def walk(node):
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            for key in TEXT_KEYS:
                add(node.get(key), found)
                if len(found) >= limit:
                    return
            for child in node.values():
                if isinstance(child, str):
                    add(child, generic)
                else:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    merged = found + [item for item in generic if item not in found]
    return merged[:limit]


def json_refs(value, limit=20):
    found = []

    def add(text):
        if isinstance(text, str) and text.lower().endswith(".json") and text not in found:
            found.append(text)

    def walk(node):
        if len(found) >= limit:
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
    return found[:limit]


def resolve_ref(base, ref):
    rel = Path(ref.replace("\\", "/"))
    direct = base / rel
    if direct.is_file():
        return direct
    matches = list(base.rglob(rel.name))
    for path in matches:
        if str(path).replace("\\", "/").endswith(str(rel).replace("\\", "/")):
            return path
    return matches[0] if matches else None


def linked_texts(base, value, limit=5):
    out = []
    for ref in json_refs(value):
        path = resolve_ref(base, ref)
        if not path:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for text in extract_text(data, limit=limit):
            if text not in out:
                out.append(text)
            if len(out) >= limit:
                return out
    return out


def shape(value, limit=20):
    keys = []
    strings = []

    def add_key(key):
        if key not in keys and len(keys) < limit:
            keys.append(key)

    def add_string(text):
        if isinstance(text, str) and text not in strings and len(strings) < limit:
            strings.append(text[:160])

    def walk(node):
        if isinstance(node, dict):
            for key, child in node.items():
                add_key(str(key))
                if isinstance(child, str):
                    add_string(child)
                else:
                    walk(child)
        elif isinstance(node, list):
            for child in node[:10]:
                walk(child)

    walk(value)
    return {"keys": keys, "strings": strings}


def rows(value=None, limit=50):
    base = root(value)
    out = []
    if not base.exists():
        return out
    for path in sorted(base.rglob("*.json")):
        if len(out) >= limit:
            break
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, (dict, list)):
            out.append({"path": str(path.relative_to(base)), "data": data})
    return out


def probe(value=None, limit=5):
    base = root(value)
    out = []
    for row in rows(base, limit=limit):
        out.append({
            "path": row["path"],
            "shape": shape(row["data"]),
            "refs": json_refs(row["data"], limit=5),
            "texts": extract_text(row["data"], limit=5),
            "linked_texts": linked_texts(base, row["data"], limit=5),
        })
    return out


def pack(value=None, limit=10):
    base = root(value)
    items = []
    for row in rows(base, limit=limit):
        texts = extract_text(row["data"], limit=3)
        if not texts:
            texts = linked_texts(base, row["data"], limit=3)
        text = " / ".join(texts) if texts else row["path"]
        items.append({"q": str(text)[:240], "a": "review", "source": row["path"]})
    return {
        "root": str(base),
        "root_exists": base.exists(),
        "levels": levels(base),
        "items": items,
        "local_only": True,
        "read_only": True,
    }
