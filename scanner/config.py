"""Parameters of design v11. Each says where it comes from."""
import math

DAILY_CAP = 4000          # simulations per day for the scanner
ROUND = 80                # simulations per round: 8 batches of 10 in flight (platform limit for the account)
BATCH = 10                # screen batch: untried fields of one dataset per Thompson pick
RANDOM_PER_ROUND = 8      # 8 of every 80 (10%) drawn uniformly: dataset, field, template family [11]

HIT_SHARPE = 1.0          # a hit: |Sharpe| >= 1 and turnover 1%-70%
HIT_TURNOVER = (0.01, 0.7)
SHARPE_SE = 1 / math.sqrt(10)   # standard error of a signal-free annual Sharpe over a 10-year backtest
NOISE = 0.0015654         # P(|N(0, 0.316)| >= 1): chance a signal-free alpha is a hit

FAMILY_CORR = 0.7         # templates are one family when their Sharpe across fields correlates |r| >= 0.7 [1]
FAMILY_MIN_SHARED = 100   # fields two templates must share before their correlation is used

CUT_REGULAR = 0.7         # platform self-correlation limit (regular) [2][6]
CUT_PP = 0.5              # platform Power Pool correlation limit
CORR_DAYS = 1000          # last four years of daily PnL
MIN_OVERLAP = 250         # days two series must share before their correlation is used
REG_BAR = (1.58, 1.0)     # local line: Sharpe and fitness a regular alpha needs (delay 1, outside CHN)

THETA_GRID = 400          # grid for each dataset's posterior share of good fields [3]
PRIOR_MIN_DATASETS = 3    # datasets a region x type pool needs for its own prior (else region, else all)
SET_ASIDE = (0.01, 0.05)  # reported only: P(share > 1%) < 5% = "set aside"

VARIANTS = 12             # variants per parent and order [8]
LUCK_MARGIN = SHARPE_SE * math.sqrt(2 * math.log(VARIANTS))   # 0.70: expected best of 12 signal-free Sharpes
ORDER2_GATE = (1.2, 0.7)  # parents p2 was measured on: |Sharpe|, |fitness|
ORDER3_GATE = (1.3, 0.8)
MIN_POSITIONS = 100

NU_PRIOR = (4.2, 5.8)     # chance a good field is a new signal: 267 of 629 fields, prior strength 10 [2]
ERROR_PAUSE = 20          # platform errors per dataset per day before it is skipped for the day [12]
ENOUGH = 3                # accepted alphas that light a pyramid cell: no new screening there
