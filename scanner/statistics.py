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

    ``p_bad`` and ``p_good`` bracket the 1% worth-mining line. ``miss_good``
    is the tolerated probability of abandoning a good dataset and
    ``keep_bad`` the tolerated probability of retaining a bad one.
    """

    p_bad: float = 0.005
    p_good: float = 0.02
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

