from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population
from ulga.builders import build_a1fs_v1_r5_production_bootstrap_first_session as bootstrap
from ulga.validators.validate_a1fs_v1_r5_production_bootstrap_first_session import validate

REPO_ROOT = Path(__file__).resolve().parents[2]


def _population_fixture(tmp_path: Path):
    path = REPO_ROOT / "tests/ulga/test_a1fs_v1_r3r4_authority_reviewed_production_population.py"
    spec = importlib.util.spec_from_file_location("r3r4_population_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._fixture(tmp_path)


def _bootstrap(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(bootstrap, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, source_consumer = _population_fixture(tmp_path)
    consumer = tmp_path / ".local/m2/consumer.json"
    consumer.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_consumer, consumer)
    database = tmp_path / ".local/m3/learner.sqlite3"
    m3.LearnerStateStore(database).initialize(consumer)
    output = tmp_path / ".local/r5_bootstrap"
    report = bootstrap.bootstrap(
        database_path=database,
        ontology_path=ontology,
        graph_path=graph,
        output_root=output,
        learner_id="learner-anonymous-01",
        display_label="A1 Learner",
        purpose="CORE_PRACTICE",
        planned_item_count=1,
        consumer_search_root=tmp_path / ".local",
        reviewed_at="2026-07-19T03:00:00Z",
        port=8876,
    )
    return ontology, graph, consumer, database, output, report


def test_bootstrap_discovers_hash_bound_consumer_and_starts_safe_session(tmp_path: Path, monkeypatch) -> None:
    ontology, graph, consumer, database, output, report = _bootstrap(tmp_path, monkeypatch)
    assert report["validation_status"] == bootstrap.STATUS
    assert report["profile_created"] is True
    assert report["session"]["session_state"] == "ACTIVE"
    assert report["session"]["assignment_count"] == 1
    assert report["stop_reason"] == "REAL_LEARNER_SESSION_EXECUTION_REQUIRED"
    bootstrap.safe_scan(report)

    private = json.loads((output / bootstrap.PRIVATE_RECEIPT).read_text())
    session = json.loads((output / bootstrap.SESSION_PAYLOAD).read_text())
    assert private["access_token"]
    assert session["assignments"][0]["item"]["learner_contract"]["prompt"]
    assert (output / bootstrap.WINDOWS_LAUNCHER).is_file()

    result = validate(
        database_path=database,
        ontology_path=ontology,
        graph_path=graph,
        output_root=output,
        consumer_path=consumer,
        consumer_search_root=tmp_path / ".local",
    )
    assert result["error_count"] == 0, result["errors"]


def test_safe_report_tampering_is_detected(tmp_path: Path, monkeypatch) -> None:
    ontology, graph, consumer, database, output, _ = _bootstrap(tmp_path, monkeypatch)
    safe_path = output / bootstrap.SAFE_REPORT
    safe = json.loads(safe_path.read_text())
    safe["session"]["planned_item_count"] = 99
    safe_path.write_text(json.dumps(safe), encoding="utf-8")
    result = validate(
        database_path=database,
        ontology_path=ontology,
        graph_path=graph,
        output_root=output,
        consumer_path=consumer,
        consumer_search_root=tmp_path / ".local",
    )
    assert result["error_count"] > 0
    assert "safe_report_digest_invalid" in result["errors"]


def test_missing_hash_bound_consumer_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(bootstrap, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(population, "REPO_ROOT", tmp_path)
    ontology, graph, source_consumer = _population_fixture(tmp_path)
    consumer = tmp_path / ".local/m2/consumer.json"
    consumer.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_consumer, consumer)
    database = tmp_path / ".local/m3/learner.sqlite3"
    m3.LearnerStateStore(database).initialize(consumer)
    consumer.unlink()
    with pytest.raises(bootstrap.ProductionBootstrapError, match="hash_bound_m2_consumer_not_found"):
        bootstrap.bootstrap(
            database_path=database,
            ontology_path=ontology,
            graph_path=graph,
            output_root=tmp_path / ".local/r5_bootstrap",
            learner_id="learner-anonymous-01",
            consumer_search_root=tmp_path / ".local",
            reviewed_at="2026-07-19T03:00:00Z",
        )
