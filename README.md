# Adaptive Alpha Scanner

### One score for every simulation: allocating a fixed daily backtest budget with Bayesian search

**Design v11 · fitted on 113,183 simulation records through 2026-11-19 · weekly log in [CHANGELOG.md](CHANGELOG.md)**

## 1. Problem

- **Budget:** 4,000 backtests (simulations) a day. One simulation evaluates one formula over 10 years and returns Sharpe, fitness, turnover and daily PnL.
- **Search space:** 419 datasets, each with tens to thousands of fields. Each field has 56 first-order templates (the field itself plus 11 time-series operators × 5 windows), plus second-order (group operator) and third-order (entry condition) variants. That is millions of candidates against 4,000 a day.
- **Goal:** the most **new** alphas the platform accepts, per simulation. New = daily-PnL correlation with every alpha already found or submitted below the platform limit (0.7 regular, 0.5 Power Pool).

## 2. Conditions and solutions

Every number is fitted from the run logs at the start of each run.

| # | Condition (measured) | Type of problem | Solution |
|---|---|---|---|
| 1 | The 56 templates of a field move together: they form **14 families** (Sharpe correlation ≥ 0.7 across fields) | Redundant measurements | One fixed member (the medoid) per family. A field costs at most 14 simulations, not 56 |
| 2 | Different fields carry the same signal: 629 fields gave 267 distinct signals | Duplicate detection | Daily-PnL correlation with every known cluster. A field whose first hit copies one is not explored further |
| 3 | Good fields are rare and concentrated: mean share **11.3%**, most datasets far lower (Beta(0.53, 4.18), 95 datasets) | Estimating a rare rate per group from little data | Exact Bayesian posterior of each dataset's share of good fields. Prior fitted by empirical Bayes per region × type, falling back to the region, then to all datasets |
| 4 | Fixed budget, unknown dataset quality, results arrive by round | Explore vs exploit | Thompson sampling over datasets, with each pick's exact selection probability recorded |
| 5 | One test can miss a good field: the best family detects one **31%** of the time (644 fields) | Imperfect detection | Screen with that family. A missed field's chance of being good is updated by Bayes, and it is retested only when that still beats an untried field |
| 6 | Roughly one alpha per signal can be submitted | Diminishing returns | A field stops at its first alpha that can be submitted |
| 7 | Sharpe is noisy (s.e. 0.316 over 10 years). **75.5%** of randomly chosen alphas carry no signal; the rest have s.d. 0.60 (23,278 random rows) | Signal vs noise | Empirical Bayes shrinkage: expected true Sharpe and probability of real signal for each candidate |
| 8 | The best of N variants looks better by luck. One variant beats its parent by the luck margin and clears the line **1.81%** of the time in second order (19,048), **0.07%** in third order (13,700) | Selection bias | 12 variants per parent. A child counts only if it beats the parent by 0.316·√(2 ln 12) = **0.70** |
| 9 | 2,374 of 30,978 hits have negative Sharpe | Symmetry | A negative alpha that clears the line is re-run with its sign flipped, once |
| 10 | Other users' alphas are hidden; prod correlation passes **80%** (535 of 667 verdicts) | Unobservable outcome | Pass rate by region × type from past verdicts, multiplied into the score |
| 11 | The scanner's own choices bias its data | Adaptive sampling bias | 8 of every 80 simulations are uniform random (dataset, field, family); estimates are refitted from them |
| 12 | 2,120 of 2,284 platform errors came from 2 datasets | Operational | A dataset with 20 errors in a day is skipped for the rest of the day |

## 3. One score

Every possible next simulation gets the same score, **P(it produces a new alpha the platform accepts)**, and each round of 80 runs the highest.

| Inputs | Value | From |
|---|---|---|
| θ, a dataset's share of good fields | posterior draw | random rows and screens |
| q, one screen test shows a good field | 31% | 644 good fields |
| ν, a hit is a new signal | starts at 42%, updated by each PnL comparison | 267 of 629 fields |
| p₂, p₃, a variant beats its parent by 0.70 and clears the line | 1.81%, 0.07% | 19,048 and 13,700 results |
| r₁, r₂, r₃, platform passes it as regular, given it clears the local line | 1/119, 6/250, 6/284 | platform verdicts |
| r_PP, platform passes it as Power Pool | 263/544 | platform verdicts |
| ρ, prod-correlation factor of the region × type | 535/667 overall | platform verdicts |

| Option | Score |
|---|---|
| Screen an untried field | g·ν·V / (1 + g·ν·L), g = θ·q. V = P(a new good field ends accepted), L = simulations its follow-up costs |
| Rescreen a missed field (no untried field left) | same, g = P(good \| its misses) · q of its next family |
| Dig a good, new field: next template family | P(that family clears the line) · r₁ · ρ |
| Second-order variant (12, run as one set) | p₂ · r₂ · ρ |
| Third-order variant (12) | p₃ · r₃ · ρ |
| Flip a negative alpha that clears the line | r of its order · ρ |

**Each round:** 8 random picks, then the 72 highest scores. Screens and random picks update θ. A field's first hit is compared with the known signals by daily PnL; a copy stops the field, and a new one opens digging and second order. A field stops once it has an alpha that can be submitted. The best alpha of each signal cluster goes to the platform check, and submission is manual.

## 4. What the data says

| Finding | Evidence | Consequence |
|---|---|---|
| Clearing Sharpe 1.58 and fitness 1 locally almost never means the platform accepts a regular alpha | 1/119 (first order), 6/250, 6/284 | The platform check, not the search, is the bottleneck for regular alphas |
| Power Pool passed far more often than regular | 263/544 first-order Power Pool passes vs 13 regular passes in all checks; every pass since 2026-11-07 was pure Power Pool | Pure Power Pool must now match the current theme, so its value is counted only in theme regions while the quota is open |
| Third order is nearly worthless after correcting for luck | 0.07% per variant | Third order is almost never chosen |
| Second order on an existing good field beats screening a new dataset | 5.2 vs 1.6 accepted per 10,000 simulations (top scores, 2026-11-19) | Existing good fields are worked first |

## 5. Validation

The previous design (v8: fixed queue order, e-value dataset screen, all 56 templates on a hit field, 39 + 40 variants per parent) and v11 ran on the same synthetic markets, built from the numbers above. Each got 40,000 simulations, in 6 markets. An alpha counts as accepted when it clears the line and its true Sharpe is at least 1.2. Both versions ran their real code; the comparison was run in the private repository.

| | v8 | v11 |
|---|---:|---:|
| Distinct accepted signals (mean of 6) | 19.7 | **37.7** |
| Markets where v11 found more | | 6 of 6 (paired t = 7.6) |
| Alphas sent to the platform check (mean) | 1,064 | **105** |

An earlier v11 build lost to v8 (16.5 vs 19.7) because second order waited until a field's digging was finished, so it never ran. Removing that wait is what produced the result above.

## 6. Limitations

- The synthetic markets follow the model v11 assumes, which favours it. The live checks are the random 10% and a weekly assumption report.
- All 10 years are in-sample; the platform checks are the only test of stability.
- The year-by-year Sharpe test is not computed locally.
- Regular pass rates rest on 13 passes; they will move as verdicts accumulate.
- This repository is the decision layer only. Formulas, field names, identifiers, endpoints, credentials and raw logs are excluded; simulation and submission run through a private adapter, and submission is manual.

## 7. Repository

```text
scanner/
  config.py            parameters, each with its source
  statistics.py        template families, shrinkage, luck margin, field-level likelihood, empirical Bayes prior
  novelty.py           daily-PnL signal clusters
  policy.py            the score of every option, Thompson sampling, one round
  loop.py              the day: rounds until the budget, novelty after each result
  platform_adapter.py  the boundary a private adapter implements
tests/
  market.py            synthetic market implementing the adapter
  test_v11.py          one test block per condition, plus a whole day (18 tests)
```

Run the tests with `python -m pytest`.
