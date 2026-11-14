"""Statistical decisions used by the scanner.

The module contains no platform calls or research identifiers.  It implements
the design described in the accompanying statistical note: a Wald sequential
probability ratio test (SPRT) for dataset gating and a transparent, approximate
false-discovery calculation for first-order hits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable


class SPRTDecision(str, Enum):
    CONTINUE = "continue"
    MINE = "mine"
    ABANDON = "abandon"


@dataclass(frozen=True)
class SPRTConfig:
    """Two-point Bernoulli SPRT configuration.

    ``p_bad`` and ``p_good`` bracket the ~2% indifference rate (the rate at which the test is
    equally likely to retain or abandon). ``miss_good``
    is the tolerated probability of abandoning a good dataset and
    ``keep_bad`` the tolerated probability of retaining a bad one.
    """

    p_bad: float = 0.005
    p_good: float = 0.05
    miss_good: float = 0.05
    keep_bad: float = 0.10
    cap: int = 1_600

    def __post_init__(self) -> None:
        if not 0 < self.p_bad < self.p_good < 1:
            raise ValueError("require 0 < p_bad < p_good < 1")
        if not 0 < self.miss_good < 1 or not 0 < self.keep_bad < 1:
            raise ValueError("error tolerances must be probabilities")
        if self.cap <= 0:
            raise ValueError("cap must be positive")

    @property
    def upper(self) -> float:
        return math.log((1 - self.miss_good) / self.keep_bad)

    @property
    def lower(self) -> float:
        return math.log(self.miss_good / (1 - self.keep_bad))


class SequentialTest:
    """Accumulate Bernoulli outcomes and return the current SPRT decision."""

    def __init__(self, config: SPRTConfig | None = None) -> None:
        self.config = config or SPRTConfig()
        self.hits = 0
        self.trials = 0

    @property
    def log_likelihood_ratio(self) -> float:
        c = self.config
        misses = self.trials - self.hits
        return (
            self.hits * math.log(c.p_good / c.p_bad)
            + misses * math.log((1 - c.p_good) / (1 - c.p_bad))
        )

    def update(self, outcomes: Iterable[bool]) -> SPRTDecision:
        batch = list(outcomes)
        self.trials += len(batch)
        self.hits += sum(batch)
        return self.decision()

    def decision(self) -> SPRTDecision:
        score = self.log_likelihood_ratio
        if score >= self.config.upper:
            return SPRTDecision.MINE
        if score <= self.config.lower:
            return SPRTDecision.ABANDON
        if self.trials >= self.config.cap:
            return SPRTDecision.MINE if score >= 0 else SPRTDecision.ABANDON
        return SPRTDecision.CONTINUE


@dataclass(frozen=True)
class FieldTestConfig:
    """Per-field SPRT: is this field hot (q_hot) or cold (q_cold)?

    Rates are the README E3 measurement: cells of a field that already hit
    hit again 19.4%; other cells 2.2%. The field's triggering hit is excluded
    from the test, because the field was selected for testing on that hit.
    """

    q_cold: float = 0.022
    q_hot: float = 0.194
    miss_hot: float = 0.05
    keep_cold: float = 0.05
    cap: int = 30

    def as_sprt(self) -> SPRTConfig:
        return SPRTConfig(
            p_bad=self.q_cold, p_good=self.q_hot,
            miss_good=self.miss_hot, keep_bad=self.keep_cold, cap=self.cap,
        )


def screening_probes_needed(pi_min: float, q_hot: float, miss: float) -> int:
    """Distinct-field probes F so that a dataset whose hot-field share is at
    least ``pi_min`` shows no screening hit with probability at most ``miss``.

    One probe = one random template on one never-probed field, so it hits a
    hot field's signal with probability pi_min * q_hot.
        F = ln(miss) / ln(1 - pi_min * q_hot)
    """

    if not (0 < pi_min <= 1 and 0 < q_hot <= 1 and 0 < miss < 1):
        raise ValueError("invalid screening design inputs")
    return math.ceil(math.log(miss) / math.log(1 - pi_min * q_hot))


def expected_noise_hits(trials: int, noise_hit_rate: float = 0.0015654) -> float:
    """Expected threshold crossings under the documented 10-year noise model."""

    if trials < 0 or not 0 <= noise_hit_rate <= 1:
        raise ValueError("invalid trials or noise_hit_rate")
    return trials * noise_hit_rate


def estimated_fdr(trials: int, observed_hits: int, noise_hit_rate: float = 0.0015654) -> float | None:
    """Expected noise hits divided by observed hits; not a corrected q-value."""

    if observed_hits < 0:
        raise ValueError("observed_hits cannot be negative")
    if observed_hits == 0:
        return None
    return expected_noise_hits(trials, noise_hit_rate) / observed_hits

