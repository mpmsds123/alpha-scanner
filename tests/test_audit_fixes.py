"""Regression tests for the 2026-11-14 audit fixes (see CHANGELOG 2026-11-14)."""
import random

from scanner.formula_factory import FormulaSpec, Order, first_order_specs, wrap_specs
from scanner.pipeline import AdaptiveScanner, DatasetState, ScannerConfig, check_queue, promote
from scanner.platform_adapter import SimulationResult
from scanner.statistics import screening_probes_needed


class FieldModel:
    """Hot fields hit 19.4% of cells, cold fields 0.3% (README E2/E3)."""

    def __init__(self, hot, seed=0):
        self.hot, self.rng = set(hot), random.Random(seed)

    def simulate(self, specs):
        out = []
        for s in specs:
            hit = self.rng.random() < (0.194 if s.field_key in self.hot else 0.003)
            out.append(SimulationResult(s.candidate_key, s.field_key, 1.5 if hit else 0.1, 0.9 if hit else 0.0, 0.2, 150))
        return out

    def minimum_history_passes(self, top):
        return True


NO_HIGHER = ScannerConfig(second_order_visit_cap=0, third_order_visit_cap=0)


def specs(n_fields, n_templates=56):
    return first_order_specs([f"f{i}" for i in range(n_fields)], [f"t{j}" for j in range(n_templates)])


def test_screening_probe_formula():
    # F = ln(0.10) / ln(1 - 0.03 * 0.194) = 395
    assert screening_probes_needed(0.03, 0.194, 0.10) == 395
    assert ScannerConfig().screening_probes == 400  # whole rounds of 80


def test_few_hot_fields_dataset_is_kept_most_of_the_time():
    # Dataset C shape: 8 strong fields in 300. The v7 gate kept this 0.5% of the time.
    kept = 0
    for r in range(40):
        hot = random.Random(r).sample([f"f{i}" for i in range(300)], 8)
        rep = AdaptiveScanner(FieldModel(hot, r), NO_HIGHER, seed=r).run_visit(specs(300))
        kept += rep.state != DatasetState.ABANDONED
    assert kept >= 28  # Monte Carlo 81.5% over 400 runs


def test_dead_dataset_is_abandoned():
    rep = AdaptiveScanner(FieldModel(set(), 1), NO_HIGHER, seed=1).run_visit(specs(300))
    assert rep.state == DatasetState.ABANDONED
    assert rep.screening_probes == 300  # every field probed once (300 < 400)
    assert rep.simulations < 400


def test_resume_reaches_same_gate_state_as_one_visit():
    hot = ["f3", "f7"]
    s = specs(200)
    cfg = ScannerConfig(first_order_visit_cap=160, second_order_visit_cap=0, third_order_visit_cap=0)
    a = AdaptiveScanner(FieldModel(hot, 5), cfg, seed=5).run_visit(s)
    b = AdaptiveScanner(FieldModel(hot, 6), cfg, seed=6).run_visit(
        s, completed_keys=a.completed_keys, prior_results=a.results,
        gate_decision=a.gate_decision, history_checked=a.history_checked,
        screening_keys=a.screening_keys,
    )
    assert set(a.screening_keys) <= set(b.screening_keys)
    assert b.screening_probes >= a.screening_probes


def test_flipped_parent_sign_reaches_children():
    parent = first_order_specs(["f"], ["t"])[0]
    res = {parent.candidate_key: SimulationResult(parent.candidate_key, "f", -1.6, -0.9, 0.2, 150)}
    [p] = promote([parent], res, 1.2, 0.7, 10, 5)
    assert p.sign == -1
    assert all(c.sign == -1 for c in wrap_specs([p], ["g1", "g2"], Order.SECOND))


def test_check_queue_skips_record_that_failed_in_sample_check():
    a, b = first_order_specs(["f"], ["t1", "t2"])
    res = {
        a.candidate_key: SimulationResult(a.candidate_key, "f", 2.4, 1.5, 0.2, 150,
                                          frozenset({"IS_LADDER_SHARPE"})),
        b.candidate_key: SimulationResult(b.candidate_key, "f", 1.9, 1.2, 0.2, 150),
    }
    queue = check_queue([a, b], res)
    assert [q.candidate_key for q in queue] == [b.candidate_key]
