import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_exam_source_manifest.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_egp_alignment_cambridge_official_exam_source_manifest_summary.json"
TASK_ID = "R7-M104E1_CambridgeOfficialExamEvidenceIntake"

OFFICIAL_SOURCES = [
    {
        "source_id": "CAMBRIDGE_OFFICIAL_PRE_A1_STARTERS_PAGE",
        "source_type": "official_cambridge_exam_page",
        "url": "https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/starters/",
        "exam": "Pre A1 Starters",
        "cefr_level": "Pre A1",
        "evidence_scope": "exam_level_and_learner_outcome_only",
        "verified_claims": [
            "first of three Cambridge English Qualifications for young learners",
            "CEFR level Pre A1",
            "focuses on everyday written and spoken English through listening, speaking, reading, and writing",
            "learner outcomes include understanding simple instructions, descriptions and questions, copying words, phrases and short sentences, and responding to very simple questions",
        ],
    },
    {
        "source_id": "CAMBRIDGE_OFFICIAL_A1_MOVERS_PAGE",
        "source_type": "official_cambridge_exam_page",
        "url": "https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/movers/",
        "exam": "A1 Movers",
        "cefr_level": "A1",
        "evidence_scope": "exam_level_and_learner_outcome_only",
        "verified_claims": [
            "second of three Cambridge English Qualifications for young learners",
            "CEFR level A1",
            "focuses on everyday written and spoken English through listening, speaking, reading, and writing",
            "learner outcomes include understanding very simple dialogue and descriptions, asking simple questions, writing short simple phrases and sentences, and giving simple descriptions of objects, pictures and actions",
        ],
    },
    {
        "source_id": "CAMBRIDGE_OFFICIAL_A2_FLYERS_PAGE",
        "source_type": "official_cambridge_exam_page",
        "url": "https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/flyers/",
        "exam": "A2 Flyers",
        "cefr_level": "A2",
        "evidence_scope": "exam_level_and_learner_outcome_only",
        "verified_claims": [
            "third of three Cambridge English Qualifications for young learners",
            "CEFR level A2",
            "focuses on everyday written and spoken English through listening, speaking, reading, and writing",
            "learner outcomes include linking phrases or sentences with connectors, telling and writing simple stories, and reading texts containing narrative tenses",
        ],
    },
    {
        "source_id": "CAMBRIDGE_OFFICIAL_A2_KEY_PAGE",
        "source_type": "official_cambridge_exam_page",
        "url": "https://www.cambridgeenglish.org/exams-and-tests/qualifications/key/",
        "exam": "A2 Key for Schools and A2 Key",
        "cefr_level": "A2",
        "evidence_scope": "exam_level_and_learner_outcome_only",
        "verified_claims": [
            "qualification showing learners can communicate in simple situations",
            "tests reading, writing, listening and speaking",
            "CEFR level A2",
            "learner outcomes include understanding and using basic phrases and expressions, understanding simple written English, answering basic questions about themselves, and interacting at a basic level",
        ],
    },
]


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cambridge_official_exam_source_manifest",
        "official_cambridge_source_verified": True,
        "official_source_count": len(OFFICIAL_SOURCES),
        "official_sources": OFFICIAL_SOURCES,
        "authority_scope": {
            "allowed": [
                "confirm Cambridge official exam names",
                "confirm CEFR level of each exam page",
                "confirm broad learner outcomes and exam-facing skills",
                "use as exam-level alignment evidence",
            ],
            "not_allowed": [
                "treat as direct EGP grammar-row authority",
                "auto-patch grammar_nodes.json",
                "auto-create grammar nodes",
                "claim per-cluster official Cambridge verification before an explicit cluster-to-source bridge exists",
            ],
        },
        "per_cluster_official_cambridge_bridge_ready": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_egp_alignment_cambridge_official_exam_source_manifest_summary",
        "validation_status": "PASS",
        "official_cambridge_source_verified": True,
        "official_source_count": len(OFFICIAL_SOURCES),
        "covered_exam_levels": sorted({source["cefr_level"] for source in OFFICIAL_SOURCES}),
        "per_cluster_official_cambridge_bridge_ready": False,
        "operator_patch_decision_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M104E2_CambridgeOfficialClusterBridgePlan",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1 EGP alignment Cambridge official exam source manifest build: PASS")
    print("Official source count:", len(OFFICIAL_SOURCES))
    print("Covered exam levels:", summary["covered_exam_levels"])
    print("Per-cluster bridge ready:", summary["per_cluster_official_cambridge_bridge_ready"])


if __name__ == "__main__":
    main()
