from __future__ import annotations

from collections import Counter

from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population


def _candidate(item_id: str, skill: str, payload: object | None = None, *, delivery_state: str = "AVAILABLE") -> dict:
    dependencies = []
    manifest = []
    if payload is not None:
        dependencies.append(
            {
                "dependency_id": "DEP_AUDIO_1",
                "kind": "AUDIO",
                "renderer_type": "AUDIO_PLAYER",
                "delivery_state": delivery_state,
                "required": True,
                "visibility_required": True,
            }
        )
        manifest.append(
            {
                "dependency_id": "DEP_AUDIO_1",
                "kind": "AUDIO",
                "renderer_type": "AUDIO_PLAYER",
                "delivery_state": delivery_state,
                "payload": payload,
            }
        )
    return {
        "item_id": item_id,
        "skill": skill,
        "media_payload_state": "DEFERRED_MEDIA_PAYLOAD" if skill == "LISTENING" else "NOT_REQUIRED",
        "learner_contract": {
            "stimulus_contract": {"dependencies": dependencies},
            "stimulus_render_manifest": manifest,
        },
    }


def test_listening_audio_authority_requires_real_audio_player_payload() -> None:
    assert population._listening_audio_authority_ready(
        _candidate("L1", "LISTENING", "private-media://listening/L001.mp3")
    ) is True
    assert population._listening_audio_authority_ready(
        _candidate("L2", "LISTENING", "SCRIPT_ONLY_NO_AUDIO_BYTES")
    ) is False
    assert population._listening_audio_authority_ready(
        _candidate("L3", "LISTENING", "audio.wav", delivery_state="DEFERRED_MEDIA_PAYLOAD")
    ) is False
    assert population._listening_audio_authority_ready(
        _candidate("L4", "LISTENING")
    ) is False


def test_candidate_projection_removes_text_only_listening_and_preserves_other_skills(monkeypatch) -> None:
    good_listening = _candidate("L-GOOD", "LISTENING", {"url": "asset://audio/l-good.ogg"})
    bad_listening = _candidate("L-BAD", "LISTENING")
    speaking = _candidate("S-GOOD", "SPEAKING")
    source_candidates = [good_listening, bad_listening, speaking]
    source_by_node = {"NODE_1": list(source_candidates)}

    monkeypatch.setattr(
        population,
        "_ORIGINAL_CANDIDATE_PROJECTION",
        lambda *args, **kwargs: (source_candidates, source_by_node, Counter()),
    )

    candidates, by_node, rejected = population._candidate_projection()

    assert [row["item_id"] for row in candidates] == ["L-GOOD", "S-GOOD"]
    assert candidates[0]["media_payload_state"] == "AVAILABLE"
    assert [row["item_id"] for row in by_node["NODE_1"]] == ["L-GOOD", "S-GOOD"]
    assert rejected == Counter({"LISTENING_PLAYABLE_AUDIO_REQUIRED": 1})


def test_listening_obligation_remains_media_required(monkeypatch) -> None:
    obligation = {
        "required_skills": ["LISTENING"],
        "required_media_policy": "NONE",
    }
    registry = {
        "profiles": [
            {
                "obligations": [obligation],
            }
        ]
    }
    index = {("CAP", "LIFE", "DOMAIN"): {"obligation": obligation}}

    monkeypatch.setattr(
        population,
        "_ORIGINAL_PROFILES_AND_OBLIGATIONS",
        lambda *args, **kwargs: (registry, index),
    )

    result, result_index = population._profiles_and_obligations()

    assert result["profiles"][0]["obligations"][0]["required_media_policy"] == "REQUIRED"
    assert result_index[("CAP", "LIFE", "DOMAIN")]["obligation"]["required_media_policy"] == "REQUIRED"
