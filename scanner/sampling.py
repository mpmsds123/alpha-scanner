"""Field-first adaptive sampling without exposing research field names."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Cell:
    """One abstract field-template experiment."""

    field_key: str
    template_key: str


def choose_round(
    cells_by_field: Mapping[str, Sequence[Cell]],
    completed: Iterable[Cell],
    hit_fields: set[str],
    size: int = 80,
    rng: random.Random | None = None,
) -> list[Cell]:
    """Choose a batch while prioritizing fields that already produced a hit.

    Stage one takes at most one cell per field, which keeps the dataset gate
    close to its independence assumption. Hit fields are visited first. If the
    dataset has fewer fields than the requested batch size, stage two fills the
    remaining capacity from other untested cells.
    """

    if size <= 0:
        return []
    rng = rng or random.Random()
    done = set(completed)
    remaining = {
        field: [cell for cell in cells if cell not in done]
        for field, cells in cells_by_field.items()
    }
    remaining = {field: cells for field, cells in remaining.items() if cells}

    priority = [field for field in remaining if field in hit_fields]
    ordinary = [field for field in remaining if field not in hit_fields]
    rng.shuffle(priority)
    rng.shuffle(ordinary)

    selected: list[Cell] = []
    for field in priority + ordinary:
        selected.append(rng.choice(remaining[field]))
        if len(selected) == size:
            return selected

    selected_set = set(selected)
    pool = [
        cell
        for cells in remaining.values()
        for cell in cells
        if cell not in selected_set
    ]
    rng.shuffle(pool)
    selected.extend(pool[: size - len(selected)])
    return selected

