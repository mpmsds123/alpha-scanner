"""A synthetic market that implements the platform adapter, built from fitted numbers, for tests and comparisons.

- dataset: share of good fields theta ~ Beta(a, b); 30-300 fields
- good field: true Sharpe |N(0, tau)| on one signal cluster (a copy of an existing one with chance 1 - nu)
- first order: a family carries the field's signal with chance q[family]; measured Sharpe = true + N(0, 0.316)
- second / third order: parent's true Sharpe + N(0, 0.15)
- daily PnL: 0.8 x cluster series + 0.4 x noise for alphas with signal, noise otherwise (copies correlate about 0.8)
- accepted (truth, for scoring only): clears the line and true Sharpe >= 1.2"""
import zlib

import numpy as np

from scanner.policy import Dataset, Result

DAYS, SE = 1000, 1 / np.sqrt(10)


class Market:
    def __init__(self, cal, n_datasets=60, seed=0, a=0.53, b=4.18, tau=0.6, nu=0.42, regions=('USA', 'EUR', 'ASI')):
        self.rng = np.random.default_rng(seed)
        self.q = cal['q']
        self.datasets, self.truth, self.series, self.alphas = [], {}, {}, {}
        n_c = {r: 0 for r in regions}
        for i in range(n_datasets):
            region = regions[i % len(regions)]
            d = Dataset(region, f'd{i:03d}', 'model')
            d.n = int(self.rng.integers(30, 300))
            theta = self.rng.beta(a, b)
            for j in range(d.n):
                if self.rng.random() < theta:
                    if n_c[region] and self.rng.random() > nu:
                        c = f'{region}{int(self.rng.integers(n_c[region]))}'
                    else:
                        c = f'{region}{n_c[region]}'
                        n_c[region] += 1
                        self.series[c] = self.rng.normal(size=DAYS)
                    self.truth[(d.key, f'f{j}')] = (abs(self.rng.normal(0, tau)), c,
                                                    1 if zlib.crc32(f'{d.key}{j}'.encode()) % 2 else -1)
            self.datasets.append(d)
        self.sims = 0

    def fields(self, d):
        return [f'f{j}' for j in range(d.n)]

    def simulate(self, picks):
        out = []
        for p in picks:
            self.sims += 1
            t = self.truth.get((p.dataset.key, p.field.key))
            s = p.spec
            true, cluster = 0.0, None
            if t is not None:
                if s['order'] == 1 and not s.get('flip_of'):
                    carry = zlib.crc32(f'{p.dataset.key}{p.field.key}{s["family"]}'.encode()) % 10000 / 10000 < self.q[s['family']]
                    if carry:
                        true, cluster = t[0] * t[2], t[1]
                elif s.get('flip_of'):
                    prev = self.alphas[s['flip_of']]
                    true, cluster = -prev['true'], prev['cluster']
                else:
                    parent = self.alphas.get(s['parent'].lstrip('-'), {'true': t[0]})
                    true, cluster = abs(parent['true']) + self.rng.normal(0, 0.15), t[1]
                    if s['order'] == 3:
                        true *= 0.9
            sh = true + self.rng.normal(0, SE)
            daily = (0.8 * self.series[cluster] * np.sign(true or 1) + 0.4 * self.rng.normal(size=DAYS)
                     if cluster else self.rng.normal(size=DAYS)) + 0.06 * sh
            key = f'a{self.sims}'
            self.alphas[key] = {'true': true, 'cluster': cluster, 'sharpe': sh}
            r = Result(key, p.field.key, s['order'], round(float(sh), 2), round(float(sh * 0.75), 2),
                       float(self.rng.uniform(0.05, 0.4)), family=s.get('family'))
            out.append((r, daily))
        return out

    def accepted(self):
        """Distinct clusters with an alpha that clears the line and has true Sharpe >= 1.2."""
        return {a['cluster'] for a in self.alphas.values()
                if a['cluster'] and a['sharpe'] >= 1.58 and a['sharpe'] * 0.75 >= 1 and a['true'] >= 1.2}
