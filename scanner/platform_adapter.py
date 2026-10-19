"""Platform boundary for a public, non-authenticated reference implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .formula_factory import FormulaSpec


@dataclass(frozen=True)
class SimulationResult:
    candidate_key: str
    field_key: str
    sharpe: float
    fitness: float
    turnover: float
    positions: int = 0

    @property
    def is_first_order_hit(self) -> bool:
        return abs(self.sharpe) >= 1.0 and 0.01 <= self.turnover <= 0.70


class PlatformAdapter(Protocol):
    """Minimal interface implemented outside this repository by the researcher."""

    def simulate(self, candidates: Sequence[FormulaSpec]) -> list[SimulationResult]:
        """Run candidates and return results with matching public candidate keys."""

    def minimum_history_passes(self, top_results: Sequence[SimulationResult]) -> bool:
        """Return whether the dataset satisfies the platform's history gate."""


class AdapterNotConfigured(RuntimeError):
    pass


class PublicStubAdapter:
    """Fails explicitly instead of embedding credentials or private endpoints."""

    def simulate(self, candidates: Sequence[FormulaSpec]) -> list[SimulationResult]:
        raise AdapterNotConfigured(
            "Provide your own PlatformAdapter; the public repository contains no "
            "authentication, endpoints, or production expressions."
        )

    def minimum_history_passes(self, top_results: Sequence[SimulationResult]) -> bool:
        raise AdapterNotConfigured("history checks belong in a private adapter")

