# Changelog

Weekly log, newest first. Each entry has six parts: **Summary** (simulations, passes, submissions), **Performance** (passes per 1,000 simulations against the prior week and a 1‰ baseline, by region and category), **Assumption checks** (README section 4 items tested by the week's data), **Logic changes** (design or code), **Risks / known issues**, **Next week**. Entries before 2026-11-07 use the earlier Ran / Found / Changed / Open format. The design document is [README.md](README.md).

## 2026-11-07 · weekly report

Window: 2026-10-31 00:00 to 2026-11-06 24:00 Pacific (last record 11-06 00:00). Prior week, same definitions: 2026-10-24 to 2026-10-30. Pass = every platform check passes; figures are distinct signals.

**1) Summary**
27,849 simulations, 4 platform passes, 9 submissions on the account (submitted count 57 → 66 in the check log; 3 of them are this week's scanner passes).

**2) Performance**
- Passes per 1,000 simulations: **0.14** (4 / 27,849), up from 0.08 (2 / 24,700) last week; still about one-seventh of the 1‰ baseline.
- Funnel: stage-1 hit rate 8.3% (1,456 / 17,592) vs 13.6% last week; lines 1,261 vs 764; 194 signals checked (527 check records) vs 9. Stage-2 / stage-3 cells: 5,167 / 5,030 vs 3,216 / 1,640. 28 datasets touched vs 15.
- Execution: 99.8% completed (50 errored, 10 failed) vs 90.7% last week (2,184 errored, 108 failed).

| Region | Simulations | Passes | Per 1,000 | Prior week |
|---|---:|---:|---:|---:|
| USA | 12,512 | 3 | 0.24 | no simulations |
| EUR | 15,337 | 1 | 0.07 | 0.13 (2 / 15,876) |
| GLB | 0 | – | – | 0.00 (0 / 8,824) |

| Category | Simulations | Passes | Per 1,000 | Stage-1 hit rate | Prior week |
|---|---:|---:|---:|---:|---:|
| fundamental | 12,846 | 2 | 0.16 | 8.6% | no simulations |
| model | 11,051 | 1 | 0.09 | 10.2% | 0.00 (0 / 8,138) |
| news | 3,952 | 0 | 0.00 | 4.9% | 0.00 (0 / 320) |
| analyst | 0 | 1 | – | – | 0.13 (2 / 15,196) |
| pv | 0 | – | – | – | 0.00 (0 / 1,046) |

The analyst pass is a re-check of a signal simulated before the window. By cell: USA fundamental 2 passes in 8,560 (0.23), EUR model 1 in 11,051 (0.09), EUR fundamental 0 in 4,286, USA news 0 in 3,952. Four passes are too few to rank regions or cells.

**3) Assumption checks** (README section 4)
- **#5 Two-point hit rate: Challenged.** Of 28 datasets with at least 80 stage-1 simulations this week, 12 are below 0.5%, 8 in 0.5–2%, 2 in 2–5%, 6 at or above 5% (median 0.7%). The middle band holds 10 of 28, against 7 of 39 last week.
- **#8 A hit indicates real signal: No change (Weak).** Luck share 1.9% (27.5 expected noise hits vs 1,456); only 1.7% of stage-1 hits reach the line (25 / 1,456), against 1.6% in the register.
- **E3 Hit-field priority: Supported, weaker.** Cells of fields that had already hit: 13.1% (1,249 / 9,534); other cells 2.6% (207 / 8,058). Positive in 10 of 14 datasets (18 of 18 in the register).
- **#10 Errors missing at random: Challenged.** All 50 errored simulations came from one EUR fundamental dataset and all 10 failed ones from one EUR model dataset. Last week 2,120 of 2,184 errors sat in two EUR datasets.
- **#11 Per-dataset limit and look size: No new evidence on the 1,600 limit.** 19 datasets stopped by the test after 80 to 320 simulations; none reached 1,600.
- **#13 Stopped datasets hold nothing: No new evidence.** 19 new stops; none was continued, so false negatives cannot be measured.
- **#20 Line thresholds predict passing: Weak.** 194 signals checked, 4 passed (2.1%).
- **#21 One family representative suffices: Challenged (n = 1).** A stage-1 EUR fundamental line record was never sent to the platform checks; it was submitted by hand on 11-05 and accepted.
- **#23 Correlation is the binding constraint: Challenged.** 24 of 190 failing signals (13%) include a correlation failure, against 75% in the register. Most common failures: in-sample Sharpe ladder 128 (67%), sub-universe Sharpe 57, concentrated weight 42, 2-year Sharpe 32, short duration 23. The population changed: from 11-03 more members per family are checked after a non-correlation failure, and the number of signals checked rose from 9 to 194.

**4) Logic changes**
- **11-03 · Family checks, verdict storage, queue order.** After a non-correlation failure, the scanner now checks up to 2 more family members with a different operator set; correlation or already-submitted still ends the family. Basis: on 11-03, 77 of 93 families failed on non-correlation reasons and 16 on correlation. A verdict is stored as soon as one check definitely fails, rather than re-asked every run. Paused datasets without an accepted signal now queue behind untried datasets in the same cell, and cells with equal priority alternate. Expected: more passes per family, fewer repeated checks, wider coverage.
- **11-04 · Submittable-check fixes.** Global sub-region Sharpe checks no longer block a Power Pool candidate, because two signals were accepted with them at warning. The history rule is 500 trading days (platform rule), not 4 years, because a signal with two years of history was accepted. Only correlation and already-submitted failures are stored permanently; other failures and Power Pool warnings are re-checked each run, because two signals stored as failing showed only a warning on the platform. Expected: fewer submittable signals marked not submittable.
- **11-04 · Power Pool AMER rule restored.** A global candidate with AMER sub-region Sharpe of 1 or less is blocked again, because this month's theme requires AMER Sharpe above 1.

**5) Risks / known issues**
- Missed submittable signals: on 11-05 a signal submitted by hand was accepted while the scanner reported none submittable (see #21). The number missed is unknown.
- Output file: the end-of-run message names the tonight-submittable file, but results are written to the general submittable file; the tonight file currently has 0 rows.
- Power Pool shortlist count: a reported small number of global candidates conflicts with more than 100 rows seen in the output file; not reconciled.
- Theme rules: the current theme was misread (one rule changed and reversed on 11-04). Correlation failures and queue order were also raised on 11-02; this week correlation is no longer the main failure (#23).
- One pass (EUR model, 11-02) has no already-submitted record by 11-06.
- One USA fundamental visit stopped on quota with an interactive login required.
- Unit tests were not re-run for this report.

**6) Next week**
Measure how many line records never reached checks (#21) and fix the output file name; break down the in-sample Sharpe ladder failures, now 67% of failing signals.

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
- Replaying the current dataset gate over the logs: 27 of 40 datasets stop, 13 keep. Against H1 = 2% it saves 16,544 more simulations (27% of the logged 60,533) and loses 1,668 line records and 3 of the 9 passes. Seven datasets that ran 640 or more first-order simulations would have been stopped at 80 to 240; they produced 1,668 line records and 3 passes, all from one dataset whose value sat in a few fields. The gate treats a dataset as one hit rate and can miss such datasets (README, E10).
- No stage-2 or stage-3 lines on 10-29 to 10-31: those days were first-order only (below).

**Changed**
- README: restored the formulas (search space, hit, noise baseline, sequential test boundaries and increments, luck share) and added a worked example of three datasets, start to finish.
- README restructured as a problem statement, definitions, design with parameter origins, a 28-item assumptions table (assumption, dependency, consequence if wrong, test, evidence, status), evidence table, results and limitations, with figures and a table of contents.
- Regions of a theme-specific shortlist program were scanned first-order only from 10-29; the program was switched off on 10-31.
- Corrections to the 2026-10-27 entry: its first-order coverage (36 datasets) and record counts are superseded by the totals above.

**Open**
- 6 of the 70 private unit tests fail because they assume the theme program is on; the running scanner is unaffected.
- Dataset-gate false negatives: unmeasured beyond the 7 cases above; assumption 13 is now marked Challenged.
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
