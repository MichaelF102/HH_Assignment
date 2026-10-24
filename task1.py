"""
Task 1: Nifty futures overnight continuation, long/flat, 15-minute bars.

Hold a long position overnight when (1) the prior close is above its `sma`-day average and (2) the index is up on the
day (return since the prior close > `mom`) at the decision bar.

Timing (p=2, q=1): decision at the close of the 14:30 bar, fill at the 14:45 open; held through the 15:15 bar, the
overnight gap and the 09:15 bar; flat from the 09:30 open. The trigger bar starts 15*(p+1) minutes before 15:30;
q is the number of next-morning bars held. A fill delay of 3 or more bars puts the entry after the close.

Parameters (range reported):
  sma   daily-close average length                        50-200
  p     extra bars before the final bar at entry          1-3
  q     next-morning bars held                            1-3
  mom   minimum return on the day at the decision bar     -0.2% to +0.2%
"""
import numpy as np
import pandas as pd

PARAMS = {'sma': 100, 'p': 2, 'q': 1, 'mom': 0.0}

BAR_MIN = 15
OPEN_MIN = 9 * 60 + 15
LAST_MIN = 15 * 60 + 15


def positions(bars: pd.DataFrame, params: dict) -> pd.Series:
    idx = bars.index
    day = idx.normalize()
    tod = (idx.hour * 60 + idx.minute).values
    c = bars['close']

    dclose = c.groupby(day).last()                       # day's last close (only ever used shifted by one day)
    prev_close = dclose.shift(1).reindex(day).values
    sma = dclose.rolling(params['sma']).mean().shift(1).reindex(day).values
    uptrend = prev_close > sma                           # False while the average is warming up (NaN)

    t_entry = LAST_MIN - BAR_MIN * (params['p'] + 1)     # bar whose close triggers entry; fill is at the next bar's open
    strong = (c.values / prev_close - 1) > params['mom']
    go = pd.Series(np.where(tod == t_entry, uptrend & strong, False), index=day).groupby(level=0).max()

    go_today = go.reindex(day).values.astype(bool)
    go_prev = go.shift(1).reindex(day).fillna(False).values.astype(bool)

    want = np.zeros(len(bars))
    want = np.where(tod >= t_entry, go_today, want)                                  # evening: hold the night position
    want = np.where(tod < OPEN_MIN + BAR_MIN * (params['q'] - 1), go_prev, want)     # next morning: hold q bars
    return pd.Series(want.astype(float), index=idx)
