"""Design v11, one test block per item [1]..[12] of the README, plus a whole day on the synthetic market."""
import datetime
import math
import unittest

import numpy as np

from scanner import config as C
from scanner import statistics as S
from scanner.loop import run
from scanner.novelty import Clusters
from scanner.policy import Dataset, Field, Policy, Result
from tests.market import Market

FAMS = ['F01', 'F02', 'F03', 'F04']


def cal():
    return {'medoids': {f: f'{f}_t' for f in FAMS}, 'q': {'F01': 0.2, 'F02': 0.4, 'F03': 0.1, 'F04': 0.1},
            'online': {'F01': 0.05, 'F02': 0.03, 'F03': 0.02, 'F04': 0.01}, 'screen_family': 'F02',
            'dig_order': ['F01', 'F03', 'F04'], 'y': 0.2, 'dig_len': 3.0, 'p2': 0.02, 'p3': 0.001,
            'priors': {'*|*': (0.6, 5.6)}, 'R': {1: 0.0125, 2: 0.025, 3: 0.02}, 'PP1': 0.48, 'rho': {'*|*': 1.0}}


def res(key, sh, fi=None, family='F02', order=1, to=0.2):
    return Result(key, 'f', order, sh, sh * 0.7 if fi is None else fi, to, family=family)


def dataset(n=30, key='ds'):
    d = Dataset('USA', key, 'model')
    d.fields = {f'f{i}': Field(f'f{i}') for i in range(n)}
    return d


class TestFamilies(unittest.TestCase):                                     # [1]
    def test_templates_that_move_together_are_one_family(self):
        rng = np.random.default_rng(0)
        ts = ['a1', 'a2', 'b1', 'b2']
        prof = {}
        for j in range(200):
            x, y = rng.normal(), rng.normal()
            prof[j] = {'a1': x + rng.normal(0, .1), 'a2': x + rng.normal(0, .1), 'b1': y + rng.normal(0, .1),
                       'b2': -y + rng.normal(0, .1)}                         # a mirror image is the same signal
        fam, med = S.template_families(prof, ts)
        self.assertEqual(fam['a1'], fam['a2'])
        self.assertEqual(fam['b1'], fam['b2'])
        self.assertNotEqual(fam['a1'], fam['b1'])
        self.assertEqual(len(med), 2)


class TestNovelty(unittest.TestCase):                                      # [2][6]
    def test_copy_joins_and_power_pool_cut_is_stricter(self):
        rng = np.random.default_rng(1)
        z = rng.normal(size=1000)
        c = Clusters()
        self.assertTrue(c.assess('A', 'USA', z, 2.0, 'cand', True)[0])
        self.assertFalse(c.assess('B', 'USA', z + 0.3 * rng.normal(size=1000), 2.0, 'cand', True)[0])
        x = z + 1.2 * rng.normal(size=1000)                                  # correlation about 0.64
        self.assertTrue(c.assess('R', 'USA', x, 2.0, 'cand', True)[0])      # regular limit 0.7: new
        c2 = Clusters()
        c2.assess('A', 'USA', z, 2.0, 'cand', True)
        self.assertFalse(c2.assess('P', 'USA', x, 1.2, 'cand', False)[0])   # Power Pool limit 0.5: copy
        self.assertFalse(c2.assess('N', 'USA', -z, -2.0, 'cand', True)[0])  # a negative alpha is compared flipped


class TestDatasetModel(unittest.TestCase):                                 # [3][4][5]
    def test_prior_fit_recovers_the_mean(self):
        rng = np.random.default_rng(2)
        lls = []
        for _ in range(60):
            th = rng.beta(1, 9)
            lls.append(S.field_loglik([[('F', rng.random() < (0.4 if rng.random() < th else 0.0015))] for _ in range(150)],
                                      {'F': 0.4}))
        a, b = S.fit_beta_prior(lls)
        self.assertAlmostEqual(a / (a + b), 0.1, delta=0.04)

    def test_six_good_fields_beat_one_field_six_times(self):
        q = {'F': 0.5}
        m = lambda obs: float((S.posterior(1, 9, S.field_loglik(obs, q)) * S.THETA).sum())
        self.assertLess(m([[('F', True)] + [('F', False)] * 5]), m([[('F', True)] for _ in range(6)]))

    def test_a_miss_lowers_a_fields_chance(self):
        self.assertAlmostEqual(S.post_good(0.024, [0.53]), 0.024 * 0.47 / (0.024 * 0.47 + 0.976))

    def test_thompson_probabilities_are_exact(self):
        p = Policy(cal())
        ds = [dataset(key=k) for k in 'abc']
        rng = np.random.default_rng(0)
        for _ in range(3):
            self.assertAlmostEqual(p.thompson(ds, rng)[3], 1 / 3, delta=0.02)

    def test_rescreen_only_when_no_untried_field_is_left(self):
        p = Policy(cal())
        d = dataset(n=3)
        self.assertEqual(p.screen_option(d)[0], 'screen')
        for f in d.fields.values():
            f.rows['F02'] = res(f'{f.key}x', 0.1)
        o = p.screen_option(d)
        self.assertEqual((o[0], o[2]), ('rescreen', 'F01'))


class TestFieldActions(unittest.TestCase):                                 # [5][6][8][9][12]
    def setUp(self):
        self.p, self.d = Policy(cal()), dataset()
        self.f = self.d.fields['f0']

    def kinds(self):
        return sorted(a[1] for a in self.p.fixed_actions(self.d))

    def test_new_good_field_digs_and_runs_second_order(self):
        self.f.rows['F02'] = res('h', 1.3, 0.8)
        self.f.new = True
        self.assertEqual(self.kinds(), ['dig', 'order2'])
        dig = [a for a in self.p.fixed_actions(self.d) if a[1] == 'dig'][0]
        self.assertEqual(dig[3][0]['family'], 'F01')
        self.assertAlmostEqual(dig[0], 0.05 * 0.0125)
        o2 = [a for a in self.p.fixed_actions(self.d) if a[1] == 'order2'][0]
        self.assertEqual(len(o2[3]), C.VARIANTS)

    def test_copy_or_qualified_field_stops(self):
        self.f.rows['F02'] = res('h', 1.3, 0.8)
        self.f.new = False
        self.assertEqual(self.kinds(), [])
        self.f.new, self.f.rows['F01'] = True, res('q', 1.9, 1.3, 'F01')
        self.assertEqual(self.kinds(), [])

    def test_member_specific_failure_reopens_the_field(self):
        self.f.rows['F02'] = res('q', 1.9, 1.3)
        self.f.new = True
        self.assertEqual(self.kinds(), [])
        self.f.verdicts[1] = 'fail'
        self.assertEqual(self.kinds(), ['dig', 'order2'])

    def test_negative_qualifying_alpha_is_flipped_once(self):
        self.f.rows['F02'] = res('n', -1.9, -1.3)
        acts = self.p.fixed_actions(self.d)
        self.assertEqual([(a[1], a[3][0]['flip_of']) for a in acts], [('flip1', 'n')])
        self.f.flips.add('n')
        self.assertEqual(self.p.fixed_actions(self.d), [])

    def test_luck_margin(self):
        self.assertAlmostEqual(C.LUCK_MARGIN, (1 / math.sqrt(10)) * math.sqrt(2 * math.log(12)))
        self.assertTrue(S.beats_parent(2.1, 1.3))
        self.assertFalse(S.beats_parent(1.9, 1.3))

    def test_variant_set_is_never_cut(self):
        self.f.rows['F02'] = res('h', 1.3, 0.8)
        self.f.new = True
        plan = self.p.plan([self.d], 5, np.random.default_rng(0))
        self.assertNotIn('order2', [x.kind for x in plan])

    def test_error_pause_and_lit_cell(self):
        self.d.err_today = C.ERROR_PAUSE
        self.assertFalse(self.p.eligible(self.d, ()))
        d2 = dataset(key='d2')
        self.assertFalse(self.p.eligible(d2, {'USA|model'}))

    def test_power_pool_route_closes_when_the_quota_is_covered(self):
        p = Policy(cal(), ('USA',), datetime.date(2026, 11, 22))
        today = datetime.date(2026, 11, 20)
        self.assertTrue(p.pp_open('USA', today))
        p.pp_waiting['USA'] = 3
        self.assertFalse(p.pp_open('USA', today))


class TestShrinkage(unittest.TestCase):                                    # [7]
    def test_fit_and_shrink(self):
        rng = np.random.default_rng(3)
        s = np.where(rng.random(4000) < 0.8, 0, rng.normal(0, 0.7, 4000))
        pi0, tau = S.fit_sharpe_prior(s + rng.normal(0, C.SHARPE_SE, 4000))
        self.assertAlmostEqual(pi0, 0.8, delta=0.05)
        self.assertLess(S.shrink(1.0, pi0, tau)[0], 1.0)


class TestRound(unittest.TestCase):                                        # [11]
    def test_random_share_and_no_repeats(self):
        p = Policy(cal())
        ds = [dataset(key='a'), dataset(key='b')]
        plan = p.plan(ds, C.ROUND, np.random.default_rng(0))
        rnd = [x for x in plan if x.kind == 'random']
        self.assertEqual(len(rnd), C.RANDOM_PER_ROUND)
        self.assertAlmostEqual(rnd[0].prob, 1 / (2 * 30 * 4))
        keys = [(x.dataset.key, x.field.key, tuple(sorted(x.spec.items()))) for x in plan]
        self.assertEqual(len(keys), len(set(keys)))


class TestDay(unittest.TestCase):                                          # whole day on the synthetic market
    def test_day(self):
        m = Market(cal(), n_datasets=12, seed=5)
        picks, cands = run(Policy(cal()), m.datasets, m, budget=800, seed=1)
        self.assertEqual(m.sims, len(picks))
        self.assertLessEqual(m.sims, 800)
        self.assertTrue({'random', 'screen'} <= {x.kind for x in picks})
        keys = [(x.dataset.key, x.field.key, tuple(sorted(x.spec.items()))) for x in picks]
        self.assertEqual(len(keys), len(set(keys)))                          # nothing simulated twice


if __name__ == '__main__':
    unittest.main()
