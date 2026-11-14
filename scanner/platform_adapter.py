"""Platform boundary for a public, non-authenticated reference implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    # Names of in-sample checks that FAILED in the simulation result itself
    # (no submission call needed). Correlation checks are pending at that
    # point and must not be listed here.
    failed_checks: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_first_order_hit(self) -> bool:
        return abs(self.sharpe) >= 1.0 and 0.01 <= self.turnover <= 0.70

    def is_line(self, min_sharpe: float = 1.58, min_fitness: float = 1.0) -> bool:
        """Local pre-filter before the platform check.

        Sharpe and fitness are taken in absolute value because a negative
        record is submitted flipped. A record that already failed any
        in-sample check would fail the platform check for the same reason,
        so it is not a line.
        """

        return (
            abs(self.sharpe) >= min_sharpe
            and abs(self.fitness) >= min_fitness
            and not self.failed_checks
        )


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


class RetryingAdapter:
    """Retry transient adapter failures without embedding platform details."""

    def __init__(self, adapter: PlatformAdapter, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.adapter = adapter
        self.max_attempts = max_attempts

    def _call(self, method_name: str, *args):
        for attempt in range(1, self.max_attempts + 1):
            try:
                return getattr(self.adapter, method_name)(*args)
            except Exception:
                if attempt == self.max_attempts:
                    raise

    def simulate(self, candidates: Sequence[FormulaSpec]) -> list[SimulationResult]:
        return self._call("simulate", candidates)

    def minimum_history_passes(self, top_results: Sequence[SimulationResult]) -> bool:
        return self._call("minimum_history_passes", top_results)

