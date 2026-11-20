"""The execution boundary. The researcher's private adapter implements it; this repository never authenticates,
holds no endpoints, and never submits."""
from typing import Protocol, Sequence

from .policy import Dataset, Pick


class PlatformAdapter(Protocol):
    def fields(self, dataset: Dataset) -> list:
        """Keys of the dataset's usable fields."""

    def simulate(self, picks: Sequence[Pick]) -> list:
        """One (Result, daily PnL array) per pick, in order. A failed simulation is a Result with error=True."""
