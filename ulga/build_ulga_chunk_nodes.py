import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE_DIR / "chunk_profile" / "json" / "chunks.json"
SAFE_CHUNKS_PATH = BASE_DIR / "chunk_profile" / "json" / "chunks_generator_safe.json"
EQUIVALENCE_GROUPS_PATH = BASE_DIR / "chunk_profile" / "json" / "chunk_equivalence_groups.json"
USAGE_CLASS_MAPPING_PATH = BASE_DIR / "chunk_profile" / "json" / "chunk_usage_class_mapping.json"
OUTPUT_DIR = BASE_DIR / "ulga" / "graph"
REPORT_DIR = BASE_DIR / "ulga" / "reports"
CHUNK_NODES_OUT_PATH = OUTPUT_DIR / "chunk_nodes.json"
GRAPH_CHUNK_NODES_OUT_PATH = OUTPUT_DIR / "ulga_graph.chunk_nodes.json"
SUMMARY_OUT_PATH = REPORT_DIR / "chunk_node_mount_summary.json"
DUPLICATES_OUT_PATH = REPORT_DIR / "chunk_node_duplicates.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    if not text:
        return ""
    value = unicodedata.normalize("NFKD", str(text))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = re.sub(r"[\s/]+", "_", value)
    value = re.sub(r"[^a-z0-9_.:-]", "", value)
    value = re.sub(r"_{2,}", "_", value)
    return value.strip("_")


def build_equivalence_indexes(equivalence_groups):
    by_canonical_id = {}
    by_member_id = {}
    for group in equivalence_groups:
        group_id = group.get("group_id")
        canonical_id = group.get("canonical_id")
        if canonical_id:
            by_canonical_id[canonical_id] = group
        for equivalent_id in group.get("equivalent_ids") or []:
            by_member_id[equivalent_id] = group_id
    return by_canonical_id, by_member_id


def build_raw_chunk_index(raw_chunks):
    return {record.get("id"): record for record in raw_chunks if record.get("id")}


def canonical_key_for_safe_chunk(record, duplicate_slug_counts):
    base_slug = slugify(record.get("normalized_chunk") or record.get("chunk"))
    if not base_slug:
        base_slug = slugify(record.get("safe_id") or record.get("canonical_chunk_id"))
    if duplicate_slug_counts[base_slug] == 1:
        return base_slug
    return f"{base_slug}:{slugify(record.get('safe_id'))}"


def make_node(record, raw_chunk_by_id, equivalence_by_canonical_id, equivalence_member_index, duplicate_slug_counts, generated_at):
    source_chunk_id = record.get("canonical_chunk_id")
    raw_record = raw_chunk_by_id.get(source_chunk_id, {})
    equivalence_group = equivalence_by_canonical_id.get(source_chunk_id)
    equivalent_group_id = None
    if equivalence_group:
        equivalent_group_id = equivalence_group.get("group_id")
    elif source_chunk_id:
        equivalent_group_id = equivalence_member_index.get(source_chunk_id)

    equivalent_ids = record.get("equivalent_ids") or []
    has_equivalence_merge = bool(equivalence_group) or len(equivalent_ids) > 1 or (record.get("raw_count") or 0) > 1
    canonical_chunk = canonical_key_for_safe_chunk(record, duplicate_slug_counts)
    node_id = f"chunk:{canonical_chunk}"

    confidence_value = 0.9 if has_equivalence_merge else 1.0
    confidence_notes = ["Mounted from canonical generator-safe chunk."]
    if has_equivalence_merge:
        confidence_notes.append("Canonical chunk represents an equivalence merge.")

    metadata = {
        "source_chunk_id": source_chunk_id,
        "canonical_chunk": canonical_chunk,
        "normalized_chunk": record.get("normalized_chunk"),
        "safe_chunk_id": record.get("safe_id"),
        "equivalent_group_id": equivalent_group_id,
        "equivalent_ids": equivalent_ids,
        "chunk_type": record.get("chunk_type"),
        "usage_class": record.get("usage_class"),
        "theme_hint": record.get("theme_hint") or [],
        "priority_band": record.get("priority_band"),
        "frequency_proxy_score": record.get("frequency_proxy_score"),
        "generator_allowed": record.get("generator_allowed"),
        "validator_accepts_equivalents": record.get("validator_accepts_equivalents"),
        "safe_layer_source": record.get("source"),
        "is_canonical": record.get("is_canonical"),
        "source_file": raw_record.get("source_file") or record.get("source_file"),
        "mounting_stage": "ULGA-S6B",
        "raw_count": record.get("raw_count"),
        "guideword": record.get("guideword"),
        "topic": record.get("topic"),
    }

    return {
        "id": node_id,
        "node_type": "chunk",
        "label": record.get("chunk") or record.get("normalized_chunk") or canonical_chunk,
        "cefr_level": record.get("level"),
        "authority_source": {
            "source_name": "EVP Chunk Generator Safe Layer",
            "source_file": "chunk_profile/json/chunks_generator_safe.json",
            "source_record_id": record.get("safe_id"),
            "derivation": "derived_safe_layer",
        },
        "confidence": {
            "value": confidence_value,
            "method": "authority_mount",
            "notes": confidence_notes,
        },
        "version": {
            "contract": "ULGA-S2",
            "source_version": "1.0.0",
            "generated_at": generated_at,
        },
        "metadata": metadata,
    }


def build_duplicate_report(safe_chunks):
    by_normalized_slug = defaultdict(list)
    for record in safe_chunks:
        normalized_slug = slugify(record.get("normalized_chunk") or record.get("chunk"))
        by_normalized_slug[normalized_slug].append(
            {
                "safe_id": record.get("safe_id"),
                "canonical_chunk_id": record.get("canonical_chunk_id"),
                "chunk": record.get("chunk"),
                "normalized_chunk": record.get("normalized_chunk"),
                "level": record.get("level"),
                "guideword": record.get("guideword"),
                "topic": record.get("topic"),
                "usage_class": record.get("usage_class"),
            }
        )

    duplicate_normalized_chunks = {
        slug: records for slug, records in sorted(by_normalized_slug.items()) if len(records) > 1
    }
    return {
        "duplicate_normalized_chunk_count": len(duplicate_normalized_chunks),
        "duplicate_safe_records_count": sum(len(records) for records in duplicate_normalized_chunks.values()),
        "duplicate_normalized_chunks": duplicate_normalized_chunks,
        "policy": (
            "Repeated normalized chunks are preserved as separate ChunkNodes when they represent distinct safe "
            "records or EVP senses. The generated canonical_chunk appends safe_chunk_id only for colliding slugs."
        ),
    }


def main():
    print("Loading chunk authority data...")
    raw_chunks = load_json(CHUNKS_PATH)
    safe_chunks = load_json(SAFE_CHUNKS_PATH)
    equivalence_groups = load_json(EQUIVALENCE_GROUPS_PATH)
    usage_mapping = load_json(USAGE_CLASS_MAPPING_PATH)

    print(f"Loaded {len(raw_chunks)} raw chunks.")
    print(f"Loaded {len(safe_chunks)} generator-safe chunks.")
    print(f"Loaded {len(equivalence_groups)} equivalence groups.")
    print(f"Loaded {len(usage_mapping)} usage class mappings.")

    raw_chunk_by_id = build_raw_chunk_index(raw_chunks)
    equivalence_by_canonical_id, equivalence_member_index = build_equivalence_indexes(equivalence_groups)
    duplicate_slug_counts = Counter(slugify(record.get("normalized_chunk") or record.get("chunk")) for record in safe_chunks)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    nodes = [
        make_node(
            record,
            raw_chunk_by_id,
            equivalence_by_canonical_id,
            equivalence_member_index,
            duplicate_slug_counts,
            generated_at,
        )
        for record in safe_chunks
    ]

    graph = {
        "graph_id": "ulga_graph.chunk_nodes",
        "contract_version": "ULGA-S2",
        "schema_version": "1.0.0",
        "formal_data_mounted": True,
        "mounted_stage": "ULGA-S6B",
        "nodes": nodes,
        "edges": [],
        "node_count": len(nodes),
        "chunk_node_count": len(nodes),
        "edge_count": 0,
        "chunk_vocabulary_linkage": False,
        "chunk_theme_projection": False,
        "chunk_grammar_metadata": False,
        "chunk_morphology_linkage": False,
        "chunk_chunk_linkage": False,
        "metadata": {
            "purpose": "ULGA-S6B chunk node mounting fix",
            "data_policy": "chunk_nodes_only",
            "source_chunk_count": len(raw_chunks),
            "safe_chunk_count": len(safe_chunks),
            "equivalence_group_count": len(equivalence_groups),
        },
        "validation_status": "untested",
    }

    duplicate_report = build_duplicate_report(safe_chunks)
    summary = {
        "mounting_stage": "ULGA-S6B",
        "source_chunk_count": len(raw_chunks),
        "safe_chunk_count": len(safe_chunks),
        "canonical_chunk_count": len(nodes),
        "equivalence_group_count": len(equivalence_groups),
        "mounted_chunk_node_count": len(nodes),
        "raw_to_mounted_reduction_count": len(raw_chunks) - len(nodes),
        "raw_to_mounted_reduction_ratio": round((len(raw_chunks) - len(nodes)) / len(raw_chunks), 6) if raw_chunks else 0,
        "equivalence_merged_node_count": sum(1 for node in nodes if node["confidence"]["value"] == 0.9),
        "generator_allowed_count": sum(1 for node in nodes if node["metadata"].get("generator_allowed") is True),
        "validator_accepts_equivalents_count": sum(
            1 for node in nodes if node["metadata"].get("validator_accepts_equivalents") is True
        ),
        "edge_count": 0,
        "duplicate_normalized_chunk_count": duplicate_report["duplicate_normalized_chunk_count"],
        "duplicate_safe_records_count": duplicate_report["duplicate_safe_records_count"],
    }

    write_json(CHUNK_NODES_OUT_PATH, nodes)
    write_json(GRAPH_CHUNK_NODES_OUT_PATH, graph)
    write_json(SUMMARY_OUT_PATH, summary)
    write_json(DUPLICATES_OUT_PATH, duplicate_report)

    print(f"Wrote {len(nodes)} chunk nodes to {CHUNK_NODES_OUT_PATH}")
    print(f"Wrote chunk graph wrapper to {GRAPH_CHUNK_NODES_OUT_PATH}")
    print(f"Wrote chunk mount summary to {SUMMARY_OUT_PATH}")
    print(f"Wrote duplicate report to {DUPLICATES_OUT_PATH}")
    print("Mounting complete.")


if __name__ == "__main__":
    main()
