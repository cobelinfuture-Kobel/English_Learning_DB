from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MAPPING_PATH = Path("ulga/graph/a1_egp_canonical_mappings.json")


class CanonicalMappingError(ValueError):
    """Raised when the canonical mapping overlay is missing or inconsistent."""


@dataclass(frozen=True)
class A1CoverageSummary:
    official_rows: int
    covered_rows: int
    remaining_rows: int
    blocked_rows: int
    coverage_percent: float
    mapping_unit_count: int
    canonical_status: str


class A1CanonicalMappingConsumer:
    """Read-only consumer for the canonical A1 EGP mapping overlay."""

    def __init__(self, mapping_path: str | Path = DEFAULT_MAPPING_PATH) -> None:
        self.mapping_path = Path(mapping_path)
        self._data = self._load_and_validate(self.mapping_path)
        self._units = frozenset(self._data["canonical_mapping_units"])

    @staticmethod
    def _load_and_validate(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise CanonicalMappingError(f"Canonical mapping file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CanonicalMappingError(f"Invalid JSON in canonical mapping file: {path}") from exc

        if data.get("canonical_status") != "ACTIVE":
            raise CanonicalMappingError("A1 canonical mapping overlay is not ACTIVE")
        if data.get("official_level") != "A1":
            raise CanonicalMappingError("Canonical mapping overlay is not for official level A1")

        accounting = data.get("canonical_row_accounting")
        units = data.get("canonical_mapping_units")
        if not isinstance(accounting, dict):
            raise CanonicalMappingError("canonical_row_accounting is missing")
        if not isinstance(units, list) or not units:
            raise CanonicalMappingError("canonical_mapping_units is missing or empty")
        if len(units) != len(set(units)):
            raise CanonicalMappingError("canonical_mapping_units contains duplicates")

        official = accounting.get("official_a1_egp_rows")
        covered = accounting.get("cumulative_unique_rows")
        remaining = accounting.get("remaining_unmapped_unique_rows")
        blocked = accounting.get("blocked_rows")
        percent = accounting.get("coverage_percent")
        if not all(isinstance(value, int) for value in (official, covered, remaining, blocked)):
            raise CanonicalMappingError("Canonical row accounting counts must be integers")
        if official != covered + remaining:
            raise CanonicalMappingError("Canonical row accounting does not balance")
        expected_percent = round((covered / official) * 100, 1) if official else 0.0
        if float(percent) != expected_percent:
            raise CanonicalMappingError("Canonical coverage percent is inconsistent")

        return data

    def coverage_summary(self) -> A1CoverageSummary:
        accounting = self._data["canonical_row_accounting"]
        return A1CoverageSummary(
            official_rows=accounting["official_a1_egp_rows"],
            covered_rows=accounting["cumulative_unique_rows"],
            remaining_rows=accounting["remaining_unmapped_unique_rows"],
            blocked_rows=accounting["blocked_rows"],
            coverage_percent=float(accounting["coverage_percent"]),
            mapping_unit_count=len(self._units),
            canonical_status=self._data["canonical_status"],
        )

    def list_mapping_units(self) -> tuple[str, ...]:
        return tuple(sorted(self._units))

    def contains_mapping_unit(self, grammar_id: str) -> bool:
        return grammar_id in self._units

    def require_mapping_units(self, grammar_ids: Iterable[str]) -> tuple[str, ...]:
        missing = tuple(sorted(set(grammar_ids) - self._units))
        if missing:
            raise CanonicalMappingError(
                "Grammar units are not present in the A1 canonical overlay: " + ", ".join(missing)
            )
        return tuple(sorted(set(grammar_ids)))

    def as_query_payload(self) -> dict[str, Any]:
        summary = self.coverage_summary()
        return {
            "official_level": "A1",
            "internal_stages": tuple(self._data.get("internal_stages", ())),
            "canonical_status": summary.canonical_status,
            "coverage": {
                "official_rows": summary.official_rows,
                "covered_rows": summary.covered_rows,
                "remaining_rows": summary.remaining_rows,
                "blocked_rows": summary.blocked_rows,
                "percent": summary.coverage_percent,
            },
            "mapping_units": self.list_mapping_units(),
            "coverage_claim": self._data.get("coverage_claim", {}),
        }
