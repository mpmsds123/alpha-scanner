"""Pure statistics of design v11. No platform, no files."""
import math

import numpy as np

from . import config as C


# ---------------------------------------------------------------- [1] template families
def average_linkage(dist, cut):
    """Agglomerative clustering, average linkage, on a square distance matrix; stops when the closest pair of clusters
    is farther apart than `cut`. Returns clusters as lists of indices."""
    clusters = [[i] for i in range(len(dist))]
    while len(clusters) > 1:
        best, pair = None, None
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                d = float(np.mean([dist[i][j] for i in clusters[a] for j in clusters[b]]))
                if best is None or d < best:
                    best, pair = d, (a, b)
        if best > cut:
            break
        a, b = pair
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]
    return clusters


def template_families(profile, templates):
    """profile = {field: {template: signed Sharpe}}. Returns ({template: family}, {family: medoid template}).
    Two templates are one family when their Sharpe across shared fields correlates |r| >= FAMILY_CORR; the medoid is
    the member with the highest mean |r| to the rest (a fixed member, not the best scorer)."""
    idx = {t: i for i, t in enumerate(templates)}
    M = np.full((len(profile), len(templates)), np.nan)
    for i, d in enumerate(profile.values()):
        for t, v in d.items():
            M[i, idx[t]] = v
    n = len(templates)
    R = np.eye(n)
    for a in range(n):
        for b in range(a + 1, n):
            m = ~np.isnan(M[:, a]) & ~np.isnan(M[:, b])
            ok = m.sum() >= C.FAMILY_MIN_SHARED and M[m, a].std() > 0 and M[m, b].std() > 0
            R[a, b] = R[b, a] = np.corrcoef(M[m, a], M[m, b])[0, 1] if ok else 0.0
    fam, med = {}, {}
    for g in sorted(average_linkage(1 - np.abs(R), 1 - C.FAMILY_CORR), key=min):
        key = f'F{len(med) + 1:02d}'
        m = max(g, key=lambda i: np.mean([abs(R[i, j]) for j in g])) if len(g) > 1 else g[0]
        med[key] = templates[m]
        for i in g:
            fam[templates[i]] = key
    return fam, med


# ---------------------------------------------------------------- [7] signal or noise
def _npdf(x, s):
    return np.exp(-0.5 * (np.asarray(x, float) / s) ** 2) / (s * math.sqrt(2 * math.pi))


def fit_sharpe_prior(x, se=C.SHARPE_SE):
    """Empirical Bayes: true Sharpe is 0 with probability pi0, else N(0, tau^2); measured = true + N(0, se^2).
    Maximum likelihood on a grid. Returns (pi0, tau)."""
    x = np.asarray(x, float)
    best = None
    for tau in np.arange(0.05, 3.001, 0.05):
        f0, f1 = _npdf(x, se), _npdf(x, math.sqrt(se ** 2 + tau ** 2))
        for pi0 in np.arange(0.0, 1.0001, 0.005):
            ll = float(np.log(pi0 * f0 + (1 - pi0) * f1 + 1e-300).sum())
            if best is None or ll > best[0]:
                best = (ll, pi0, tau)
    return float(best[1]), float(best[2])


def shrink(x, pi0, tau, se=C.SHARPE_SE):
    """(posterior mean of the true Sharpe, probability of real signal) for a measured Sharpe x."""
    f0, f1 = _npdf(x, se), _npdf(x, math.sqrt(se ** 2 + tau ** 2))
    p1 = (1 - pi0) * f1 / ((1 - pi0) * f1 + pi0 * f0)
    return float(p1 * x * tau ** 2 / (tau ** 2 + se ** 2)), float(p1)


# ---------------------------------------------------------------- [8] best-of-N luck
def expected_max_noise(n, se=C.SHARPE_SE):
    """Large-n approximation of the best of n signal-free Sharpes: se * sqrt(2 ln n)."""
    return se * math.sqrt(2 * math.log(n)) if n > 1 else 0.0


def beats_parent(child, parent, margin=C.LUCK_MARGIN):
    return child is not None and parent is not None and child > parent + margin


# ---------------------------------------------------------------- [3][5] datasets: field-level Bayes on a grid
THETA = (np.arange(C.THETA_GRID) + 0.5) / C.THETA_GRID * 0.5     # share of good fields, 0 .. 50%


def field_loglik(fields, q, noise=C.NOISE):
    """log P(results of one dataset | theta) on THETA. fields = [[(family, hit), ...] per field]. A field is good with
    probability theta; on a good field family f hits with probability q[f]; a field without signal hits only by noise.
    Repeats on one field are handled exactly: the field is the unit."""
    ll = np.zeros_like(THETA)
    for obs in fields:
        lg = sum(math.log(q[f] if h else 1 - q[f]) for f, h in obs)
        lb = sum(math.log(noise if h else 1 - noise) for _, h in obs)
        m = max(lg, lb)
        ll += np.log(THETA * math.exp(lg - m) + (1 - THETA) * math.exp(lb - m)) + m
    return ll


def beta_logpdf(a, b):
    return (a - 1) * np.log(THETA) + (b - 1) * np.log(1 - THETA) - (math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))


def fit_beta_prior(logliks):
    """Empirical Bayes Beta(a, b) maximising the summed marginal likelihood of the datasets' results."""
    best, dx, L = None, THETA[1] - THETA[0], np.vstack(logliks)
    for mean in np.exp(np.linspace(np.log(0.0005), np.log(0.3), 60)):
        for k in np.exp(np.linspace(0, np.log(1000), 50)):
            z = beta_logpdf(mean * k, (1 - mean) * k)[None, :] + L
            m = z.max(1)
            tot = float((m + np.log(np.exp(z - m[:, None]).sum(1) * dx)).sum())
            if best is None or tot > best[0]:
                best = (tot, mean * k, (1 - mean) * k)
    return float(best[1]), float(best[2])


def posterior(a, b, ll):
    z = beta_logpdf(a, b) + ll
    w = np.exp(z - z.max())
    return w / w.sum()


def post_good(theta, q_tried):
    """P(field is good | every family tried on it missed)."""
    miss = float(np.prod([1 - q for q in q_tried])) if q_tried else 1.0
    return theta * miss / (theta * miss + (1 - theta))
