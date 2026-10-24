"""Task 2 backtests through the unmodified harness, plus breadth / candidate helpers."""
import hashlib
import json
import os
import pickle

import numpy as np
import pandas as pd
import streamlit as st

from . import loaders as L

H = L.H
BASE_PKL = os.path.join(L.DASH, 'cache', 't2_base.pkl')


def params_json(params):
    return json.dumps({k: (int(v) if k in ('n', 'lb', 'rebal', 'sma') else float(v)) for k, v in params.items()}, sort_keys=True)


def _pack(res):
    stats, eq = H.task2_stats(res)
    return dict(stats=stats, eq=eq, trades=res['trades'], gross=res['gross'])


@st.cache_data(show_spinner=False)
def run(pjson, cost=H.T2_COST):
    res = H.task2_backtest(L.strategy(2), L.stocks(), json.loads(pjson), H.T2_START, H.T2_END, cost)
    return _pack(res)


def base_result():
    """Submitted strategy at the default cost: precomputed (dashboard/cache/build_cache.py), else computed."""
    if os.path.exists(BASE_PKL):
        with open(BASE_PKL, 'rb') as f:
            cached = pickle.load(f)
        src = hashlib.md5(open(os.path.join(L.ROOT, 'task2.py'), 'rb').read()).hexdigest()
        if cached.get('src_md5') == src:      # ignore the cache if task2.py changed since it was built
            return cached
    return run(params_json(L.submitted_params(2)), H.T2_COST)


def window_stats(res, start, end):
    """Stats of a result restricted to [start, end] (display filter; the backtest itself is unchanged)."""
    eq, T, g = res['eq'], res['trades'], res['gross']
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    msk = (eq.index >= lo) & (eq.index <= hi)
    e = eq[msk]
    tr = T[(T.entry_date >= lo) & (T.entry_date <= hi)].ret.tolist() if len(T) else []
    extra = dict(time_in_market=float(g[msk].mean()), avg_hold_days=float(T.days.mean()) if len(T) else np.nan)
    return H.stats(e, tr, 0.0, extra), e


@st.cache_data(show_spinner=False)
def vol_cap_series(volq, min_value=1e8):
    """Per date: the 60-day volatility at the volq quantile of liquid stocks (the cap) and the universe median."""
    D = L.stocks()
    c, v = D['close'], D['volume']
    liquid = ((c * v).rolling(60, min_periods=40).median() >= min_value) & c.notna()
    vol = (c.pct_change(fill_method=None).rolling(60).std() * np.sqrt(252)).where(liquid)
    return vol.quantile(volq, axis=1), vol.median(axis=1)


def candidates(date, params):
    """Run the submitted orders() on a fresh book as of `date`: the buy list is the ranked target portfolio."""
    D = L.stocks()
    i = D['close'].index.searchsorted(pd.Timestamp(date), side='right')
    hist = {k: v.iloc[:i] for k, v in D.items()}
    pf = {'cash': 1.0, 'value': 1.0, 'positions': {}}
    out = L.strategy(2).orders(hist['close'].index[-1], hist, pf, dict(params), {'k': 0})
    c = hist['close']
    mom = c.iloc[-1] / c.iloc[-1 - int(params['lb'])] - 1
    syms = [o['symbol'] for o in out if o['side'] == 'buy']
    return pd.DataFrame({'symbol': syms, 'momentum': [mom[s] for s in syms], 'close': [c[s].iloc[-1] for s in syms]}), bool(out)


def holdings_on(res, date):
    T = res['trades']
    d = pd.Timestamp(date)
    h = T[(T.entry_date <= d) & (T.exit_date > d)].copy()
    return h
