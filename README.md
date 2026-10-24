# Nifty and NSE strategies: results dashboard

Streamlit dashboard for two systematic strategies, scored with the supplied backtest harness (`harness_public.py`, unmodified).

| | Task 1 | Task 2 |
|---|---|---|
| Market | Nifty 50 futures, 15-minute bars | NSE stocks, daily, long-only |
| Rule | Long overnight when the prior close is above its 100-day average and the index is up on the day at 14:45; held to the 09:30 open | Top 10 by 6-month return among liquid stocks above their 50-day average and below the 75th percentile of 60-day volatility; rebalanced every 21 days |
| File | `task1.py` | `task2.py` |

All results are in-sample on the visible data. Hidden windows are not shown.

## Setup
Python 3.10 or newer.
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data
The input files are not in this repository. Place the supplied `data/` folder in the project root:
```
data/nifty50_15min_train_2017-04-03_2022-01-31.csv
data/nifty_monthly_expiries_2017-01_2022-01.csv
data/stocks_daily_train_2021-04-26_2024-06-30.csv
data/nifty50_daily_2021-04-26_2024-06-30.csv
```

## Run
```
streamlit run dashboard/app.py
```
Opens at http://localhost:8501. Check the strategies directly with the harness:
```
python3 harness_public.py task1 task1.py
python3 harness_public.py task2 task2.py
```

## Dashboard
| Page | Content |
|---|---|
| Overview | Both tasks against the stated bars, equity, year-wise returns |
| Task 1 Strategy | Approaches A/B/C, parameters, fill delay, cost multiplier, date range; equity, drawdown, intraday chart, trades |
| Task 1 Robustness | Delay and cost table, sensitivity grids, walk-forward, sub-periods, overnight-gap profile |
| Task 2 Strategy | Parameters with Run backtest; volatility cap, holdings, target portfolio by date |
| Task 2 Robustness | Sensitivity grids, costs, sub-windows, year exclusion, top trades, universe stress |
| Trade Explorer | Trades for either task with a chart per trade |
| Benchmarks | Equal-weight and random baselines, variants, execution stress, working ranges |
| Notes | Failed ideas, survivorship note, risks, report |

Sidebar: Source locks parameters to the strategy files (Submitted) or unlocks the sliders (Custom). Task 1 updates live; Task 2 runs on Run backtest (a few seconds).

## Contents
```
task1.py, task2.py        strategies
harness_public.py         backtest engine (supplied)
dashboard/                app.py, pages/, core/ (loaders, engines, charts, controls)
research/*.json           precomputed grids and baselines read by the dashboard
research/audit/p1_results.json   pre-set experiment results
report.pdf, failed_ideas.md, survivorship_note.md
```
