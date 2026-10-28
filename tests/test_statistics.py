import math

from scanner.statistics import SPRTConfig, SPRTDecision, SequentialTest, estimated_fdr


def test_documented_boundaries() -> None:
    config = SPRTConfig()
    assert math.isclose(config.upper, math.log(0.95 / 0.10))
    assert math.isclose(config.lower, math.log(0.05 / 0.90))


def test_zero_hits_stop_at_first_look() -> None:
    test = SequentialTest()
    assert test.update([False] * 80) == SPRTDecision.ABANDON


def test_indifference_rate_is_about_two_percent() -> None:
    c = SPRTConfig()
    win = math.log(c.p_good / c.p_bad)
    loss = math.log((1 - c.p_good) / (1 - c.p_bad))
    assert math.isclose(-loss / (win - loss), 0.0197, abs_tol=1e-4)


def test_three_early_hits_cross_upper_boundary() -> None:
    test = SequentialTest()
    assert test.update([True] * 3 + [False] * 77) == SPRTDecision.MINE


def test_fdr_is_transparent_ratio() -> None:
    assert estimated_fdr(2_000, 347) == 2_000 * 0.0015654 / 347
    assert estimated_fdr(100, 0) is None

