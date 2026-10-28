# Assumptions Register (v7)

Every assumption the scanner's conclusions rest on. **Check** = how it can be tested from logged run data; **Status** = what is known today (updated weekly in [PROGRESS.md](PROGRESS.md)).

## A. Templates and sampling

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 1 | The 56 templates and fixed field wrapper represent whether a field carries signal | a signal expressed another way is never seen | hit yield per template | open |
| 2 | In the screening phase one random template per field measures the dataset's average quality | a dataset where only one template works is under-rated | template × field hit table | open |
| 3 | Only fields with adequate coverage, split into the two vector forms, are the population | other fields are outside every conclusion | by design | boundary |
| 4 | Screening rounds are random and unbiased; later adaptive rounds are not | rates estimated from adaptive rounds are inflated | use random rounds only | known: about 11% of first-order records are random-phase |

## B. The sequential test

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 5 | A dataset's hit rate is one of two values (0.5% or 5%) | real rates are continuous | fit a continuous mixture to first-round counts | partly checked: two-point fit works (≈25% high group at ≈6%, n = 35) |
| 6 | Simulations are independent given the dataset | fields are correlated, effective sample is smaller, true error rates differ from nominal | dispersion of round counts within a dataset | open: only 3 datasets have ≥ 3 random rounds (dispersion 7.5 vs 1.0 if independent; too few to conclude) |
| 7 | A dataset's hit rate does not change across visits or time | stale verdicts | compare repeat visits | open |
| 8 | A hit (\|Sharpe\| ≥ 1, turnover 1–70%) indicates real signal | hits are luck or unusable | hit → later-stage → platform-check conversion | open |
| 9 | The noise hit rate (0.15654%) is the same for every region, universe, history length and template | luck share wrong by a large factor (≈16× for a 5-year history) | simulations with no signal per region | open, highest priority |
| 10 | Failed or errored simulations are missing at random | hit rates biased if errors concentrate in some fields | errors by field and template | known: 4.5% errored, 0.9% failed |
| 11 | A cap of 1,600 and looks every 80 are adequate | cost per dataset mis-sized | cost simulation on fitted rates; 11 of 58 cached datasets have fewer than 1,600 cells and never reach the cap | open |
| 12 | At the cap, keep iff ≥ 32 hits | arbitrary tie-break | sensitivity analysis | open |
| 13 | Abandoned datasets contain nothing worth finding | false-negative rate unknown | re-test a random sample of abandoned datasets | not yet done |

## C. Escalation

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 14 | A first-order hit predicts improvement under second- and third-order variants; gate values are adequate | wasted budget or lost candidates | stage-to-stage conversion by gate value | open |
| 15 | Stage hit rates reflect true quality | they are inflated by selection | known bias | known |
| 16 | The group and event variants cover the useful space | unlisted variants are never tried | by design | boundary |
| 17 | Repeated selection on in-sample results does not overfit | candidates degrade out of sample | none available beyond platform checks | known limitation |

## D. Submission (platform-specific details kept private)

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 18 | The pre-submission filter predicts passing the platform's checks | good candidates dropped or bad ones checked | filter vs check outcomes | open |
| 19 | Alphas from the same field, stage and dataset have the same check outcome | a checkable candidate is skipped | spot-check non-representatives | open |
| 20 | A passing verdict is valid only while the set of submitted alphas is unchanged | stale pass | handled in code | handled |
| 21 | Correlation with existing submissions, not Sharpe, is the main bottleneck | effort aimed at the wrong target | rejection reasons | open |
| 22 | Per-category saturation rules are correct | submissions wasted or skipped | rule vs outcome | open |
| 23 | Program end conditions are as understood | wrong stop | re-read rules | open |

## E. Platform and implementation

| # | Assumption | If wrong | Check | Status |
|---|---|---|---|---|
| 24 | The same expression always gives the same result | cached and repeated results disagree | re-run a sample | open |
| 25 | Daily quota and day boundary are stable | budgeting errors | platform notices | monitored |
| 26 | The check wait time is long enough for results | false "not ready" | log of retries | open |
| 27 | Placeholder descriptions are accepted by the platform | submission blocked | first live run | not yet verified |
| 28 | The code implements this document | silent divergence | unit tests (67 in the private repo; 13 in this reference), old-vs-new parity on real logs | tests pass; no live run of v7 yet |
