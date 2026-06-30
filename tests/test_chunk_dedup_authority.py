import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_JSON_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunks.json")
SURFACE_INDEX_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunk_surface_index.json")
DUPLICATE_GROUPS_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunk_duplicate_groups.json")
CANONICAL_CANDIDATES_PATH = os.path.join(
    BASE_DIR, "chunk_profile", "json", "chunk_canonical_candidates.json"
)
DEDUP_POLICY_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunk_dedup_policy.json")
REPORT_PATH = os.path.join(BASE_DIR, "chunk_profile", "reports", "chunk_dedup_authority_report.json")
LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_chunk_surface_index_exists_and_valid():
    assert os.path.exists(SURFACE_INDEX_PATH)
    assert isinstance(load_json(SURFACE_INDEX_PATH), dict)


def test_chunk_duplicate_groups_exists_and_valid():
    assert os.path.exists(DUPLICATE_GROUPS_PATH)
    assert isinstance(load_json(DUPLICATE_GROUPS_PATH), list)


def test_chunk_canonical_candidates_exists_and_valid():
    assert os.path.exists(CANONICAL_CANDIDATES_PATH)
    assert isinstance(load_json(CANONICAL_CANDIDATES_PATH), dict)


def test_chunk_dedup_policy_exists_and_valid():
    assert os.path.exists(DEDUP_POLICY_PATH)
    assert isinstance(load_json(DEDUP_POLICY_PATH), dict)


def test_chunk_dedup_authority_report_exists_and_valid():
    assert os.path.exists(REPORT_PATH)
    assert isinstance(load_json(REPORT_PATH), dict)


def test_surface_index_covers_all_chunk_ids_exactly_once():
    chunks = load_json(CHUNK_JSON_PATH)
    index = load_json(SURFACE_INDEX_PATH)
    indexed_ids = [chunk_id for ids in index.values() for chunk_id in ids]
    chunk_ids = [chunk["id"] for chunk in chunks]
    assert sorted(indexed_ids) == sorted(chunk_ids)
    assert len(indexed_ids) == len(set(indexed_ids))


def test_duplicate_groups_only_include_count_at_least_two():
    groups = load_json(DUPLICATE_GROUPS_PATH)
    for group in groups:
        assert group["count"] >= 2
        assert len(group["ids"]) == group["count"]


def test_every_duplicate_group_id_exists_in_chunks_json():
    chunks = load_json(CHUNK_JSON_PATH)
    valid_ids = {chunk["id"] for chunk in chunks}
    groups = load_json(DUPLICATE_GROUPS_PATH)
    for group in groups:
        assert set(group["ids"]).issubset(valid_ids)


def test_canonical_candidates_contains_every_normalized_chunk():
    chunks = load_json(CHUNK_JSON_PATH)
    candidates = load_json(CANONICAL_CANDIDATES_PATH)
    surfaces = {chunk["normalized_chunk"] for chunk in chunks}
    assert set(candidates.keys()) == surfaces


def test_every_canonical_recommended_id_exists_in_chunks_json():
    chunks = load_json(CHUNK_JSON_PATH)
    valid_ids = {chunk["id"] for chunk in chunks}
    candidates = load_json(CANONICAL_CANDIDATES_PATH)
    for candidate in candidates.values():
        assert set(candidate["recommended_ids"]).issubset(valid_ids)


def test_lowest_level_follows_cefr_ordering():
    candidates = load_json(CANONICAL_CANDIDATES_PATH)
    for candidate in candidates.values():
        levels = [level for level in candidate["levels"] if level is not None]
        expected = min(levels, key=LEVEL_ORDER.index) if levels else None
        assert candidate["lowest_level"] == expected


def test_dedup_policy_does_not_delete_duplicates():
    policy = load_json(DEDUP_POLICY_PATH)
    assert policy["rules"]["do_not_delete_duplicates"] is True


def test_report_verdict_is_not_fail():
    report = load_json(REPORT_PATH)
    assert report["verdict"] in {"PASS", "WARNING"}
