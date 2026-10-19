# Statistical design

## 1. Search as a stratified experiment

The search grid is stratified by dataset, field, template family, and window. Historical evidence showed that the largest variation was between datasets and fields. The scanner therefore spends budget in the same order: decide whether a dataset deserves budget, then prioritize promising fields without prematurely deleting the rest of the grid.

## 2. Dataset gate

Let each simulation produce a Bernoulli hit indicator. The sequential log-likelihood ratio after `k` hits in `n` trials is

```text
k log(p_good / p_bad)
+ (n-k) log((1-p_good) / (1-p_bad)).
```

The implemented design uses `p_bad = 0.005`, `p_good = 0.02`, a 5% tolerance for abandoning a good dataset, and a 10% tolerance for retaining a bad one. Wald boundaries follow directly:

```text
upper = log((1 - miss_good) / keep_bad) = log(0.95 / 0.10) = 2.25
lower = log(miss_good / (1 - keep_bad)) = log(0.05 / 0.90) = -2.89
```

Sampling one cell from each of 80 different fields reduces within-field dependence during the gate. If fewer than 80 fields remain, the batch is filled from additional untested cells.

At 1,600 trials without a boundary crossing, a nonnegative score continues and a negative score abandons. This cap resolves the small fraction of datasets whose hit rates sit near the indifference region.

## 3. Adaptive cluster sampling

After the gate, a hit changes the order of future experiments for that field. The design does not infer that a first miss makes a field bad, because the observed absolute-Sharpe correlation across different templates of the same field was only about 0.2. A positive hit indicator was much more informative.

The policy is deliberately conservative:

1. choose one untested cell per field;
2. visit fields with prior hits first;
3. randomize within each priority group;
4. if capacity remains, fill from any remaining untested cells;
5. never prune solely because of a miss.

## 4. Higher orders

Parents are ranked by absolute Sharpe after passing minimum Sharpe, Fitness, and position-count gates. A per-field cap limits concentration. The public implementation represents wrappers by opaque keys, not production expressions.

The source design used bounded visits:

| Order | Maximum simulations per visit | Rationale |
|---|---:|---|
| First | 2,000 | estimate yield and complete the sequential gate |
| Second | 1,000 | expand a bounded set of first-order parents |
| Third | 1,000 | expand a bounded set of second-order parents |

Completed candidate keys, sanitized results, and gate states are supplied on the next visit. This preserves hit-field priority, sequential evidence, and parent selection without re-running cells.

## 5. False discovery and selection

The exploratory FDR estimate uses the expected number of noise crossings under a 10-year model. It is useful for scale, not a guarantee. It does not correct:

- the maximum-of-many effect when parents are ranked;
- winner inflation after comparing many wrappers;
- dependence across related cells;
- history length that differs from 10 years;
- correlation with already deployed signals.

The live evidence made the last point decisive: strong in-sample candidates can be redundant rather than false.

## 6. Validation evidence

The source design reported 3,000 Monte Carlo replications per true hit rate and a replay on 20 earlier datasets. All nine datasets with observed hit rate at least 2% were kept; datasets at or below 0.62% were abandoned within 240-480 simulations. These are design-validation results, not out-of-sample trading performance.

