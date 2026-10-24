"""
Task 2: long-only NSE momentum, lower three quarters of the liquid universe by volatility.

Rank liquid stocks by `lb`-day return. Keep names above their `sma`-day average and at or below the `volq` quantile
of 60-day volatility. Hold the top `n` equally weighted and rebalance every `rebal` trading days. No market-level brake.

Parameters (range reported):
  n       positions held                                          8-12
  lb      momentum lookback, trading days                         84-168
  rebal   days between rebalances                                 10-30
  sma     per-stock trend filter, days                            40-70
  volq    volatility quantile kept (1.00 = no cap)                0.60-1.00
Also tuned: liquidity floor MIN_TURNOVER, Rs 10 cr (Rs 25 cr tried), kept as a module constant.
Fixed: 60-day volatility window; corporate-action guard (excludes any stock with a one-day drop over 40% in the past year).
"""
import numpy as np
import pandas as pd

PARAMS = {'n': 10, 'lb': 126, 'rebal': 21, 'sma': 50, 'volq': 0.75}

MIN_TURNOVER = 1e8
JUMP = -0.40
VOL_WINDOW = 60


def orders(date, hist, portfolio, params, state):
    p = params
    k = state.get('k', 0); state['k'] = k + 1
    if k % p['rebal'] != 0:
        return []
    held = list(portfolio['positions'])
    c = hist['close'].iloc[-300:]
    v = hist['volume'].iloc[-300:]
    if len(c) <= p['lb'] or len(c) <= p['sma']:
        return []

    turnover = (c * v).rolling(60, min_periods=40).median().iloc[-1]
    liquid = (turnover >= MIN_TURNOVER) & c.iloc[-1].notna()

    r1 = c.pct_change(fill_method=None)
    vol = r1.iloc[-VOL_WINDOW:].std() * np.sqrt(252)
    mom = c.iloc[-1] / c.iloc[-1 - p['lb']] - 1
    ok = liquid & mom.notna() & ~(r1.iloc[-252:] < JUMP).any() & (c.iloc[-1] > c.iloc[-p['sma']:].mean())
    ok &= vol <= vol[liquid].quantile(p['volq'])
    top = list(mom[ok].sort_values(ascending=False).index[:p['n']])

    out = [{'symbol': s, 'side': 'sell', 'type': 'market'} for s in held if s not in top]
    free = p['n'] - len([s for s in held if s in top])
    w = 1.0 / p['n']
    out += [{'symbol': s, 'side': 'buy', 'type': 'market', 'weight': w}
            for s in top if s not in held][:max(free, 0)]
    return out
