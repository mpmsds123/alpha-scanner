"""What to simulate next. Every possible next simulation gets one score:

    score = estimated chance this simulation produces a NEW alpha the platform will accept

and each round runs the highest scores; screens compete through Thompson draws.

Calibration `cal` (fitted from the run logs):
  families {template: family}, medoids {family: template}, q {family}: P(medoid hits | good field),
  online {family}: P(medoid clears the line | good field), screen_family, dig_order, y (P a good field reaches the line
  in its dig), dig_len, p2, p3 (P one variant beats its parent by the luck margin and clears the line),
  priors {pool: (a, b)}, R {order: platform regular pass rate}, PP1 (Power Pool pass rate), rho {pool: prod factor}.

Scores (rho = prod-correlation factor of the dataset's region x type):
  flip     negative alpha that clears the line, run with its sign flipped           pass rate of its route * rho
  dig      next family on a good, new field without a qualifying alpha              online[f] * R1 * rho
  order2   12 variants of the field's best hit, run as one set                      p2 * R2 * rho, each
  order3   12 variants of the best child that beat its parent by the margin         p3 * R3 * rho, each
  screen   10 untried fields of one dataset, screen family                          Thompson draw of g*nu*V/(1+g*nu*L),
           g = theta * q_screen; nu = P(a hit is a new signal); V = P(a new good field ends accepted); L = its cost
  rescreen a missed field with its next family, when no untried field is left       same, g = P(good | misses) * q_next
  random   8 of every 80, uniform dataset, field and family (not scored)
"""
import datetime
from dataclasses import dataclass, field as dfield

import numpy as np

from . import config as C
from . import statistics as S


@dataclass
class Result:
    key: str
    field: str
    order: int
    sharpe: float
    fitness: float
    turnover: float
    family: str = None            # first order only
    flipped: bool = False
    positions: int = 400
    error: bool = False

    @property
    def hit(self):
        return (not self.error and abs(self.sharpe) >= C.HIT_SHARPE
                and C.HIT_TURNOVER[0] <= self.turnover <= C.HIT_TURNOVER[1])

    @property
    def on_line(self):
        return self.hit and abs(self.sharpe) >= C.REG_BAR[0] and abs(self.fitness) >= C.REG_BAR[1]


@dataclass
class Field:
    key: str
    rows: dict = dfield(default_factory=dict)       # family -> first-order Result (unflipped)
    flips: set = dfield(default_factory=set)        # keys of results already re-run flipped
    o2: list = dfield(default_factory=list)
    o3: list = dfield(default_factory=list)
    new: bool = None                                 # novelty of its first hit: True new, False copy, None undecided
    evidence: list = dfield(default_factory=list)   # (family, hit) from screens and random picks
    verdicts: dict = dfield(default_factory=dict)   # order -> 'pass' | 'fail' | 'fail_hard' | 'submitted'


@dataclass
class Dataset:
    region: str
    key: str
    kind: str
    fields: dict = None                              # key -> Field, once the field list is known
    err_today: int = 0
    ver: int = 0
    _post: tuple = None


@dataclass
class Pick:
    kind: str
    dataset: Dataset
    field: Field
    spec: dict                                       # abstract: order, family, parent key, variant index, flip of
    score: float
    prob: float


class Policy:
    def __init__(self, cal, theme_regions=(), theme_end=None, pp_waiting=None):
        self.cal = cal
        self.med = cal['medoids']
        self.nu = list(C.NU_PRIOR)
        self.theme_regions, self.theme_end = tuple(theme_regions), theme_end
        self.pp_waiting = dict(pp_waiting or {})

    # ---------------------------------------------------------------- routes
    def pp_open(self, region, today=None):
        """Pure Power Pool is worth finding: theme active in this region and the waiting alphas don't cover the quota."""
        today = today or datetime.date.today()
        if region not in self.theme_regions or self.theme_end is None or today > self.theme_end:
            return False
        return self.pp_waiting.get(region, 0) < (self.theme_end - today).days + 1

    def route(self, r, region):
        if not r.hit:
            return None
        if r.on_line:
            return 'regular'
        return 'pp' if self.pp_open(region) else None

    def pools(self, d):
        return (f'{d.region}|{d.kind}', f'{d.region}|*', '*|*')

    def rho(self, d):
        return next((self.cal['rho'][p] for p in self.pools(d) if p in self.cal['rho']), 1.0)

    def prior(self, d):
        return next((tuple(self.cal['priors'][p]) for p in self.pools(d) if p in self.cal['priors']), (0.6, 5.6))

    # ---------------------------------------------------------------- dataset model [3]
    def posterior(self, d):
        n = sum(len(f.evidence) for f in (d.fields or {}).values())
        if d._post is not None and d._post[0] == n:
            return d._post[1]
        a, b = self.prior(d)
        w = S.posterior(a, b, S.field_loglik([f.evidence for f in (d.fields or {}).values() if f.evidence], self.cal['q']))
        d._post = (n, w)
        return w

    def field_value(self, d):
        """(V, L): chance a new good field ends accepted, and the simulations its follow-up costs."""
        if self.pp_open(d.region):
            return self.cal['PP1'], 1.0
        rho, y, R = self.rho(d), self.cal['y'], self.cal['R']
        p2 = self.cal['p2'] * R[2] * rho
        return y * R[1] * rho + (1 - y) * (1 - (1 - p2) ** C.VARIANTS), self.cal['dig_len'] + (1 - y) * C.VARIANTS

    # ---------------------------------------------------------------- field state [5][6]
    def tried(self, f):
        return set(f.rows)

    def best_hit(self, f):
        hits = [r for r in f.rows.values() if r.hit]
        return max(hits, key=lambda r: abs(r.sharpe)) if hits else None

    def qualified(self, d, f):
        """The field has an alpha that can be submitted, or one waiting for its check: it stops."""
        if 'submitted' in f.verdicts.values():
            return True
        for order, rows in ((1, f.rows.values()), (2, f.o2), (3, f.o3)):
            open_again = f.verdicts.get(order) == 'fail'           # member-specific failure: another formula may pass
            if any(self.route(r, d.region) for r in rows) and not open_again:
                return True
        return False

    def fixed_actions(self, d):
        out = []
        if d.fields is None:
            return out
        rho, R = self.rho(d), self.cal['R']
        for f in d.fields.values():
            for order, rows in ((1, f.rows.values()), (2, f.o2), (3, f.o3)):          # [9] flips
                for r in rows:
                    route = self.route(r, d.region)
                    if route and r.sharpe < 0 and not r.flipped and r.key not in f.flips:
                        p = self.cal['PP1'] if route == 'pp' else R[order] * rho
                        out.append((p, f'flip{order}', f, [{'order': order, 'flip_of': r.key, 'family': r.family}]))
            best = self.best_hit(f)
            if best is None or f.new is not True or self.qualified(d, f):
                continue
            nxt = [g for g in self.cal['dig_order'] if g not in self.tried(f)]
            if nxt and not self.pp_open(d.region):                                      # dig
                out.append((self.cal['online'][nxt[0]] * R[1] * rho, 'dig', f, [{'order': 1, 'family': nxt[0]}]))
            if not f.o2:                                                                 # [8] second order
                if abs(best.sharpe) >= C.ORDER2_GATE[0] and abs(best.fitness) >= C.ORDER2_GATE[1] \
                        and best.positions > C.MIN_POSITIONS:
                    out.append((self.cal['p2'] * R[2] * rho, 'order2', f,
                                [{'order': 2, 'parent': best.key, 'variant': i} for i in range(C.VARIANTS)]))
            elif not f.o3:                                                               # [8] third order
                kids = [r for r in f.o2 if S.beats_parent(r.sharpe, abs(best.sharpe))]
                src = max(kids, key=lambda r: r.sharpe) if kids else best
                if abs(src.sharpe) >= C.ORDER3_GATE[0] and abs(src.fitness) >= C.ORDER3_GATE[1]:
                    out.append((self.cal['p3'] * R[3] * rho, 'order3', f,
                                [{'order': 3, 'parent': src.key, 'variant': i} for i in range(C.VARIANTS)]))
        return out

    # ---------------------------------------------------------------- screens: Thompson sampling [4]
    def screen_option(self, d):
        q, s = self.cal['q'], self.cal['screen_family']
        if d.fields is None:
            return ('screen', None, s, lambda th: th * q[s])
        untried = [f for f in d.fields.values() if not f.rows]
        if untried:
            return ('screen', untried, s, lambda th: th * q[s])
        best = None
        for f in d.fields.values():
            if self.best_hit(f) is not None:
                continue
            left = [g for g in self.med if g not in self.tried(f)]
            if not left:
                continue
            g = max(left, key=lambda g: q[g])
            key = (sum(np.log(1 - q[x]) for x in self.tried(f)), q[g])
            if best is None or key > best[0]:
                best = (key, f, g, [q[x] for x in self.tried(f)])
        if best is None:
            return None
        _, f, g, qt = best
        return ('rescreen', [f], g, lambda th: S.post_good(th, qt) * q[g])

    def value_fn(self, d, g):
        V, L = self.field_value(d)
        nu = self.nu[0] / sum(self.nu)
        return lambda th: (g(th) * nu) * V / (1 + g(th) * nu * L)

    def thompson(self, datasets, rng):
        """One pick: draw theta for every dataset, value it, take the largest. Returns (dataset, option, value,
        exact selection probability) or None."""
        opts, grids, cdfs = [], [], []
        for d in datasets:
            o = self.screen_option(d)
            if o is None:
                continue
            w = self.posterior(d)
            opts.append((d, o, w))
            grids.append(np.asarray(self.value_fn(d, o[3])(S.THETA), float))
            cdfs.append(np.cumsum(w))
        if not opts:
            return None
        draws = [v[rng.choice(len(w), p=w)] for (_, _, w), v in zip(opts, grids)]
        i = int(np.argmax(draws))
        d, o, w = opts[i]
        logp = np.zeros(len(w))
        for j, (v, c) in enumerate(zip(grids, cdfs)):
            if j != i:
                k = np.searchsorted(v, grids[i], side='left')
                logp += np.log(np.clip(np.where(k > 0, c[np.maximum(k - 1, 0)], 0.0), 1e-300, 1))
        return d, o, float(draws[i]), float((w * np.exp(logp)).sum())

    def eligible(self, d, lit):
        return d.err_today < C.ERROR_PAUSE and f'{d.region}|{d.kind}' not in lit

    # ---------------------------------------------------------------- one round
    def plan(self, datasets, budget, rng, lit=()):
        """[Pick] for one round of at most `budget` simulations. Datasets need a known field list."""
        ds = [d for d in datasets if self.eligible(d, lit) and d.fields]
        out, used = [], set()

        def add(kind, d, f, spec, score, prob):
            key = (d.key, f.key, tuple(sorted(spec.items())))
            if key not in used:
                used.add(key)
                out.append(Pick(kind, d, f, spec, score, prob))
        n_rand = min(C.RANDOM_PER_ROUND, budget)
        fams = sorted(self.med)
        for _ in range(n_rand * 3):                                                     # [11] random share
            if len(out) >= n_rand or not ds:
                break
            d = ds[rng.integers(len(ds))]
            f = list(d.fields.values())[rng.integers(len(d.fields))]
            g = fams[rng.integers(len(fams))]
            prob = 1 / (len(ds) * len(d.fields) * len(fams))
            if g in f.rows:
                f.evidence.append((g, f.rows[g].hit))                                     # reuse, no simulation
                continue
            add('random', d, f, {'order': 1, 'family': g}, None, prob)
        fixed = sorted([(s, k, d, f, items) for d in ds for s, k, f, items in self.fixed_actions(d)], key=lambda x: -x[0])
        left = list(ds)
        draw = self.thompson(left, rng)
        while len(out) < budget:
            if fixed and (draw is None or fixed[0][0] >= draw[2]):
                s, k, d, f, items = fixed.pop(0)
                if len(out) + len(items) > budget:
                    if k in ('order2', 'order3'):
                        continue                     # a variant set runs whole, or the luck margin would not apply
                    items = items[:budget - len(out)]
                for spec in items:
                    add(k, d, f, spec, s, 1.0)
                continue
            if draw is None:
                break
            d, (kind, flds, g, _), val, prob = draw
            pick = list(flds)
            rng.shuffle(pick)
            k = min(C.BATCH, budget - len(out))
            for f in pick[:k]:
                add(kind, d, f, {'order': 1, 'family': g}, val, prob * min(1.0, k / len(flds)))
            left.remove(d)
            draw = self.thompson(left, rng) if left else None
        return out

    # ---------------------------------------------------------------- after a round
    def record(self, pick, r):
        f, d = pick.field, pick.dataset
        d.ver += 1
        if r.error:
            d.err_today += 1
            return
        if pick.spec.get('flip_of'):
            f.flips.add(pick.spec['flip_of'])
            r.flipped = True
            {1: lambda: f.rows.__setitem__('flip:' + str(r.family), r), 2: lambda: f.o2.append(r),
             3: lambda: f.o3.append(r)}[r.order]()
            return
        if r.order == 1:
            f.rows[r.family] = r
            if pick.kind in ('random', 'screen', 'rescreen'):
                f.evidence.append((r.family, r.hit))
        else:
            (f.o2 if r.order == 2 else f.o3).append(r)
