"""
H TO H PARTNERS LLP - Quant Research Intern assignment: public backtest harness.

This file is the ONLY accounting your results are judged with. Do not modify it; we run your code
with an identical copy on data you have not seen.

    python harness_public.py task1 task1_template.py         # Nifty 15-min futures strategy
    python harness_public.py task2 task2_template.py         # NSE stock portfolio strategy

Needs only numpy + pandas. See README.md for the full rules.
"""
import argparse, importlib.util, os, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')

R_CASH = 0.06          # idle capital earns 6%/yr (liquid fund), credited daily as R_CASH/252
DIV_YIELD = 0.013      # Nifty dividend yield; futures carry per night = (R_CASH - DIV_YIELD)/252 of notional
T1_COST = 0.00025      # Task 1: 0.025% of notional per side
T1_WARMUP = 200        # Task 1: no position during the first 200 bars
T2_COST = 0.002        # Task 2: 0.2% of traded value per side
T2_MAX_POS = 15        # Task 2: at most 15 open positions
T2_MAX_W = 0.15        # Task 2: at most 15% of portfolio value per new position
T2_START = '2022-03-01'    # Task 2 evaluation window (first trading day is 2022-03-02)
T2_END = '2024-06-30'
MAX_PARAMS = 6


# ----------------------------------------------------------------------------------------------- loading
def load_module(path):
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def check_params(m):
    p = getattr(m, 'PARAMS', None)
    if not isinstance(p, dict): raise ValueError('module must define PARAMS = {...} (a dict, max %d entries)' % MAX_PARAMS)
    if len(p) > MAX_PARAMS: raise ValueError('PARAMS has %d entries, max allowed is %d' % (len(p), MAX_PARAMS))
    return dict(p)


def load_bars(*paths):
    """15-min Nifty bars: DatetimeIndex (bar START time, IST) and columns open, high, low, close."""
    b = pd.concat([pd.read_csv(p, parse_dates=['datetime']) for p in paths])
    b = b.drop_duplicates('datetime').set_index('datetime').sort_index()
    return b[['open', 'high', 'low', 'close']].astype(float)


def load_expiries(path):
    return set(pd.to_datetime(pd.read_csv(path).expiry_date))


def load_stocks(stock_paths, nifty_paths):
    """Returns dict of wide DataFrames (index = date, columns = symbol): open, high, low, close, volume,
    plus 'nifty' = Nifty 50 daily OHLC DataFrame on the same dates."""
    df = pd.concat([pd.read_csv(p, parse_dates=['date']) for p in stock_paths])
    df = df[df.symbol != 'NIFTY50'].drop_duplicates(['date', 'symbol'])
    D = {k: df.pivot(index='date', columns='symbol', values=k).sort_index().astype(float)
         for k in ('open', 'high', 'low', 'close', 'volume')}
    n = pd.concat([pd.read_csv(p, parse_dates=['date']) for p in nifty_paths]).drop_duplicates('date')
    n = n.set_index('date').sort_index()[['open', 'high', 'low', 'close']]
    D['nifty'] = n.reindex(D['close'].index).ffill()
    return D


# ----------------------------------------------------------------------------------------------- stats
def stats(eq, trades, rf, extra=None):
    """eq: daily equity Series (close of each day). trades: list of round-trip returns.
    rf: daily-annual risk-free used in Sharpe = what idle cash earns in that task (6% Task 1, 0% Task 2)."""
    r = eq.pct_change().dropna(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    t = np.asarray(trades, float)
    dd = float((eq / eq.cummax() - 1).min())
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) if yrs > 0 else np.nan
    sd = r.std()
    out = dict(cagr=cagr, total_return=float(eq.iloc[-1] / eq.iloc[0] - 1), max_dd=dd,
               sharpe=float((r.mean() - rf / 252) / sd * np.sqrt(252)) if sd > 0 else 0.0,
               calmar=cagr / -dd if dd < 0 else np.nan, years=yrs, trades=len(t),
               win_rate=float((t > 0).mean()) if len(t) else np.nan,
               avg_trade=float(t.mean()) if len(t) else np.nan)
    if extra: out.update(extra)
    y = pd.concat([eq.iloc[:1], eq.resample('YE').last()]).pct_change().dropna()
    out['yearly'] = {str(d.year): float(v) for d, v in y.items()}
    return out


def print_stats(title, s):
    print('\n' + title); print('-' * len(title))
    pct = {'cagr', 'total_return', 'max_dd', 'win_rate', 'avg_trade', 'time_in_market'}
    for k, v in s.items():
        if k == 'yearly': continue
        if isinstance(v, (float, np.floating)) and np.isnan(v): print('%-16s %s' % (k, 'n/a')); continue
        print('%-16s %s' % (k, ('%.2f%%' % (100 * v)) if k in pct else ('%d' % v if k == 'trades' else '%.3f' % v)))
    print('year-wise return:')
    for yr, v in s['yearly'].items(): print('   %s  %7.2f%%' % (yr, 100 * v))


# ----------------------------------------------------------------------------------------------- task 1
def task1_positions(m, bars, params):
    """Call the candidate's positions(bars, params) and validate the output."""
    p = m.positions(bars.copy(), dict(params))
    p = pd.Series(np.asarray(p, float) if not isinstance(p, pd.Series) else p.values.astype(float), index=bars.index)
    if p.isna().any(): raise ValueError('positions() returned NaN')
    if not p.isin([-1.0, 0.0, 1.0]).all(): raise ValueError('positions() must return only -1, 0 or 1')
    return p


def task1_backtest(bars, want, expiries, cost=T1_COST, warm=T1_WARMUP):
    """want[i] = position decided at the CLOSE of bar i. It is filled at the OPEN of bar i+1.
    Daily accounting (all as a fraction of capital, summed within the day):
      overnight gap  pos_prev * (open_i / close_{i-1} - 1)
      in-bar move    pos_i * (close_i / open_i - 1)
      trading cost   |pos_i - pos_prev| * cost
      on a new day, a position carried overnight pays pos * (R_CASH - DIV_YIELD)/252 and, if the previous day was
      a monthly expiry, 2 * cost * |pos| for the roll.
      every day capital also earns R_CASH/252 (margin sits in a liquid fund).
    Returns dict(daily=Series of daily return excluding cash, pos=bar positions, trades=[(entry_time, ret)])."""
    o, c = bars.open.values, bars.close.values; N = len(c)
    want = np.asarray(want, float)
    pos = np.zeros(N); pos[1:] = want[:-1]; pos[:warm] = 0
    prev = np.r_[0.0, pos[:-1]]
    pc = np.r_[c[0], c[:-1]]
    day = bars.index.normalize()
    newday = np.r_[False, day[1:] != day[:-1]]
    prev_day = np.r_[day[:1], day[:-1]]
    is_exp = np.isin(prev_day, pd.DatetimeIndex(sorted(expiries)))
    contrib = prev * (o / pc - 1) + pos * (c / o - 1) - np.abs(pos - prev) * cost
    contrib -= np.where(newday, prev * (R_CASH - DIV_YIELD) / 252 + is_exp * 2 * cost * np.abs(prev), 0.0)
    daily = pd.Series(contrib, index=day).groupby(level=0).sum()
    # round trips (entry at an open, exit at an open; cost both sides; carry/roll ignored in the per-trade number)
    trades, tr, t_in = [], None, None
    for i in range(1, N):
        if tr is not None: tr *= 1 + prev[i] * (o[i] / pc[i] - 1)
        if pos[i] != prev[i]:
            if tr is not None: trades.append((t_in, tr * (1 - cost) - 1)); tr = None
            if pos[i] != 0: tr, t_in = 1 - cost, bars.index[i]
        if tr is not None: tr *= 1 + pos[i] * (c[i] / o[i] - 1)
    return dict(daily=daily, pos=pd.Series(pos, index=bars.index), trades=trades)


def task1_stats(res, start=None, end=None):
    d = res['daily']; ps = res['pos']; lo = pd.Timestamp(start) if start else d.index[0]
    hi = pd.Timestamp(end) if end else d.index[-1]
    d = d[(d.index >= lo) & (d.index <= hi)]
    ps = ps[(ps.index.normalize() >= lo) & (ps.index.normalize() <= hi)]
    eq = (1 + d + R_CASH / 252).cumprod()
    tr = [r for t, r in res['trades'] if lo <= t.normalize() <= hi]
    yrs = max((d.index[-1] - d.index[0]).days / 365.25, 1e-9)
    act = ps.iloc[T1_WARMUP:] if start is None else ps
    extra = dict(turnover_per_yr=float(np.abs(ps.diff().fillna(ps.iloc[0])).sum() / yrs),
                 time_in_market=float((act != 0).mean()))
    return stats(eq, tr, R_CASH, extra), eq


def lookahead_check(m, bars, params, full, n=4, seed=7):
    """Re-run positions() on truncated data at a few cut points; the last value must equal the full-data value."""
    rng = np.random.default_rng(seed); bad = []
    for k in sorted(rng.integers(T1_WARMUP + 50, len(bars) - 1, n)):
        p = task1_positions(m, bars.iloc[:k + 1], params)
        if p.iloc[-1] != full.iloc[k]: bad.append(str(bars.index[k]))
    return bad


def run_task1(path, bar_files=None, expiry_file=None):
    m = load_module(path); params = check_params(m)
    bars = load_bars(*(bar_files or [os.path.join(DATA, 'nifty50_15min_train_2017-04-03_2022-01-31.csv')]))
    ex = load_expiries(expiry_file or os.path.join(DATA, 'nifty_monthly_expiries_2017-01_2022-01.csv'))
    t = time.time(); want = task1_positions(m, bars, params); el = time.time() - t
    bad = lookahead_check(m, bars, params, want)
    res = task1_backtest(bars, want.values, ex)
    s, _ = task1_stats(res)
    print('Task 1: %s  params=%s  (positions() took %.1fs)' % (os.path.basename(path), params, el))
    print('look-ahead check: %s' % ('OK' if not bad else 'FAILED at ' + ', '.join(bad)))
    print_stats('Task 1 stats, %s to %s (cash 6%%, cost 0.025%%/side, roll + carry)' % (bars.index[0].date(), bars.index[-1].date()), s)
    return s


# ----------------------------------------------------------------------------------------------- task 2
def _slice(D, t):
    return {k: v.iloc[:t + 1] for k, v in D.items()}


def task2_backtest(m, D, params, start=T2_START, end=None, cost=T2_COST, verbose=False):
    """Daily stock portfolio simulator. Long only, no leverage, starting capital 1.0, idle cash earns 0.

    Every trading day after the close the harness calls
        orders(date, hist, portfolio, params, state) -> list of order dicts
    hist = data up to and including `date` only. The orders are valid for the NEXT trading day only:
      {'symbol': s, 'side': 'buy',  'type': 'market', 'weight': w}            buy at next open
      {'symbol': s, 'side': 'buy',  'type': 'stop', 'trigger': x, 'weight': w} buy if next high > x, at max(open, x)
      {'symbol': s, 'side': 'sell', 'type': 'market'}                         sell whole position at next open
      {'symbol': s, 'side': 'sell', 'type': 'stop', 'trigger': x}             sell if next low < x, at min(open, x)
    Optional on a buy: 'max_positions': k  (fill only while fewer than k positions are open; hard cap 15).
    Buy size = min(w, 15%) * portfolio value at the decision close, capped by available cash.
    Next-day processing order: market sells at the open -> buys in the order given -> stop sells.
    No adding to an existing position; orders on symbols with no price that day lapse.
    Cost 0.2% per side: shares = amount * (1 - cost) / price; proceeds = shares * price * (1 - cost)."""
    O, H, L, C = D['open'].values, D['high'].values, D['low'].values, D['close'].values
    Cf = D['close'].ffill().values
    dates = D['close'].index; cols = list(D['close'].columns); col = {s: j for j, s in enumerate(cols)}
    t0 = int(np.searchsorted(dates, pd.Timestamp(start)))
    t1 = int(np.searchsorted(dates, pd.Timestamp(end), side='right')) - 1 if end else len(dates) - 1
    if t0 < 1: raise ValueError('need at least one day of history before start')
    cash, pos, eq, trades, state = 1.0, {}, [], [], {}
    traded, gross = 0.0, []

    def value(t): return cash + sum(p['n'] * Cf[t, col[s]] for s, p in pos.items())

    def portfolio(t):
        v = value(t)
        return {'cash': cash, 'value': v, 'positions': {s: {'shares': p['n'], 'entry_price': p['px'], 'entry_date': p['in'],
                'value': p['n'] * Cf[t, col[s]]} for s, p in pos.items()}}

    def close(s, px, d, t, why):
        nonlocal cash, traded
        p = pos.pop(s); pr = p['n'] * px * (1 - cost); cash += pr; traded += p['n'] * px
        trades.append({'symbol': s, 'entry_date': p['in'], 'exit_date': d, 'ret': pr / p['cost'] - 1, 'days': t - p['t'], 'why': why})

    pending = m.orders(dates[t0 - 1], _slice(D, t0 - 1), portfolio(t0 - 1), dict(params), state) or []
    for t in range(t0, t1 + 1):
        d = dates[t]; v_prev = value(t - 1)
        sells = [x for x in pending if x.get('side') == 'sell']; buys = [x for x in pending if x.get('side') == 'buy']
        for x in sells:
            s = x['symbol']
            if x.get('type', 'market') == 'market' and s in pos and not np.isnan(O[t, col[s]]): close(s, O[t, col[s]], d, t, 'market')
        for x in buys:
            s = x['symbol']
            if s in pos or s not in col: continue
            if len(pos) >= min(int(x.get('max_positions', T2_MAX_POS)), T2_MAX_POS): continue
            j = col[s]; o_, h_ = O[t, j], H[t, j]
            if np.isnan(o_) or np.isnan(h_): continue
            if x.get('type', 'market') == 'stop':
                trig = float(x['trigger'])
                if not h_ > trig: continue
                px = max(o_, trig)
            else: px = o_
            amt = min(min(float(x.get('weight', 0)), T2_MAX_W) * v_prev, cash)
            if amt <= 1e-12: continue
            cash -= amt; traded += amt
            pos[s] = {'n': amt * (1 - cost) / px, 'px': px, 'in': d, 't': t, 'cost': amt}
        for x in sells:
            s = x['symbol']
            if x.get('type') == 'stop' and s in pos and pos[s]['t'] < t:
                j = col[s]; trig = float(x['trigger'])
                if not np.isnan(L[t, j]) and L[t, j] < trig: close(s, min(O[t, j], trig), d, t, 'stop')
        v = value(t); eq.append((d, v)); gross.append(1 - cash / v if v > 0 else 0)
        if t < t1: pending = m.orders(d, _slice(D, t), portfolio(t), dict(params), state) or []
    E = pd.Series(dict(eq)); T = pd.DataFrame(trades)
    return dict(eq=E, trades=T, gross=pd.Series(gross, index=E.index), traded=traded)


def task2_stats(res, start=None, end=None):
    eq, T, g = res['eq'], res['trades'], res['gross']
    lo = pd.Timestamp(start) if start else eq.index[0]; hi = pd.Timestamp(end) if end else eq.index[-1]
    msk = (eq.index >= lo) & (eq.index <= hi); e = eq[msk]
    tr = T[(T.entry_date >= lo) & (T.entry_date <= hi)].ret.tolist() if len(T) else []
    yrs = max((e.index[-1] - e.index[0]).days / 365.25, 1e-9)
    extra = dict(time_in_market=float(g[msk].mean()), avg_hold_days=float(T.days.mean()) if len(T) else np.nan)
    if start is None and end is None: extra['turnover_per_yr'] = float(res['traded'] / e.mean() / yrs)
    return stats(e, tr, 0.0, extra), e


def run_task2(path, stock_files=None, nifty_files=None):
    m = load_module(path); params = check_params(m)
    D = load_stocks(stock_files or [os.path.join(DATA, 'stocks_daily_train_2021-04-26_2024-06-30.csv')],
                    nifty_files or [os.path.join(DATA, 'nifty50_daily_2021-04-26_2024-06-30.csv')])
    t = time.time(); res = task2_backtest(m, D, params, T2_START, T2_END); el = time.time() - t
    s, _ = task2_stats(res)
    print('Task 2: %s  params=%s  (backtest took %.1fs)' % (os.path.basename(path), params, el))
    print_stats('Task 2 stats, %s to %s (cost 0.2%%/side, max 15 names, 15%% each)' % (res['eq'].index[0].date(), res['eq'].index[-1].date()), s)
    return s


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('task', choices=['task1', 'task2']); ap.add_argument('file')
    a = ap.parse_args()
    (run_task1 if a.task == 'task1' else run_task2)(a.file)
