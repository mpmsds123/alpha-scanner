# Adaptive Alpha Scanner

### Sequential experimental design for allocating a fixed simulation budget in alpha discovery

Each dataset contains many usable fields, and each field can be evaluated through a fixed library of formula templates. The search space is far larger than the daily simulation budget, so the scanner is built as a **budget-constrained sequential statistical experiment**: evidence decides which datasets deserve more budget, and adaptive sampling decides where the next simulations go inside them.

| Design constant | Value |
|---|---:|
| First-order templates per field | 56 |
| Screening round | 80 simulations (80 distinct fields) |
| Daily simulation budget | 4,000 |
| Dataset screening | Wald SPRT, H0: p = 0.5% vs H1: p = 5% |

## Current Status

**As of 2026-10-27 · design version v7 · history in [CHANGELOG.md](CHANGELOG.md)**

- **Coverage:** 419 datasets queued; 36 have first-order logs (about 9%), concentrated in a few region/category groups. No conclusion extends to the unscreened 91%.
- **Dataset quality (first random round of 80, n = 35 datasets):** 22 had zero hits and 5 had four or more. A two-point mixture fits to roughly 25% high-yield datasets (hit rate ≈ 6%) and the remainder at or below about 0.5%. With n = 35 the mixing weight is imprecise.
- **Field-level clustering (verified on logs):** within 15 datasets, a field that had already produced a hit gave a later hit rate of 17.9%, versus 1.9% for fields without a prior hit.
- **Not yet verified:** a live run of v7 on the platform; within-dataset dependence (too few random rounds); the 1,600 cap (no derivation); the noise hit rate outside a 10-year history.

## Contents

1. [Search-space formulation](#search-space-formulation)
2. [Statistical design](#statistical-design)
3. [Adaptive sampling and staged search](#adaptive-sampling-and-staged-search)
4. [Evidence](#evidence)
5. [Representative case](#representative-case)
6. [Assumptions](#assumptions)
7. [Limitations and disclosure boundary](#limitations-and-disclosure-boundary)
8. [System design](#system-design)
9. [Repository structure](#repository-structure)

## Search-Space Formulation

For a dataset with $n$ usable fields and $m=56$ templates, the first-order search space is

$$
n \times 56.
$$

One cell is one field-template formula requiring one backtest simulation.

| Dataset scale | First-order candidate space |
|---|---:|
| 200 fields × 56 templates | **11,200 simulations** |
| 6,650 fields × 56 templates | **372,400 simulations** |

At 4,000 simulations per day, the largest of the 58 cached field lists would require about **93 days** of budget before any higher-order search.

![Field-template grid showing broad exploration and hit-field prioritization](figures/search_grid.svg)

- **Gray:** untested cells
- **Blue:** broad random probes across different fields
- **Orange:** remaining templates moved forward after that field produces a hit

The grid is heterogeneous: dataset hit rates differ, signal clusters by field, and related cells are dependent. This motivates two separate decisions: whether a dataset merits more budget, and where the next simulation should be spent inside it.

## Statistical Design

### Outcome and noise reference

A first-order result is a **hit** when

$$
|\mathrm{Sharpe}| \ge 1
\qquad\text{and}\qquad
1\% \le \mathrm{Turnover} \le 70\%.
$$

The turnover range is the platform's submission range. For a signal-free strategy with a 10-year daily history, the Sharpe estimate is approximately $N(0, 1/\sqrt{10})$ with standard deviation $\approx 0.316$, so $P(|\mathrm{Sharpe}| \ge 1) \approx P(|Z| \ge 3.16) \approx 0.157\%$. The measured rate in earlier no-signal simulations is **0.15654%**, which is the noise reference $\pi_{\mathrm{noise}}$ used below. The approximation depends on history length: for 5 years the same calculation gives about 2.5%. The constant is therefore only valid where the history is 10 years (assumption 9).

### Dataset gate: Wald sequential probability ratio test

Let $p$ be a dataset's unknown hit probability. The gate tests

$$
H_0:p=0.5\%
\qquad\text{vs.}\qquad
H_1:p=5.0\%.
$$

$H_0$ is about three times the noise rate; $H_1$ is a rounded, slightly conservative version of the high-yield group fitted from data (about 6%, see Status). Tolerances: $\alpha=10\%$ is the maximum probability of retaining a dataset at $H_0$; $\beta=5\%$ is the maximum probability of abandoning a dataset at $H_1$. The asymmetry reflects cost: wrongly retaining costs on the order of 100-200 simulations, wrongly abandoning loses the dataset. Wald boundaries:

$$
A=\ln\frac{1-\beta}{\alpha}=\ln\frac{0.95}{0.10}\approx +2.251,
\qquad
B=\ln\frac{\beta}{1-\alpha}=\ln\frac{0.05}{0.90}\approx -2.890.
$$

Log-likelihood-ratio increments per simulation:

$$
\Delta L_{\mathrm{hit}}=\ln\frac{0.05}{0.005}=+2.303,
\qquad
\Delta L_{\mathrm{miss}}=\ln\frac{0.95}{0.995}=-0.0463.
$$

The score $L$ is evaluated after every round of 80 simulations: $L\ge A$ retains, $L\le B$ abandons, otherwise continue. At the 1,600-simulation cap (20 looks) the dataset is retained iff $L\ge 0$, i.e. at least 32 hits.

Consequences that follow directly: a dataset with zero hits in the first 80 is abandoned immediately ($80\times 0.0463 > 2.890$); three hits in the first 80 retain it ($3\times2.303-77\times0.0463 = 3.34 > A$), two do not. The two hypotheses are equally likely to win at

$$
p^{*}=\frac{-\Delta L_{\mathrm{miss}}}{\Delta L_{\mathrm{hit}}-\Delta L_{\mathrm{miss}}}\approx 1.97\%,
$$

which is the effective retain/abandon line.

**Why 80 per round, distinct fields.** One round is 8 batches of 10, which fills the platform's 10 concurrent slots. Fields within a dataset are correlated, so each round draws 80 different fields with one random template each, to limit within-round dependence.

**Operating characteristics.** Exact evaluation by dynamic programming over the 20 looks (independent Bernoulli outcomes):

| True hit rate | Retained | Mean simulations |
|---:|---:|---:|
| 0.16% | 0.03% | 91 |
| 0.5% | 0.9% | 119 |
| 1.0% | 7.6% | 161 |
| 1.5% | 25% | 193 |
| 2.0% | 49% | 199 |
| 3.0% | 83% | 161 |
| 5.0% | 98.1% | 103 |
| 10% | 99.98% | 81 |

Realised error rates (0.9% at $H_0$, 1.9% at $H_1$) are well below the nominal 10% and 5% because looks are discrete and the boundaries are conservative. These figures assume independent trials; with field-level dependence the effective sample is smaller and the true error rates are not known (assumption 6). The 1,600 cap and the 32-hit tie-break are pragmatic, not derived (assumptions 11-12).

### Luck share

For $n$ simulated cells and $h$ observed hits,

$$
\widehat{\text{luck share}}=\frac{n\,\pi_{\mathrm{noise}}}{h}.
$$

This is a plug-in false-discovery estimate that treats every tested cell as signal-free ($\pi_0=1$), so it is an upper bound on the share of hits attributable to noise under the iid-noise model. It is not a multiplicity-corrected q-value, and it ignores dependence between cells.

## Adaptive Sampling and Staged Search

After the gate, allocation adapts at the field level. The scanner **does not prune** untested cells; it only reorders them: the remaining templates of fields that have already hit are tested first.

### Multi-stage search

| Stage | Per-visit cap | Construction |
|---|---:|---|
| First order | 2,000 | field × first-order template |
| Second order | 1,000 | selected parent × group wrapper |
| Third order | 1,000 | selected parent × conditional `trade_when` variant |

The 4,000 daily budget is the 5,000 platform quota less 1,000 reserved for a separate pipeline; the 2,000/1,000/1,000 split is a design choice, not an optimum. First-order promotion requires $|\mathrm{Sharpe}|\ge1.2$, $|\mathrm{Fitness}|\ge0.7$ and more than 100 positions; candidates are decay-adjusted, negative signals are flipped, and the best 100 are kept with at most five per field and sign. Second-order promotion uses 1.3 / 0.8 and the best 200. Gate values are inherited from earlier versions, not optimised (assumption 14). Higher-order wrapper names remain abstract in the public implementation.

## Evidence

All figures below were recomputed from the run logs on 2026-10-27. They support the allocation method; they are not claims about the performance of any individual alpha.

1. **Dataset quality distribution.** First random round (80 simulations) for 35 datasets: 22 with zero hits (about 23.5 expected if every dataset were at 0.5%), 5 with four or more. A two-point mixture fitted by maximum likelihood: low group about 0.2% (the lowest value searched), high group about 6%, high-group weight about 25%. Replaying the stopping rule over all 36 datasets with first-order logs: 25 abandon, 10 retain, 1 undecided.
2. **Field-level clustering.** In the 15 datasets with at least 30 first-order results in both states, the hit rate of a cell whose field had already hit was 17.9% (n = 12,970) versus 1.9% (n = 13,754) for fields with no prior hit; the dataset-stratified (Mantel-Haenszel weighted) risk difference is +13.3 percentage points and is positive in all 15 datasets. Pooling across all datasets gives 17.9% versus 1.4%, but that comparison is confounded by dataset quality and is not used. Caution: sampling after a field's first hit is adaptive, so this is an observed association under the scanner's own policy, not a randomised experiment.
3. **Same-field dependence.** For the same field and operator, the Pearson correlation of signed Sharpe between adjacent windows is 0.875 (5 vs 22 days), 0.854 (22 vs 66), 0.893 (66 vs 120) and 0.917 (120 vs 240), each over about 3,300 pairs pooled across datasets.
4. **Predictive value of the first result.** The correlation of $|\mathrm{Sharpe}|$ between the first two logged cells of the same field is 0.32 (n = 1,833 fields). The magnitude is only moderately informative, and the policy uses hit/no-hit as its state. Whether a richer state would allocate better is untested. Later cells are chosen adaptively, so this correlation is range-restricted.
5. **Noise scale.** For 19 datasets with hit rate at or below 0.6% and at least 200 simulations, the standard deviation of Sharpe across cells ranges from 0.25 to 0.38, against 0.316 for a signal-free 10-year history. The spread across datasets is not yet explained (history length, residual signal and universe are candidates).

A first-order expected maximum under noise gives a sense of winner inflation: for 10,000 independent noise Sharpes it is approximately $0.316\sqrt{2\ln 10{,}000}\approx1.36$.

## Representative Case

### USA / Option-Chart Model: one recorded visit (v6 logic)

One 4,000-simulation visit moved from broad exploration across **380 fields** to targeted higher-order refinement across **7 selected field families**. Counts below were re-verified against the logs.

| Stage | Candidate space | Executed simulations | Hits | Hit rate | Promotion-qualified |
|---|---:|---:|---:|---:|---:|
| First order | 24,584 | 2,000 | 347 | 17.35% | 36 (13 fields) |
| Second order | 2,178 | 1,000 | 759 | 75.9% | 216 |
| Third order | 1,320 | 1,000 | 825 | 82.5% | n/a |

**Candidate space is not executed budget.** The table reports both so a partially sampled stage is not mistaken for exhaustive evaluation. Later-stage hit rates are conditional on deliberate selection of parents; they are not a causal improvement from 17.35% to 75.9% or 82.5%, and they overstate true quality (winner's curse).

## Assumptions

Every assumption the conclusions rest on. *Check* is how it can be tested from logged data; *Status* is what is known today. Nine further assumptions concern platform rules and submission mechanics and are tracked privately.

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 1 | The 56 templates and the fixed field wrapper (back-fill, winsorize at 4 standard deviations) represent whether a field carries signal | a signal expressed another way is never seen | hit yield per template | open |
| 2 | In screening, one random template per field measures the dataset's average quality | a dataset where only one template works is under-rated | field × template hit table | open |
| 3 | The relevant population is fields with adequate coverage, with vector fields split into two forms | other fields are outside every conclusion | by design | boundary |
| 4 | Screening rounds are random and unbiased; later adaptive rounds are not | rates from adaptive rounds are inflated | estimate from random rounds only | known: about 11% of first-order records are random-phase |
| 5 | A dataset's hit rate takes one of two values (0.5% or 5%) | real rates are continuous | fit a continuous mixture to first-round counts | two-point fit adequate on n = 35 |
| 6 | Simulations are independent given the dataset | effective sample is smaller; true error rates differ from nominal | within-dataset dispersion across random rounds | open: 3 datasets with at least 3 random rounds (dispersion 7.5 vs 1.0 if independent), too few to conclude |
| 7 | A dataset's hit rate is constant across visits and time | stale verdicts | compare repeat visits | open |
| 8 | A hit indicates real signal | hits are noise or unusable | conversion from hit to later stages and platform checks | open |
| 9 | The noise hit rate (0.15654%) is the same for every region, universe, history length and template | luck share wrong by a large factor (about 16 times for a 5-year history) | no-signal simulations per region | open, highest priority |
| 10 | Errored and failed simulations are missing at random | hit rates biased if failures concentrate in some fields | failures by field and template | known: 4.5% errored, 0.9% failed |
| 11 | A 1,600 cap and a look every 80 are adequate | cost per dataset mis-sized | cost simulation on fitted rates (11 of 58 cached datasets have fewer than 1,600 cells and never reach the cap) | open |
| 12 | At the cap, retain iff at least 32 hits | arbitrary tie-break | sensitivity analysis | open |
| 13 | Abandoned datasets contain nothing worth finding | false-negative rate unknown | re-test a random sample of abandoned datasets | not done |
| 14 | A first-order hit predicts improvement under second- and third-order variants; the gate values are adequate | wasted budget or lost candidates | stage-to-stage conversion by gate value | open |
| 15 | Later-stage hit rates reflect true quality | they are inflated by selection | known bias | known |
| 16 | The group and event variants cover the useful space | unlisted variants are never tried | by design | boundary |
| 17 | Repeated in-sample selection does not overfit | candidates degrade out of sample | none beyond platform checks | known limitation |
| 18 | The same expression always returns the same result | cached and repeated results disagree | re-run a sample | open |
| 19 | The code implements this document | silent divergence | unit tests and old-versus-new parity on real logs | 13 tests here; the private implementation has 67 tests and matched the previous version on all 9 datasets checked; no live run of v7 yet |

## Limitations and Disclosure Boundary

- Within-field sampling reduces dependence during screening but does not eliminate it.
- The binary hit abstraction discards the continuous information in Sharpe, turnover and other diagnostics.
- The noise model is horizon-dependent; $1/\sqrt{10}$ is not valid for every history length or return process, and real return series are autocorrelated and fat-tailed.
- Top-parent and best-of-k selection create winner inflation that is recognised but not corrected here.
- Platform historical partitions and sub-universe checks are not true future out-of-sample evidence.
- The repository demonstrates research design and orchestration, not a live, predictive or tradable system.

Real field names, alpha expressions, identifiers, credentials, account details, endpoints, raw logs and private research notes are excluded. Public candidate keys and wrappers are synthetic and non-reversible. Authenticated simulation and final submission require a private adapter and explicit human action.

## System Design

The public system separates statistical policy from platform execution:

- `statistics.py` implements Wald SPRT decisions and the exploratory noise-FDR diagnostic.
- `sampling.py` selects diverse screening batches and prioritizes remaining cells from hit fields.
- `formula_factory.py` creates sanitized first-, second-, and third-order experiment specifications.
- `pipeline.py` tracks stage budgets, skips completed experiments, and supports pause/resume from prior results.
- `platform_adapter.py` defines the execution boundary, including explicit retry handling, without authentication or endpoints.
- `tests/` verifies stopping boundaries, distinct-field batches, hit-field priority, budget caps, retry behavior, and resume behavior.

Completed experiment keys and sanitized result records can be persisted by the caller and supplied to the next visit. Final platform checks and submission remain manual by design; this repository does not auto-submit research outputs.

## Repository Structure

```text
alpha-scanner/
├── README.md          this document: design, evidence, assumptions, status
├── CHANGELOG.md       weekly updates, newest first
├── figures/
│   └── search_grid.svg
├── scanner/
│   ├── statistics.py        SPRT gate and luck share
│   ├── sampling.py          distinct-field rounds, hit-field priority
│   ├── formula_factory.py   abstract first/second/third-order specifications
│   ├── pipeline.py          budget-aware orchestration, pause/resume
│   └── platform_adapter.py  execution boundary and retry wrapper
├── tests/                   13 deterministic tests
└── pyproject.toml
```

Run the tests with `python -m pytest`.
