from __future__ import annotations

import base64
import hashlib
import json
import lzma
import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from .constants import *


class U02SA01R1BuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def normalize_surface(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", value).strip().casefold()


def normalize_sentence(value: str) -> str:
    value = normalize_surface(value)
    value = re.sub(r"\s+([,.!?;:])", r"\1", value)
    return re.sub(r"[.!?]+$", "", value).strip()


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def load_manifest(paths: tuple[Path, ...] = SAFE_MANIFEST_SHARD_PATHS) -> dict[str, Any]:
    compressed = b"".join(base64.b64decode(path.read_text(encoding="ascii")) for path in paths)
    value = json.loads(lzma.decompress(compressed).decode("utf-8"))
    claimed = value.get("manifest_sha256")
    core = {k: v for k, v in value.items() if k != "manifest_sha256"}
    if claimed != digest(core):
        raise U02SA01R1BuildError("SAFE_MANIFEST_DIGEST_INVALID")
    src = value.get("source_evidence", {})
    if src.get("cambridge_yle", {}).get("sha256") != CAMBRIDGE_YLE_SHA256:
        raise U02SA01R1BuildError("YLE_SOURCE_SHA_DRIFT")
    if src.get("unit01_sentence_pool", {}).get("sha256") != UNIT01_SENTENCE_POOL_SHA256:
        raise U02SA01R1BuildError("UNIT01_POOL_SHA_DRIFT")
    if src.get("unit01_defer", {}).get("sha256") != UNIT01_DEFER_SHA256:
        raise U02SA01R1BuildError("UNIT01_DEFER_SHA_DRIFT")
    return value


def load_vocabulary(path: Path = VOCABULARY_PATH) -> list[dict[str, Any]]:
    if git_blob_sha(path) != VOCABULARY_GIT_BLOB_SHA:
        raise U02SA01R1BuildError("CANONICAL_VOCABULARY_BLOB_DRIFT")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise U02SA01R1BuildError("CANONICAL_VOCABULARY_NOT_LIST")
    ids = [str(row.get("vocab_id") or "") for row in value]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise U02SA01R1BuildError("CANONICAL_VOCABULARY_IDENTITY_INVALID")
    return [dict(row) for row in value]


def _is_noun(row: Mapping[str, Any]) -> bool:
    return normalize_surface(row.get("part_of_speech") or "") == "noun"


def _active_level(row: Mapping[str, Any], level: str) -> bool:
    return row.get("active") is True and str(row.get("level") or "").upper() == level


def _last_lexical_head(surface: str) -> tuple[str, str, str] | None:
    matches = list(re.finditer(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?", surface))
    if not matches:
        return None
    m = matches[-1]
    return surface[:m.start()], m.group(0), surface[m.end():]


def plain_s_plural(surface: str) -> tuple[str | None, str]:
    normalized = normalize_surface(surface)
    head_info = _last_lexical_head(surface)
    if head_info is None:
        return None, "NO_LEXICAL_HEAD"
    prefix, head_raw, suffix = head_info
    head = normalize_surface(head_raw)
    if head in {"fish", "foot", "man", "sheep", "tooth", "woman", "person", "child", "mouse"}:
        return None, "IRREGULAR_PLURAL"
    if head.endswith(("s", "x", "z", "ch", "sh")):
        return None, "REQUIRES_ES_OR_ALREADY_PLURAL"
    if head.endswith("y") and len(head) > 1 and head[-2] not in "aeiou":
        return None, "REQUIRES_IES"
    if head.endswith(("f", "fe")):
        return None, "F_FE_REVIEW_REQUIRED"
    # O-endings are lexical: permit known simple +s forms, otherwise defer structurally.
    if head.endswith("o") and head not in {"photo", "piano", "radio", "video", "zoo"}:
        return None, "O_ENDING_REVIEW_REQUIRED"
    plural_head = head_raw + "s"
    return prefix + plural_head + suffix, "PLAIN_S_STRUCTURALLY_VALID"


