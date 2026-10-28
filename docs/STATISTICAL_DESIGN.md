# Statistical Design (v7)

Version: v7 · Status: in force · Changes only at scheduled reviews (see [PROGRESS.md](PROGRESS.md)).

**Problem.** A fixed simulation budget (4,000 per day) must be spread over hundreds of datasets, each with up to thousands of fields and 56 formula templates per field. Testing everything is impossible, so the scanner first *samples* each dataset to decide whether it deserves more budget.

## 1. What is measured

| Item | Value | Reason |
|---|---|---|
| Unit of work | one cell = one field × one template = one simulation | the platform returns one backtest per formula |
| Hit | \|Sharpe\| ≥ 1.0 and 1% ≤ turnover ≤ 70% | turnover range is the platform's submission range; a Sharpe of 1 is about 3.2 standard deviations of pure noise over 10 years (σ ≈ 1/√10 ≈ 0.316), so a hit is unlikely by luck alone |
| Noise hit rate | 0.15654% | measured from simulations with no signal; matches the normal approximation P(\|Z\| ≥ 3.16) ≈ 0.157% for a 10-year history. It is much larger for shorter histories (≈2.5% at 5 years), so it must be re-checked per region |
| Templates | 56 = 1 raw + 11 time-series operators × 5 windows (5, 22, 66, 120, 240 days) | windows roughly cover week, month, quarter, half-year and year; the set is inherited from earlier versions and its coverage is assumption 1 |
| Field wrapper | back-fill, then winsorize at 4 standard deviations | removes gaps and extreme values before any template; inherited, not re-tested |

## 2. The dataset gate (sequential test)

For each dataset the unknown hit rate is *p*. Two hypotheses are compared:

- **Bad dataset (H0):** p = 0.5%. Reason: about three times the noise rate, so "slightly above luck" counts as bad.
- **Good dataset (H1):** p = 5%. Reason: the high-yield group in the current data fits at about 6% (see PROGRESS.md); 5% is a rounded, slightly conservative value.

Error budgets: keep a bad dataset at most **10%** of the time; abandon a good one at most **5%** of the time. Reason for the asymmetry: wrongly keeping a bad dataset costs roughly 100–200 simulations, wrongly abandoning a good one loses the whole dataset.

Each simulation adds a score: a hit adds **+2.303**, a miss subtracts **0.0463**. Stop and keep when the score reaches **+2.251**; stop and abandon when it falls to **−2.890**.

Plain reading: with no hits at all the score falls below −2.89 after 63 misses, so a dataset with zero hits in the first round of 80 is abandoned immediately. Three hits in the first 80 are enough to keep it. The two hypotheses are equally likely at a hit rate of **1.97%**, which is the effective retain/abandon line.

| Setting | Value | Reason |
|---|---|---|
| Looks | every 80 simulations | one round = 8 batches × 10 simulations = the platform's 10 concurrent slots, all in flight at once |
| Sampling inside a round | 80 *different* fields, one random template each | fields in the same dataset are correlated; spreading a round over distinct fields limits that |
| Cap | 1,600 simulations (20 looks) | pragmatic bound on cost per dataset; **not derived** (open item) |
| At the cap | keep if score ≥ 0 (≥ 32 hits) | tie-break at the neutral point |

Exact operating characteristics are in the README.

## 3. After the gate

1. **Adaptive sampling.** In a kept dataset, remaining templates of fields that already hit are tested first; nothing is deleted, only reordered. Reason: same-field variants are strongly correlated (Sharpe correlation 0.70–0.87 across adjacent windows).
2. **Stage escalation.** First-order results that pass a gate (|Sharpe| ≥ 1.2, fitness ≥ 0.7, > 100 positions; best 100, at most 5 per field and sign; negative signals flipped) get second-order variants (group wrappers); second-order results passing a stricter gate (1.3 / 0.8, best 200) get third-order variants (open/exit conditions).
3. **Budget per visit.** 2,000 / 1,000 / 1,000 simulations for the three stages, of a 4,000 daily budget (5,000 platform quota minus 1,000 reserved for another pipeline). The split is a design choice, not an optimum.
4. **Luck share.** n × 0.15654% ÷ observed hits estimates the share of hits expected from noise alone. It assumes every tested cell is pure noise (the most pessimistic case), so it is an upper bound on the luck share, not a formal false-discovery rate.

## 4. Known biases

- Later-stage hit rates (≈ 66% and 84%) describe already-selected populations and overstate true quality (winner's curse).
- Only the first, random rounds give unbiased hit-rate estimates. After the gate, sampling is adaptive and must not be used naively to estimate rates.
- All evaluation is in-sample. The platform's own checks are the only out-of-sample-like filter.

The full list of assumptions is in [ASSUMPTIONS.md](ASSUMPTIONS.md).
