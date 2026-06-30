from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.validators import validate_raz_downstream_discovery_drift as drift_validator  # noqa: E402


class RazDownstreamDiscoveryDriftValidatorTests(unittest.TestCase):
    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_inventory(self, path: Path) -> None:
        self.write_json(
            path,
            [
                {
                    "level": "A",
                    "normalized_level": "A",
                    "authority_status": "candidate_only",
                    "promotion_allowed": False,
                }
            ],
        )

    def write_allowlist(self, path: Path) -> None:
        self.write_json(
            path,
            {
                "safe_single_level_utilities": [
                    {
                        "path": "tools/raz/build_raz_level_manifest.py",
                        "required_patterns": ["--level"],
                        "reason": "Explicit single-level utility.",
                    }
                ],
                "warning_legacy_references": [],
            },
        )

    def run_report(self, tmp_path: Path, scan_paths: list[Path]) -> dict:
        inventory_path = tmp_path / "ulga" / "graph" / "raz_level_discovery_inventory.json"
        s6e_path = tmp_path / "ulga" / "reports" / "raz_level_discovery_downstream_integration_qa.json"
        allowlist_path = tmp_path / "ulga" / "policies" / "raz_downstream_discovery_drift_allowlist.json"
        report_path = tmp_path / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"
        self.write_inventory(inventory_path)
        self.write_json(s6e_path, {"status": "PASS_WITH_WARNINGS"})
        self.write_allowlist(allowlist_path)
        return drift_validator.build_validation_report(
            base_dir=tmp_path,
            inventory_path=inventory_path,
            s6e_report_path=s6e_path,
            allowlist_path=allowlist_path,
            report_path=report_path,
            scan_paths=scan_paths,
        )

    def test_current_repo_scan_is_not_fail(self) -> None:
        report = drift_validator.build_validation_report()
        self.assertIn(report["status"], {"PASS", "PASS_WITH_WARNINGS"})
        self.assertTrue(report["s6d_inventory_exists"])
        self.assertTrue(report["s6e_report_exists"])
        self.assertEqual(report["candidate_only_invariant"], "PASS")
        self.assertEqual(report["promotion_allowed_invariant"], "PASS")

    def test_fail_on_direct_level_scan_in_active_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            active = tmp_path / "tools" / "raz_bad_builder.py"
            self.write_text(
                active,
                'from pathlib import Path\nroot = Path("raz_output_jsons")\nlevels = sorted(root.glob("Level_*"))\n',
            )
            report = self.run_report(tmp_path, [active])
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(len(report["risky_direct_level_scans"]), 1)

    def test_fail_on_fixed_level_universe_in_active_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            active = tmp_path / "ulga" / "query" / "raz_bad_query.py"
            self.write_text(
                active,
                'LEVELS = ("A", "B", "C", "D", "E", "F")\n',
            )
            report = self.run_report(tmp_path, [active])
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(len(report["risky_fixed_level_universes"]), 1)

    def test_pass_on_test_fixture_level_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixture = tmp_path / "tests" / "test_raz_fixture.py"
            self.write_text(fixture, 'raw_dir = tmp_path / "Level_F"\n')
            report = self.run_report(tmp_path, [fixture])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["safe_test_fixtures"]), 1)

    def test_pass_on_historical_doc_level_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc = tmp_path / "docs" / "ulga" / "RAZ_HISTORY.md"
            self.write_text(doc, "Load all Level_A-F enriched files.\n")
            report = self.run_report(tmp_path, [doc])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["safe_historical_docs"]), 1)

    def test_pass_on_single_level_utility_with_explicit_level_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            utility = tmp_path / "tools" / "raz" / "build_raz_level_manifest.py"
            self.write_text(
                utility,
                'parser.add_argument("--level", default="A")\npdf_dir = base_dir / "input" / "pdf" / level.lower()\n',
            )
            report = self.run_report(tmp_path, [utility])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["safe_single_level_utilities"]), 1)

    def test_fail_on_promotion_allowed_true_in_active_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            active = tmp_path / "ulga" / "query" / "raz_bad_promotion.py"
            self.write_text(active, 'query_metadata = {"authority_promotion_allowed": true}\n')
            report = self.run_report(tmp_path, [active])
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(len(report["risky_independent_readiness_logic"]), 1)

    def test_json_report_contains_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            active = tmp_path / "tools" / "raz_ok.py"
            self.write_text(active, "from ulga.builders import build_raz_level_discovery\n")
            report = self.run_report(tmp_path, [active])
            required_keys = {
                "task",
                "status",
                "s6d_inventory_exists",
                "s6e_report_exists",
                "files_scanned",
                "safe_discovery_consumers",
                "safe_test_fixtures",
                "safe_historical_docs",
                "safe_single_level_utilities",
                "safe_path_naming_patterns",
                "warnings",
                "risky_direct_level_scans",
                "risky_fixed_level_universes",
                "risky_independent_readiness_logic",
                "must_fix_findings",
                "candidate_only_invariant",
                "promotion_allowed_invariant",
                "summary",
                "next_recommended_task",
            }
            self.assertTrue(required_keys <= set(report))


if __name__ == "__main__":
    unittest.main()
