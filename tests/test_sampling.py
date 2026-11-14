import random

from scanner.sampling import Cell, plan_round


def grid(n_fields, n_templates):
    return {f"field-{i}": [Cell(f"field-{i}", f"field-{i}/t{j}") for j in range(n_templates)] for i in range(n_fields)}


def test_screening_uses_distinct_unprobed_fields():
    plan = plan_round(grid(100, 3), [], set(), [], [], mining=False, size=80, rng=random.Random(7))
    assert len(plan.screening) == 80
    assert len({c.field_key for c in plan.screening}) == 80
    assert not plan.followups and not plan.mining


def test_followups_come_first_and_are_not_screening():
    cells = grid(10, 5)
    plan = plan_round(cells, [], {"field-0"}, ["field-0"], [], mining=False, size=3, rng=random.Random(1))
    assert [c.field_key for c in plan.followups] == ["field-0"] * 3
    assert plan.screening == []


def test_probed_cold_fields_are_not_resampled_before_mining():
    cells = grid(2, 5)
    plan = plan_round(cells, [], {"field-0", "field-1"}, [], [], mining=False, size=6, rng=random.Random(2))
    assert plan.cells() == []


def test_mining_fills_hot_fields_first():
    cells = grid(3, 4)
    plan = plan_round(cells, [], {"field-0", "field-1", "field-2"}, [], ["field-2"], mining=True, size=4, rng=random.Random(3))
    assert {c.field_key for c in plan.mining} == {"field-2"}
