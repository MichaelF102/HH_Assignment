"""Task 1 backtests through the unmodified harness. Approach C is the submitted task1.py; A and B are the
comparison approaches from the report, re-implemented here so the dashboard can show all three."""
import json

import numpy as np
import pandas as pd
import streamlit as st

from . import loaders as L

H = L.H
APPROACHES = {
    'C': 'C: hybrid overnight continuation (submitted)',
    'A': 'A: pure overnight gap (last bar + gap)',
    'B': 'B: daily trend long/flat',
}
SCENARIOS = {  # name -> (delay, cost multiplier)
    'Base': (0, 1), 'Delay 1 bar': (1, 1), 'Delay 2 bars': (2, 1), '2x costs': (0, 2), '3x costs': (0, 3),
    '4x costs': (0, 4), 'No costs': (0, 0)}
DEFAULTS = {'A': {'sma': 100}, 'B': {'sma': 50, 'vol': 0.35}}


def default_params(approach):
    return L.submitted_params(1) if approach == 'C' else dict(DEFAULTS[approach])


def _daily(bars):
    day = bars.index.normalize()
    return day, bars['close'].groupby(day).last()


def want_for(approach, params):
    bars = L.bars()
    if approach == 'C':
        return L.strategy(1).positions(bars.copy(), dict(params)).values.astype(float)
    day, dc = _daily(bars)
    tod = (bars.index.hour * 60 + bars.index.minute).values
    if approach == 'A':
        s = (dc > dc.rolling(int(params['sma'])).mean()).astype(float).shift(1)
        return np.where(tod == 15 * 60, np.nan_to_num(s.reindex(day).values), 0.0)
    vol = dc.pct_change().rolling(20).std() * np.sqrt(252)
    s = ((dc > dc.rolling(int(params['sma'])).mean()) & (vol < params['vol'])).astype(float)
    is_last = np.r_[day[1:] != day[:-1], True]
    return np.nan_to_num(np.where(is_last, s.reindex(day).values, s.shift(1).reindex(day).values))


@st.cache_data(show_spinner=False)
def run(approach, params_json, delay=0, cost_mult=1.0, start=None, end=None):
    params = json.loads(params_json)
    bars, want = L.bars(), want_for(approach, params)
    if delay:
        want = np.r_[np.zeros(delay), want[:-delay]]
    res = H.task1_backtest(bars, want, L.expiries(), cost=H.T1_COST * cost_mult)
    stats, eq = H.task1_stats(res, start, end)
    trades = pd.DataFrame(res['trades'], columns=['entry', 'ret'])
    if start or end:
        lo = pd.Timestamp(start) if start else trades.entry.min().normalize()
        hi = pd.Timestamp(end) if end else trades.entry.max().normalize()
        trades = trades[(trades.entry.dt.normalize() >= lo) & (trades.entry.dt.normalize() <= hi)]
    daily = res['daily'] + H.R_CASH / 252
    if start or end:
        daily = daily[(daily.index >= eq.index[0]) & (daily.index <= eq.index[-1])]
    return dict(stats=stats, eq=eq, daily=daily, pos=res['pos'], trades=trades.reset_index(drop=True), want=want)


def pj(params):
    return json.dumps({k: (int(v) if float(v).is_integer() and k != 'mom' and k != 'vol' else float(v)) for k, v in params.items()}, sort_keys=True)


@st.cache_data(show_spinner=False)
def lookahead_status(params_json):
    m = L.strategy(1)
    params = json.loads(params_json)
    full = pd.Series(want_for('C', params), index=L.bars().index)
    return H.lookahead_check(m, L.bars(), params, full)


@st.cache_data(show_spinner=False)
def scenario_table(approach, params_json, start=None, end=None):
    rows = []
    for name, (d, c) in SCENARIOS.items():
        s = run(approach, params_json, d, c, start, end)['stats']
        rows.append(dict(Scenario=name, Sharpe=s['sharpe'], MaxDD=s['max_dd'], CAGR=s['cagr'], Trades=s['trades']))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def live_grid(params_json, ax1, v1, ax2, v2, delay):
    base = json.loads(params_json)
    z = np.zeros((len(v1), len(v2), 3))
    for i, a in enumerate(v1):
        for j, b in enumerate(v2):
            s = run('C', pj({**base, ax1: a, ax2: b}), delay)['stats']
            z[i, j] = (s['sharpe'], s['max_dd'], s['cagr'])
    return z


@st.cache_data
def benchmark_curve():
    b = L.bars().close
    return b.groupby(b.index.normalize()).last()


@st.cache_data
def tod_profile():
    b = L.bars()
    tod = b.index.strftime('%H:%M')
    inbar = (b.close / b.open - 1).groupby(tod).mean() * 1e4
    day = b.index.normalize()
    d = b.groupby(day).agg(open=('open', 'first'), close=('close', 'last'))
    gap = (d.open / d.close.shift(1) - 1).dropna()
    by_year = (gap.groupby(gap.index.year).mean() * 1e4)
    return inbar, by_year, float(gap.mean() * 1e4), float(gap.mean() / gap.std() * np.sqrt(len(gap)))
