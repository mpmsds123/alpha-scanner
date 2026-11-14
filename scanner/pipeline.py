"""Budget-aware orchestration for the public scanner."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import random
from typing import Iterable

from .formula_factory import FormulaSpec, Order, wrap_specs
from .platform_adapter import PlatformAdapter, SimulationResult
from .sampling import Cell, plan_round
from .statistics import (
    FieldTestConfig,
    SPRTDecision,
    SequentialTest,
    estimated_fdr,
    screening_probes_needed,
)


class DatasetState(str, Enum):
    UNTOUCHED = "untouched"
    GATING = "gating"
    ABANDONED = "abandoned"
    PAUSED = "paused"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class ScannerConfig:
    daily_budget: int = 4_000
    round_size: int = 80
    first_order_visit_cap: int = 2_000
    second_order_visit_cap: int = 1_000
    third_order_visit_cap: int = 1_000
    parent_limit_first_to_second: int = 100
    parent_limit_second_to_third: int = 200
    max_parents_per_field: int = 5
    # Dataset gate: stop only after enough distinct-field probes that a
    # dataset with >= screening_pi_min hot fields would have shown a hit
    # with probability >= 1 - screening_miss, and every hit field tested cold.
    screening_pi_min: float = 0.03
    screening_miss: float = 0.10
    followups_per_field: int = 8
    field_test: FieldTestConfig = field(default_factory=FieldTestConfig)

    @property
    def screening_probes(self) -> int:
        f = screening_probes_needed(self.screening_pi_min, self.field_test.q_hot, self.screening_miss)
        return -(-f // self.round_size) * self.round_size  # whole rounds


@dataclass
class ScanReport:
    state: DatasetState
    simulations: int
    first_order_hits: int
    screening_probes: int
    screening_hits: int
    hot_fields: tuple[str, ...]
    estimated_first_order_fdr: float | None
    completed_keys: tuple[str, ...]
    results: tuple[SimulationResult, ...]
    gate_decision: SPRTDecision
    history_checked: bool
    screening_keys: tuple[str, ...] = ()
    check_queue: tuple[FormulaSpec, ...] = ()
    note: str = ""


@dataclass
class GateState:
    decision: SPRTDecision
    probed_fields: set[str]
    testing_fields: list[str]
    hot_fields: list[str]
    screening_hits: int


def evaluate_gate(
    by_field: dict[str, list[Cell]],
    results: dict[str, SimulationResult],
    screening_keys: set[str],
    config: ScannerConfig,
    prior: SPRTDecision,
) -> GateState:
    """Rebuild the dataset decision from the records alone.

    Recomputed from scratch each time, so a resumed visit reaches the same
    state as an uninterrupted one. Per field: the first hit selected the field,
    so the test sees (hits - 1) hits and (cells - hits) misses.
    """

    first = [r for r in results.values() if r.candidate_key.startswith("first:")]
    probed = {results[k].field_key for k in screening_keys if k in results}
    screening_hits = sum(results[k].is_first_order_hit for k in screening_keys if k in results)
    per_field: dict[str, list[bool]] = {}
    for r in first:
        per_field.setdefault(r.field_key, []).append(r.is_first_order_hit)
    testing, hot = [], []
    for f, outcomes in per_field.items():
        h = sum(outcomes)
        if h == 0:
            continue
        t = SequentialTest(config.field_test.as_sprt())
        verdict = t.update([True] * (h - 1) + [False] * (len(outcomes) - h))
        untested_left = len(outcomes) < len(by_field.get(f, ()))
        if verdict == SPRTDecision.CONTINUE and not untested_left:
            # Field has no cells left to test: Wald's truncation rule.
            verdict = SPRTDecision.MINE if t.log_likelihood_ratio >= 0 else SPRTDecision.ABANDON
        if verdict == SPRTDecision.MINE:
            hot.append(f)
        elif verdict == SPRTDecision.CONTINUE and untested_left:
            testing.append(f)
    if prior == SPRTDecision.MINE or hot:
        decision = SPRTDecision.MINE
    elif not testing and len(probed) >= min(config.screening_probes, len(by_field)):
        decision = SPRTDecision.ABANDON
    else:
        decision = SPRTDecision.CONTINUE
    return GateState(decision, probed, sorted(testing), sorted(hot), screening_hits)


def check_queue(specs: Iterable[FormulaSpec], results: dict[str, SimulationResult]) -> list[FormulaSpec]:
    """One representative per family (order, field) for the platform check.

    The representative is the highest-|Sharpe| record that is a line, i.e.
    that has not already failed an in-sample check. Its sign is set so the
    submitted version has positive Sharpe.
    """

    best: dict[tuple[int, str], tuple[float, FormulaSpec]] = {}
    for spec in specs:
        r = results.get(spec.candidate_key)
        if r is None or not r.is_line():
            continue
        key = (int(spec.order), spec.field_key)
        if key not in best or abs(r.sharpe) > best[key][0]:
            sign = spec.sign * (1 if r.sharpe >= 0 else -1)
            best[key] = (abs(r.sharpe), replace(spec, sign=sign))
    return [v[1] for _, v in sorted(best.items())]


def promote(
    specs: Iterable[FormulaSpec],
    results: dict[str, SimulationResult],
    min_sharpe: float,
    min_fitness: float,
    limit: int,
    per_field: int,
) -> list[FormulaSpec]:
    """Select parents by documented numeric cutoffs with a field concentration cap."""

    ranked = sorted(
        (
            spec
            for spec in specs
            if spec.candidate_key in results
            and abs(results[spec.candidate_key].sharpe) >= min_sharpe
            and abs(results[spec.candidate_key].fitness) >= min_fitness
            and results[spec.candidate_key].positions > 100
        ),
        key=lambda spec: abs(results[spec.candidate_key].sharpe),
        reverse=True,
    )
    selected: list[FormulaSpec] = []
    counts: dict[str, int] = {}
    for spec in ranked:
        if counts.get(spec.field_key, 0) >= per_field:
            continue
        flip = 1 if results[spec.candidate_key].sharpe >= 0 else -1
        selected.append(replace(spec, sign=spec.sign * flip))
        counts[spec.field_key] = counts.get(spec.field_key, 0) + 1
        if len(selected) == limit:
            break
    return selected


class AdaptiveScanner:
    """Run the documented decisions through an injected platform adapter."""

    def __init__(self, adapter: PlatformAdapter, config: ScannerConfig | None = None, seed: int = 0) -> None:
        self.adapter = adapter
        self.config = config or ScannerConfig()
        self.rng = random.Random(seed)

    def run_visit(
        self,
        first_order: list[FormulaSpec],
        second_wrappers: Iterable[str] = (),
        third_wrappers: Iterable[str] = (),
        completed_keys: Iterable[str] = (),
        prior_results: Iterable[SimulationResult] = (),
        gate_decision: SPRTDecision = SPRTDecision.CONTINUE,
        history_checked: bool = False,
        screening_keys: Iterable[str] = (),
    ) -> ScanReport:
        """Run one resumable visit without exceeding the configured budget.

        First order: screening probes and per-field follow-ups until the
        dataset gate decides; once a field is confirmed hot, the dataset is
        mined (hot fields first). Then bounded stage-2 and stage-3 expansions.
        Pass back ``screening_keys`` on resume: they are the only records the
        dataset estimate may use.
        """

        cfg = self.config
        results = {result.candidate_key: result for result in prior_results}
        completed = set(completed_keys) | set(results)
        screening = set(screening_keys)
        spent = 0

        by_key = {spec.candidate_key: spec for spec in first_order}
        by_field: dict[str, list[Cell]] = {}
        for spec in first_order:
            by_field.setdefault(spec.field_key, []).append(Cell(spec.field_key, spec.candidate_key))

        gate = evaluate_gate(by_field, results, screening, cfg, gate_decision)
        first_spent = 0
        while first_spent < cfg.first_order_visit_cap and spent < cfg.daily_budget:
            if gate.decision == SPRTDecision.ABANDON:
                break
            done_cells = {Cell(by_key[k].field_key, k) for k in completed if k in by_key}
            plan = plan_round(
                by_field, done_cells, gate.probed_fields, gate.testing_fields, gate.hot_fields,
                mining=gate.decision == SPRTDecision.MINE,
                size=min(cfg.round_size, cfg.first_order_visit_cap - first_spent, cfg.daily_budget - spent),
                followups_per_field=cfg.followups_per_field,
                rng=self.rng,
            )
            batch_cells = plan.cells()
            if not batch_cells:
                break
            batch_specs = [by_key[cell.template_key] for cell in batch_cells]
            batch_results = self.adapter.simulate(batch_specs)
            if {r.candidate_key for r in batch_results} != {s.candidate_key for s in batch_specs}:
                raise ValueError("adapter returned incomplete or unexpected candidate keys")
            results.update((r.candidate_key, r) for r in batch_results)
            completed.update(r.candidate_key for r in batch_results)
            screening.update(c.template_key for c in plan.screening)
            first_spent += len(batch_results)
            spent += len(batch_results)

            if not history_checked:
                leaders = sorted(batch_results, key=lambda r: abs(r.sharpe), reverse=True)[:3]
                if not self.adapter.minimum_history_passes(leaders):
                    return self._report(DatasetState.ABANDONED, spent, results, completed, gate,
                                        history_checked, screening, (), "minimum-history gate")
                history_checked = True
            gate = evaluate_gate(by_field, results, screening, cfg, gate.decision)

        if gate.decision == SPRTDecision.ABANDON:
            return self._report(DatasetState.ABANDONED, spent, results, completed, gate,
                                history_checked, screening, (), "dataset gate")
        remaining_first = [spec for spec in first_order if spec.candidate_key not in completed]
        if gate.decision == SPRTDecision.CONTINUE and remaining_first:
            return self._report(DatasetState.PAUSED, spent, results, completed, gate,
                                history_checked, screening, (), "dataset gate unresolved")

        p1 = promote(first_order, results, 1.2, 0.7, cfg.parent_limit_first_to_second, cfg.max_parents_per_field)
        second = wrap_specs(p1, second_wrappers, Order.SECOND)
        spent = self._run_bounded(second, results, completed, spent, cfg.second_order_visit_cap)
        p2 = promote(second, results, 1.3, 0.8, cfg.parent_limit_second_to_third, cfg.max_parents_per_field)
        third = wrap_specs(p2, third_wrappers, Order.THIRD)
        spent = self._run_bounded(third, results, completed, spent, cfg.third_order_visit_cap)

        all_specs = first_order + second + third
        state = DatasetState.EXHAUSTED if all(s.candidate_key in completed for s in all_specs) else DatasetState.PAUSED
        return self._report(state, spent, results, completed, gate, history_checked, screening,
                            tuple(check_queue(all_specs, results)))

    def _run_bounded(
        self,
        specs: list[FormulaSpec],
        results: dict[str, SimulationResult],
        completed: set[str],
        spent: int,
        order_cap: int,
    ) -> int:
        pending = [spec for spec in specs if spec.candidate_key not in completed]
        allowance = min(order_cap, self.config.daily_budget - spent, len(pending))
        for start in range(0, allowance, self.config.round_size):
            batch = pending[start : min(start + self.config.round_size, allowance)]
            batch_results = self.adapter.simulate(batch)
            if {r.candidate_key for r in batch_results} != {s.candidate_key for s in batch}:
                raise ValueError("adapter returned incomplete or unexpected candidate keys")
            results.update((r.candidate_key, r) for r in batch_results)
            completed.update(r.candidate_key for r in batch_results)
            spent += len(batch_results)
        return spent

    @staticmethod
    def _report(
        state: DatasetState,
        spent: int,
        results: dict[str, SimulationResult],
        completed: set[str],
        gate: GateState,
        history_checked: bool,
        screening: set[str],
        queue: tuple[FormulaSpec, ...],
        note: str = "",
    ) -> ScanReport:
        first_results = [r for r in results.values() if r.candidate_key.startswith("first:")]
        hits = sum(r.is_first_order_hit for r in first_results)
        return ScanReport(
            state=state,
            simulations=spent,
            first_order_hits=hits,
            screening_probes=len(screening),
            screening_hits=gate.screening_hits,
            hot_fields=tuple(gate.hot_fields),
            estimated_first_order_fdr=estimated_fdr(len(first_results), hits),
            completed_keys=tuple(sorted(completed)),
            results=tuple(sorted(results.values(), key=lambda result: result.candidate_key)),
            gate_decision=gate.decision,
            history_checked=history_checked,
            screening_keys=tuple(sorted(screening)),
            check_queue=queue,
            note=note,
        )
