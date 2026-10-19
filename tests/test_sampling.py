import random

from scanner.sampling import Cell, choose_round


def test_round_uses_distinct_fields_when_capacity_allows() -> None:
    cells = {
        f"field-{i}": [Cell(f"field-{i}", f"template-{j}") for j in range(3)]
        for i in range(100)
    }
    selected = choose_round(cells, completed=[], hit_fields=set(), size=80, rng=random.Random(7))
    assert len(selected) == 80
    assert len({cell.field_key for cell in selected}) == 80


def test_hit_fields_are_prioritized() -> None:
    cells = {
        "hit-field": [Cell("hit-field", "a"), Cell("hit-field", "b")],
        "other-field": [Cell("other-field", "c")],
    }
    selected = choose_round(cells, completed=[], hit_fields={"hit-field"}, size=1, rng=random.Random(1))
    assert selected[0].field_key == "hit-field"


def test_small_dataset_fills_from_additional_cells() -> None:
    cells = {
        "field-a": [Cell("field-a", str(i)) for i in range(5)],
        "field-b": [Cell("field-b", str(i)) for i in range(5)],
    }
    selected = choose_round(cells, completed=[], hit_fields=set(), size=6, rng=random.Random(2))
    assert len(selected) == 6

