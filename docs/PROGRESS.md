# Progress Log

Updated weekly. Each entry: what changed, what the data say, what is still unverified, what happens next.

## 2026-10-27 (v7 baseline)

**Engineering**
- Scanner rewritten as a layered package (statistics, sampling, queueing, storage, platform access, runner, pipeline) with the policy separated from execution. Private repo: 67 tests, old-versus-new results identical on all 9 real datasets checked. Rollback tag kept for the previous version.
- This public reference was brought in line with v7: H1 hit rate 2% → 5%, zero-hit datasets now stop at the first 80 simulations (previously 240), operating-characteristic table recomputed exactly, assumptions register and design document added. 13 tests pass.

**Data so far**
- 419 datasets are queued; 36 have first-order logs, so about 9% of the universe has been screened and the screened part is concentrated in a few region/category groups. Nothing can be said yet about the rest.
- 48,423 simulation records: 94.6% completed, 4.5% errored, 0.9% failed.
- Random-phase records are about 11% of first-order records; the other 89% come from adaptive sampling and are not used for rate estimates.

**Calibration (first-round counts, 35 datasets)**
- 22 datasets had zero hits in their first 80 simulations (expected ≈ 23.5 if all datasets were at 0.5%); 5 had four or more.
- Two-point fit: low group ≈ 0.2% (the lowest value searched), high group ≈ 6%, weight of the high group ≈ 25%. n = 35, so the weight is imprecise. This supports the current 0.5% / 5% values.
- Stopping rule replayed on the logs: 25 abandon, 10 retain, 1 undecided.
- Noise hit rate: the measured 0.15654% equals the 10-year normal approximation (0.157%). It would be about 2.5% for a 5-year history, so every region's history length must be confirmed.

**Not verified**
- No live platform run of v7 yet.
- Within-dataset dependence cannot be estimated yet (3 datasets with ≥ 3 random rounds).
- Cap of 1,600 has no derivation.

**Next week**
1. Run v7 live for a week; log the first complete day.
2. Re-estimate the hit-rate distribution with more first rounds.
3. Verify the noise rate per region.
4. Audit abandoned datasets: re-test a random 1 in 10 with one extra round.
5. Template yield table from random-phase data only.
