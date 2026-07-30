from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as registry
from ulga.validators import validate_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as validator


def approval() -> dict:
    return {
        'task_id':'A1FS-V1-RAZQ01B2_Unit01V2ApprovalReplayConsumerReconciliation',
        'unit_id':registry.UNIT_ID,
        'decision_status':'APPROVED_AS_RECONCILED',
        'approved_contract_sha256':registry.APPROVED_CONTRACT_SHA256,
        'boundaries':{
            'unit02_to_unit24_modified':False,
            'canonical_question_bank_written':False,
            'learner_facing_content_written':False,
            'audio_enabled':False,
            'speaking_capture_enabled':False,
            'a2_unlocked':False,
            'parallel_curriculum_created':False,
        },
    }


def build() -> dict:
    return registry.build_registry(contract_builder.build_contract(), approval())


def test_registry_materializes_exact_unit01_denominators() -> None:
    report = build()
    assert report['denominators'] == {
        'active_vocabulary':22,
        'active_nouns':16,
        'active_adjectives':6,
        'receptive_vocabulary':9,
        'canonical_chunks':3,
        'instructional_phrases_distinct':46,
        'target_sentence_frames':9,
        'scaffold_sentence_frames':2,
        'total_language_asset_bindings':91,
    }
    assert validator.validate_report(report)['validation_status'] == validator.PASS_STATUS


def test_registry_preserves_authority_ids_and_reference_only_reuse() -> None:
    report = build()
    vocabulary = report['asset_bindings']['vocabulary']
    apple = next(row for row in vocabulary if row['surface_form'] == 'apple')
    assert apple['asset_id'] == 'vocabulary:apple:v_418'
    assert apple['copy_on_reuse'] is False
    assert apple['reusable_in_later_units'] is True
    assert apple['introduced_unit_sequence'] == 1
    assert 'RECOMBINATION' in apple['eligible_future_unit_roles']
    assert report['cumulative_reuse_policy']['copy_records_into_later_units'] is False


def test_phrase_registry_deduplicates_surfaces_and_merges_provenance() -> None:
    report = build()
    phrases = report['asset_bindings']['instructional_phrases']
    assert len(phrases) == 46
    assert len({row['normalized_surface'] for row in phrases}) == 46
    a_bag = next(row for row in phrases if row['normalized_surface'] == 'a bag')
    source_types = {row['source_type'] for row in a_bag['provenance']}
    assert source_types == {'NOUN_MEMORY_INDEFINITE','INSTRUCTIONAL_PHRASE'}


def test_a2_bridge_and_countability_sensitive_chunk_remain_receptive() -> None:
    report = build()
    toy = next(row for row in report['asset_bindings']['vocabulary'] if row['surface_form'] == 'toy')
    assert toy['a2_bridge'] is True
    assert toy['production_allowed'] is False
    assert toy['direct_assessment_allowed'] is False
    ice_cream = next(row for row in report['asset_bindings']['canonical_chunks'] if row['asset_id'] == 'EVP_CHUNK_000054')
    assert ice_cream['production_allowed'] is False
    assert ice_cream['direct_assessment_allowed'] is False


def test_validator_fails_closed_on_copy_or_question_bank_drift() -> None:
    report = build()
    drifted = deepcopy(report)
    drifted['cumulative_reuse_policy']['copy_records_into_later_units'] = True
    with pytest.raises(validator.RegistryValidationError, match='copy_on_reuse_forbidden'):
        validator.validate_report(drifted)
    drifted = deepcopy(report)
    drifted['asset_bindings']['vocabulary'][0]['question_id'] = 'Q-U01-001'
    with pytest.raises(validator.RegistryValidationError, match='forbidden_content_keys'):
        validator.validate_report(drifted)


def test_repository_approved_contract_materializes_and_validates() -> None:
    approval_path = Path(
        "ulga/graph/a1fs_v1_razq01b2_unit01_content_contract_approval_v2.json"
    )
    approved = json.loads(approval_path.read_text(encoding="utf-8"))
    report = registry.build_registry(contract_builder.build_contract(), approved)
    result = validator.validate_report(report)
    assert result["denominators"]["total_language_asset_bindings"] == 91
    assert result["registry_sha256"] == report["registry_sha256"]
