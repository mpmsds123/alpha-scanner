"""The day: rounds of 80 chosen by the policy, results recorded, every first hit and every candidate compared with the
known signal clusters (daily PnL), until the budget is used. Platform checks and submission happen outside."""
import numpy as np

from . import config as C
from .novelty import Clusters
from .policy import Field


def prepare(datasets, adapter):
    for d in datasets:
        if d.fields is None:
            d.fields = {k: Field(k) for k in adapter.fields(d)}


def run(policy, datasets, adapter, budget=C.DAILY_CAP, seed=0, clusters=None, lit=()):
    """Returns (picks made, candidates found: [(dataset, field, result)])."""
    rng = np.random.default_rng(seed)
    clusters = clusters or Clusters()
    prepare(datasets, adapter)
    used, picks_all, cands = 0, [], []
    while used < budget:
        plan = policy.plan(datasets, min(C.ROUND, budget - used), rng, lit)
        if not plan:
            break
        out = adapter.simulate(plan)
        used += len(plan)
        picks_all += plan
        for pick, (r, daily) in zip(plan, out):
            policy.record(pick, r)
            d, f = pick.dataset, pick.field
            if r.error:
                continue
            if f.new is None and r.hit:                                        # first hit of the field [2]
                f.new, _, _ = clusters.assess(r.key, d.region, daily, r.sharpe, 'field', r.on_line)
                policy.nu[0 if f.new else 1] += 1
            if f.new and r.sharpe > 0 and policy.route(r, d.region):           # candidate [6]
                new, _, _ = clusters.assess(r.key, d.region, daily, r.sharpe, 'cand', r.on_line)
                if new:
                    cands.append((d, f, r))
    return picks_all, cands
