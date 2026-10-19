"""Budget-aware orchestration for the public scanner."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import Iterable

from .formula_factory import FormulaSpec, Order, wrap_specs
from .platform_adapter import PlatformAdapter, SimulationResult
from .sampling import Cell, choose_round
from .statistics import SPRTConfig, SPRTDecision, SequentialTest, estimated_fdr


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
    sprt: SPRTConfig = field(default_factory=SPRTConfig)


@dataclass
class ScanReport:
    state: DatasetState
    simulations: int
    first_order_hits: int
    sprt_score: float
    estimated_first_order_fdr: float | None
    completed_keys: tuple[str, ...]
    results: tuple[SimulationResult, ...]
    gate_decision: SPRTDecision
    history_checked: bool
    note: str = ""


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
        selected.append(spec)
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
    ) -> ScanReport:
        """Run one resumable visit without exceeding the configured budget.

        The method executes the dataset gate and adaptive first-order sampling,
        then bounded higher-order expansions. Completed keys, sanitized results,
        and gate states are accepted so resume preserves statistical context.
        """

        cfg = self.config
        results = {result.candidate_key: result for result in prior_results}
        completed = set(completed_keys) | set(results)
        hit_fields = {
            result.field_key
            for result in results.values()
            if result.is_first_order_hit and result.candidate_key.startswith("first:")
        }
        test = SequentialTest(cfg.sprt)
        prior_first = [
            result.is_first_order_hit
            for result in results.values()
            if result.candidate_key.startswith("first:")
        ]
        if prior_first:
            test.update(prior_first)
        spent = 0

        by_key = {spec.candidate_key: spec for spec in first_order}
        by_field: dict[str, list[Cell]] = {}
        for spec in first_order:
            by_field.setdefault(spec.field_key, []).append(Cell(spec.field_key, spec.candidate_key))

        decision = gate_decision
        first_spent = 0
        while first_spent < cfg.first_order_visit_cap and spent < cfg.daily_budget:
            done_cells = {
                Cell(by_key[key].field_key, key)
                for key in completed
                if key in by_key
            }
            batch_cells = choose_round(
                by_field,
                done_cells,
                hit_fields,
                min(cfg.round_size, cfg.first_order_visit_cap - first_spent, cfg.daily_budget - spent),
                self.rng,
            )
            if not batch_cells:
                break
            batch_specs = [by_key[cell.template_key] for cell in batch_cells]
            batch_results = self.adapter.simulate(batch_specs)
            if {r.candidate_key for r in batch_results} != {s.candidate_key for s in batch_specs}:
                raise ValueError("adapter returned incomplete or unexpected candidate keys")
            results.update((r.candidate_key, r) for r in batch_results)
            completed.update(r.candidate_key for r in batch_results)
            outcomes = [r.is_first_order_hit for r in batch_results]
            hit_fields.update(r.field_key for r in batch_results if r.is_first_order_hit)
            if decision == SPRTDecision.CONTINUE:
                decision = test.update(outcomes)
            first_spent += len(batch_results)
            spent += len(batch_results)

            if not history_checked:
                leaders = sorted(batch_results, key=lambda r: abs(r.sharpe), reverse=True)[:3]
                if not self.adapter.minimum_history_passes(leaders):
                    return self._report(
                        DatasetState.ABANDONED, spent, results, test, completed,
                        decision, history_checked, "minimum-history gate"
                    )
                history_checked = True
            if decision == SPRTDecision.ABANDON:
                return self._report(
                    DatasetState.ABANDONED, spent, results, test, completed,
                    decision, history_checked, "SPRT gate"
                )

        remaining_first = [spec for spec in first_order if spec.candidate_key not in completed]
        if decision == SPRTDecision.CONTINUE and remaining_first:
            return self._report(
                DatasetState.PAUSED, spent, results, test, completed,
                decision, history_checked, "dataset gate unresolved"
            )

        p1 = promote(first_order, results, 1.2, 0.7, cfg.parent_limit_first_to_second, cfg.max_parents_per_field)
        second = wrap_specs(p1, second_wrappers, Order.SECOND)
        spent = self._run_bounded(second, results, completed, spent, cfg.second_order_visit_cap)
        p2 = promote(second, results, 1.3, 0.8, cfg.parent_limit_second_to_third, cfg.max_parents_per_field)
        third = wrap_specs(p2, third_wrappers, Order.THIRD)
        spent = self._run_bounded(third, results, completed, spent, cfg.third_order_visit_cap)

        all_specs = first_order + second + third
        state = DatasetState.EXHAUSTED if all(s.candidate_key in completed for s in all_specs) else DatasetState.PAUSED
        return self._report(state, spent, results, test, completed, decision, history_checked)

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
        test: SequentialTest,
        completed: set[str],
        gate_decision: SPRTDecision,
        history_checked: bool,
        note: str = "",
    ) -> ScanReport:
        first_results = [r for r in results.values() if r.candidate_key.startswith("first:")]
        hits = sum(r.is_first_order_hit for r in first_results)
        return ScanReport(
            state=state,
            simulations=spent,
            first_order_hits=hits,
            sprt_score=test.log_likelihood_ratio,
            estimated_first_order_fdr=estimated_fdr(len(first_results), hits),
            completed_keys=tuple(sorted(completed)),
            results=tuple(sorted(results.values(), key=lambda result: result.candidate_key)),
            gate_decision=gate_decision,
            history_checked=history_checked,
            note=note,
        )

