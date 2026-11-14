"""Field-first adaptive sampling without exposing research field names.

Each round has two kinds of cells, and they are recorded separately because
they answer different questions:

* screening cell: one random template on a field never probed before. Only
  these estimate how common hot fields are in the dataset (README D1).
* follow-up cell: another template on a field that already hit. These test
  that one field (per-field SPRT) and are never fed to the dataset estimate,
  because they were chosen *because* of a hit (adaptive selection).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
import random
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Cell:
    """One abstract field-template experiment."""

    field_key: str
    template_key: str


@dataclass
class RoundPlan:
    followups: list[Cell] = dc_field(default_factory=list)
    screening: list[Cell] = dc_field(default_factory=list)
    mining: list[Cell] = dc_field(default_factory=list)

    def cells(self) -> list[Cell]:
        return self.followups + self.screening + self.mining


def plan_round(
    cells_by_field: Mapping[str, Sequence[Cell]],
    completed: Iterable[Cell],
    probed_fields: set[str],
    testing_fields: Iterable[str],
    hot_fields: Iterable[str],
    mining: bool,
    size: int = 80,
    followups_per_field: int = 8,
    rng: random.Random | None = None,
) -> RoundPlan:
    """Plan one round of at most ``size`` cells.

    Order: (1) up to ``followups_per_field`` follow-ups per field still under test, (2) screening probes
    on never-probed fields, one per field, (3) only once the dataset is being
    mined, remaining cells with hot fields first. Untested cells are never
    pruned; before mining starts, cold fields are not re-sampled.
    """

    plan = RoundPlan()
    if size <= 0:
        return plan
    rng = rng or random.Random()
    done = set(completed)
    remaining = {
        f: [c for c in cells if c not in done] for f, cells in cells_by_field.items()
    }
    remaining = {f: cells for f, cells in remaining.items() if cells}
    taken: set[Cell] = set()

    def take(bucket: list[Cell], cell: Cell) -> bool:
        bucket.append(cell)
        taken.add(cell)
        return len(taken) >= size

    testing = [f for f in testing_fields if f in remaining]
    rng.shuffle(testing)
    for f in testing:
        for c in rng.sample(remaining[f], min(followups_per_field, len(remaining[f]))):
            if take(plan.followups, c):
                return plan

    fresh = [f for f in remaining if f not in probed_fields]
    rng.shuffle(fresh)
    for f in fresh:
        if take(plan.screening, rng.choice(remaining[f])):
            return plan

    if mining:
        hot = set(hot_fields)
        pool_hot = [c for f in remaining if f in hot for c in remaining[f] if c not in taken]
        pool_rest = [c for f in remaining if f not in hot for c in remaining[f] if c not in taken]
        rng.shuffle(pool_hot)
        rng.shuffle(pool_rest)
        for c in pool_hot + pool_rest:
            if take(plan.mining, c):
                return plan
    return plan
