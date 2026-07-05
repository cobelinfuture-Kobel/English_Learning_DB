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


def extract_text(value, limit=8):
    found = []

    def walk(node):
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            for key in TEXT_KEYS:
                item = node.get(key)
                if isinstance(item, str) and item.strip():
                    found.append(item.strip())
                    if len(found) >= limit:
                        return
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found


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


def pack(value=None, limit=10):
    base = root(value)
    items = []
    for row in rows(base, limit=limit):
        texts = extract_text(row["data"], limit=3)
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
