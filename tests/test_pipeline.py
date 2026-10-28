from scanner.formula_factory import first_order_specs
from scanner.pipeline import AdaptiveScanner, DatasetState, ScannerConfig
from scanner.platform_adapter import RetryingAdapter, SimulationResult


class FakeAdapter:
    def __init__(self, hit_keys: set[str], history_passes: bool = True) -> None:
        self.hit_keys = hit_keys
        self.history_passes = history_passes

    def simulate(self, candidates):
        return [
            SimulationResult(
                candidate_key=spec.candidate_key,
                field_key=spec.field_key,
                sharpe=1.5 if spec.candidate_key in self.hit_keys else 0.0,
                fitness=0.9 if spec.candidate_key in self.hit_keys else 0.0,
                turnover=0.20,
                positions=150,
            )
            for spec in candidates
        ]

    def minimum_history_passes(self, top_results):
        return self.history_passes


def make_specs(fields: int, templates: int):
    return first_order_specs(
        [f"field-{i:03d}" for i in range(fields)],
        [f"template-{j:02d}" for j in range(templates)],
    )


def test_rich_dataset_completes_small_grid() -> None:
    specs = make_specs(80, 1)
    hits = {spec.candidate_key for spec in specs[:3]}
    report = AdaptiveScanner(FakeAdapter(hits), seed=3).run_visit(specs)
    assert report.state == DatasetState.EXHAUSTED
    assert report.simulations == 80
    assert report.first_order_hits == 3


def test_zero_hit_dataset_is_abandoned_at_first_look() -> None:
    specs = make_specs(300, 1)
    config = ScannerConfig(first_order_visit_cap=300)
    report = AdaptiveScanner(FakeAdapter(set()), config=config, seed=4).run_visit(specs)
    assert report.state == DatasetState.ABANDONED
    assert report.simulations == 80
    assert report.note == "SPRT gate"


def test_history_gate_precedes_more_spending() -> None:
    specs = make_specs(100, 1)
    report = AdaptiveScanner(FakeAdapter(set(), history_passes=False), seed=5).run_visit(specs)
    assert report.state == DatasetState.ABANDONED
    assert report.simulations == 80
    assert report.note == "minimum-history gate"


def test_visit_respects_first_order_cap_and_can_resume() -> None:
    specs = make_specs(120, 2)
    hits = {spec.candidate_key for spec in specs[:24]}
    config = ScannerConfig(first_order_visit_cap=160, round_size=80)
    first = AdaptiveScanner(FakeAdapter(hits), config=config, seed=1).run_visit(specs)
    assert first.state == DatasetState.PAUSED
    assert first.simulations == 160

    second = AdaptiveScanner(FakeAdapter(hits), config=config, seed=1).run_visit(
        specs,
        completed_keys=first.completed_keys,
        prior_results=first.results,
        gate_decision=first.gate_decision,
        history_checked=first.history_checked,
    )
    assert second.simulations <= 80
    assert second.first_order_hits == 24


def test_retrying_adapter_recovers_from_transient_failure() -> None:
    class FlakyAdapter(FakeAdapter):
        def __init__(self):
            super().__init__(set())
            self.calls = 0

        def simulate(self, candidates):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient")
            return super().simulate(candidates)

    flaky = FlakyAdapter()
    results = RetryingAdapter(flaky, max_attempts=2).simulate(make_specs(2, 1))
    assert len(results) == 2
    assert flaky.calls == 2

