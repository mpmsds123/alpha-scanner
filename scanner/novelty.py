"""[2][6] Same signal or new: daily-PnL correlation (last CORR_DAYS days, oriented by the sign of Sharpe) against every
cluster representative of the region. Above the cutoff: a copy; otherwise a new cluster, and a new representative."""
import numpy as np

from . import config as C


class Clusters:
    def __init__(self):
        self.reps = {}            # region -> list of (key, kind, oriented daily PnL)

    @staticmethod
    def _orient(daily, sharpe):
        x = np.asarray(daily, float)[-C.CORR_DAYS:]
        return -x if (sharpe or 0) < 0 else x

    def max_corr(self, region, x, only_cand):
        best, near = None, None
        for key, kind, y in self.reps.get(region, []):
            if only_cand and kind != 'cand':
                continue
            n = min(len(x), len(y))
            if n < C.MIN_OVERLAP:
                continue
            a, b = x[-n:], y[-n:]
            if a.std() == 0 or b.std() == 0:
                continue
            c = float(np.corrcoef(a, b)[0, 1])
            if best is None or c > best:
                best, near = c, key
        return best, near

    def assess(self, key, region, daily, sharpe, scope, regular):
        """scope 'field' (cutoff 0.7, against all) or 'cand' (cutoff 0.7 regular / 0.5 Power Pool, against candidates).
        Returns (new?, max correlation, nearest)."""
        x = self._orient(daily, sharpe)
        corr, near = self.max_corr(region, x, scope == 'cand')
        cut = C.CUT_REGULAR if scope == 'field' or regular else C.CUT_PP
        new = corr is None or corr <= cut
        if new:
            self.reps.setdefault(region, []).append((key, 'cand' if scope == 'cand' else 'field', x))
        return new, corr, near
