# Changelog

Weekly updates, newest first. Each entry has the same four parts: what changed, what the data show, what is still unverified, what happens next. The design document is [README.md](README.md); its Current Status section mirrors the latest entry.

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
