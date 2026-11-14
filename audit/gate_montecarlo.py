"""Monte Carlo of the dataset gate on synthetic datasets built from the README's measured rates.

Field model (E3): a "hot" field hits on 19.4% of its cells, a "cold" field on q_cold.
Dataset types:
  dead     : 300 fields, all cold at 0.3%  (stopped datasets measured 0.22%, E2)
  few_hot  : 300 fields, 8 hot             (Dataset C: value in a few fields, E10)
  rich     : 380 fields, 37 hot            (Dataset A)
Run: python audit/gate_montecarlo.py
"""
import random, statistics, sys
sys.path.insert(0, ".")
from scanner.formula_factory import first_order_specs
from scanner.pipeline import AdaptiveScanner, ScannerConfig, DatasetState
from scanner.platform_adapter import SimulationResult

Q_HOT, Q_COLD, T = 0.194, 0.003, 56

class Synth:
    def __init__(self, hot, seed):
        self.hot, self.rng = hot, random.Random(seed)
    def simulate(self, specs):
        out = []
        for s in specs:
            q = Q_HOT if s.field_key in self.hot else Q_COLD
            hit = self.rng.random() < q
            out.append(SimulationResult(s.candidate_key, s.field_key, 1.5 if hit else 0.1, 0.9 if hit else 0.0, 0.2, 150))
        return out
    def minimum_history_passes(self, top): return True

def run(n_fields, n_hot, reps=400):
    kept, cost = 0, []
    for r in range(reps):
        fields = [f"f{i}" for i in range(n_fields)]
        hot = set(random.Random(r).sample(fields, n_hot))
        specs = first_order_specs(fields, [f"t{j}" for j in range(T)])
        rep = AdaptiveScanner(Synth(hot, r), ScannerConfig(second_order_visit_cap=0, third_order_visit_cap=0), seed=r).run_visit(specs)
        kept += rep.state != DatasetState.ABANDONED
        cost.append(rep.simulations if rep.state == DatasetState.ABANDONED else None)
    stopped = [c for c in cost if c is not None]
    return kept / reps, (statistics.mean(stopped) if stopped else float("nan"))

if __name__ == "__main__":
    for name, n, k in [("dead", 300, 0), ("few_hot", 300, 8), ("rich", 380, 37)]:
        p, c = run(n, k)
        print(f"{name:8s} kept {p:6.1%}   mean cost when stopped {c:6.0f} sims")
