import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_JSON_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunks.json")
LEVEL_MAPPING_PATH = os.path.join(BASE_DIR, "chunk_profile", "json", "chunk_level_mapping.json")
REPORT_PATH = os.path.join(BASE_DIR, "chunk_profile", "reports", "chunk_extract_report.json")
VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
REQUIRED_FIELDS = {
    "id",
    "chunk",
    "normalized_chunk",
    "level",
    "chunk_type",
    "guideword",
    "topic",
    "details",
    "source",
    "source_file",
    "source_sheet",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_chunks_json_exists():
    assert os.path.exists(CHUNK_JSON_PATH), "chunks.json does not exist"


def test_chunks_json_is_valid_json():
    chunks = load_json(CHUNK_JSON_PATH)
    assert isinstance(chunks, list)


def test_every_item_has_required_fields():
    chunks = load_json(CHUNK_JSON_PATH)
    for item in chunks:
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"{item.get('id')} missing fields: {missing}"
        for field in ["id", "chunk", "level", "chunk_type", "source"]:
            assert item.get(field), f"{item.get('id')} has empty {field}"


def test_id_is_unique():
    chunks = load_json(CHUNK_JSON_PATH)
    ids = [item["id"] for item in chunks]
    assert len(ids) == len(set(ids))


def test_normalized_chunk_is_lowercase_and_trimmed():
    chunks = load_json(CHUNK_JSON_PATH)
    for item in chunks:
        normalized = item["normalized_chunk"]
        assert normalized == normalized.strip()
        assert normalized == normalized.lower()


def test_level_only_in_allowed_cefr_levels():
    chunks = load_json(CHUNK_JSON_PATH)
    for item in chunks:
        assert item["level"] in VALID_LEVELS


def test_chunk_type_is_not_empty():
    chunks = load_json(CHUNK_JSON_PATH)
    for item in chunks:
        assert item["chunk_type"]


def test_chunk_level_mapping_keys_contain_all_cefr_levels():
    mapping = load_json(LEVEL_MAPPING_PATH)
    assert VALID_LEVELS.issubset(set(mapping.keys()))


def test_report_verdict_is_not_fail():
    report = load_json(REPORT_PATH)
    assert report["verdict"] in {"PASS", "WARNING"}
