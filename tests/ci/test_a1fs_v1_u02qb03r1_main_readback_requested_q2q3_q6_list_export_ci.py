import base64
import json
import os
import zlib
from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02qb03r1_main_readback_requested_q2q3_q6_list_export as builder,
)
from ulga.validators.a1fs_v1_u02sa01r1_validation.privacy import private_fields

EXPORT_BRANCH = "a1fs-v1-u02qb03r1-main-readback-list-export"


@lru_cache(maxsize=1)
def _payload():
    return builder.build_export_payload()


def test_u02qb03r1_main_readback_and_requested_list_counts():
    payload = _payload()
    assert payload["status"] == builder.PASS_STATUS
    assert payload["main_readback"]["unit01_reference_item_count"] == 474
    assert payload["main_readback"]["unit02_approved_item_count"] == 994
    assert payload["main_readback"]["cumulative_catalog_item_count"] == 1468
    assert payload["main_readback"]["runtime_occurrence_count"] == 640
    assert payload["main_readback"]["q6_bound_runtime_occurrence_count"] == 128
    assert payload["main_readback"]["runtime_connected"] is True
    assert payload["q2_q3_vocabulary_morphology"]["row_count"] == 162
    assert payload["q6_sentence_assets"]["asset_count"] > 162


def test_u02qb03r1_export_is_complete_distinct_and_public_safe():
    payload = _payload()
    q2 = payload["q2_q3_vocabulary_morphology"]["rows"]
    q6 = payload["q6_sentence_assets"]["assets"]
    assert len(q2) == 162
    assert len({row["singular"].casefold() for row in q2}) == 162
    assert len(q6) == payload["q6_sentence_assets"]["asset_count"]
    assert len({row["sentence_id"] for row in q6}) == len(q6)
    assert len({row["normalized_text"] for row in q6}) == len(q6)
    assert private_fields(payload) == []
    assert payload["claim_boundaries"]["readback_only"] is True
    assert payload["claim_boundaries"]["canonical_content_created"] is False


def test_u02qb03r1_export_payload_roundtrip_and_emit_only_on_export_branch(capsys):
    payload = _payload()
    raw = builder.canonical(payload).encode("utf-8")
    compressed = zlib.compress(raw, 9)
    encoded = base64.b64encode(compressed).decode("ascii")
    restored = json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))
    assert restored == payload

    if os.environ.get("GITHUB_HEAD_REF") == EXPORT_BRANCH:
        with capsys.disabled():
            print("U02QB03R1_EXPORT_BEGIN")
            for index in range(0, len(encoded), 6000):
                ordinal = index // 6000
                print(f"U02QB03R1_EXPORT_CHUNK={ordinal:04d}:{encoded[index:index + 6000]}")
            print("U02QB03R1_EXPORT_END")
