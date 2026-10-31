# Changelog

Daily or weekly log, newest first. Each entry: **Ran** (what executed), **Found** (what the data show), **Changed** (design or code), **Open** (known unverified or broken). The design document is [README.md](README.md).

## 2026-10-31 · design v7, first live week

**Ran**
- v7 has run on the platform since 2026-10-28. Completed cells per day (stage 1 / 2 / 3): 10-28 1,545 / 286 / 0; 10-29 3,546 / 0 / 0; 10-30 3,305 / 0 / 0; 10-31 1,360 / 0 / 0 (partial).
- Totals through 2026-10-31: 58,567 records (95.4% completed, 3.8% errored, 0.8% failed); 41,622 stage-1, 8,907 stage-2, 5,190 stage-3 completed cells.
- Platform checks 2026-10-16 to 2026-10-30: 57 run, 9 passed, 48 failed; 36 of the 48 include a correlation failure.

**Found**
- Hit rate by dataset (39 datasets with at least 80 first-order simulations) ranges from 0% to 22.6%; pooled 9.8%, equal-allocation mean 4.2%.
- Early stopping: 21 stopped datasets used about 18% of the budget a full first-order visit would have used and yielded 13 hits in 5,886 simulations (0.22%).
- Cells of a field that had already hit hit again 19.4% of the time versus 2.2% for other fields (positive in 18 of 18 datasets).
- Template hit rates differ (chi-square 178 on 55 df): scale, rank, zscore and quantile 4.2-5.6%; std_dev, delay, delta and mean 0.6-1.1%.
- No stage-2 or stage-3 lines on 10-29 to 10-31: those days were first-order only (below).

**Changed**
- README restructured as a problem statement, definitions, design with parameter origins, a 28-item assumptions table (assumption, dependency, consequence if wrong, test, evidence, status), evidence table, results and limitations, with figures and a table of contents.
- Regions of a theme-specific shortlist program were scanned first-order only from 10-29; the program was switched off on 10-31.
- Corrections to the 2026-10-27 entry: its first-order coverage (36 datasets) and record counts are superseded by the totals above.

**Open**
- 6 of the 70 private unit tests fail because they assume the theme program is on; the running scanner is unaffected.
- Whether a cell came from a random or an adaptive round is not logged, so assumption 4 cannot be re-measured.
- No control arm: the allocation has not been compared with uniform allocation.
- 40 of 419 queued datasets have first-order records.

## 2026-10-27 · design v7 baseline

**What changed**
- The private scanner was rewritten as a layered package (statistics, sampling, queueing, storage, platform access, runner, pipeline), with policy separated from execution. 67 tests; results identical to the previous version on all 9 real datasets compared. A rollback tag marks the previous version.
- This public reference was aligned with v7: H1 hit rate 2% → 5%; a dataset with zero hits in its first 80 simulations is now abandoned immediately (previously after 240); the operating-characteristic table was recomputed exactly; README consolidated into one document with the full 28-item assumptions register. 13 tests.

**What the data show** (recomputed from run logs)
- 419 datasets queued, 36 with first-order logs (about 9%). 48,423 simulation records: 94.6% completed, 4.5% errored, 0.9% failed. About 11% of first-order records come from random sampling; the rest are adaptive and are not used to estimate rates.
- First random round, 35 datasets: 22 with zero hits, 5 with four or more. Two-point fit: about 25% of datasets at about 6%, the rest at or below about 0.5%.
- Within 15 datasets, cells of fields that had already hit hit at 17.9% versus 1.9% for other fields (stratified risk difference +13.3 points, positive in 15 of 15).
- Same-field adjacent-window Sharpe correlation 0.85-0.92. Correction to earlier public text: the earlier figures (0.70-0.87, an 18.1% vs 1.3-3.1% hit-rate contrast, 0.28-0.33 Sharpe dispersion, 0.2 first-result correlation) came from an older, smaller sample and were replaced by the values above (0.32 first-result correlation; Sharpe dispersion 0.25-0.38).
- The measured noise rate (0.15654%) equals the 10-year normal approximation; it would be about 2.5% for a 5-year history.

**Not verified**
- No live platform run of v7 yet.
- Within-dataset dependence: only 3 datasets have at least 3 random rounds.
- The 1,600 cap has no derivation.
- Noise rate per region and history length.

**Next**
1. Run v7 live for a week and log the first complete day.
2. Re-estimate the hit-rate distribution as more first rounds arrive.
3. Check the noise rate per region.
4. Audit abandoned datasets: re-test a random 1 in 10 with one extra round.
5. Template yield table from random-phase data only.
