from __future__ import annotations
from typing import Any, Mapping
FORBIDDEN_PRIVATE_KEYS = {"private_sentence_bodies","private_sentence_fingerprints","unit01_sentence_texts","unit01_exact_hashes","unit01_normalized_hashes"}

def private_fields(value: Any, prefix: str="") -> list[str]:
    found=[]
    if isinstance(value, Mapping):
        for k,v in value.items():
            path=f"{prefix}.{k}" if prefix else str(k)
            if str(k) in FORBIDDEN_PRIVATE_KEYS: found.append(path)
            found.extend(private_fields(v,path))
    elif isinstance(value,list):
        for i,v in enumerate(value): found.extend(private_fields(v,f"{prefix}[{i}]") )
    return found
