import numpy as np
import pandas as pd


def drawdown(eq):
    return eq / eq.cummax() - 1


def yearly(eq):
    y = pd.concat([eq.iloc[:1], eq.resample('YE').last()]).pct_change().dropna()
    return pd.Series(y.values, index=[str(d.year) for d in y.index])


def monthly_table(eq):
    m = eq.resample('ME').last().pct_change().dropna()
    t = pd.DataFrame({'y': m.index.year, 'm': m.index.month, 'r': m.values}).pivot(index='y', columns='m', values='r')
    t.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:t.shape[1]] if t.shape[1] == 12 else t.columns
    return t


def rolling_sharpe(daily_ret, rf_annual, window=126):
    ex = daily_ret - rf_annual / 252
    return ex.rolling(window).mean() / ex.rolling(window).std() * np.sqrt(252)


def sharpe(daily_ret, rf_annual):
    ex = daily_ret - rf_annual / 252
    return float(ex.mean() / ex.std() * np.sqrt(252)) if ex.std() > 0 else 0.0


def drop_year(daily_ret, rf_annual):
    """Sharpe and annualised mean return with each calendar year removed."""
    rows = []
    for y in sorted(set(daily_ret.index.year)):
        x = daily_ret[daily_ret.index.year != y]
        rows.append(dict(Removed=str(y), Sharpe=sharpe(x, rf_annual), AnnReturn=float(x.mean() * 252)))
    return pd.DataFrame(rows)


def top_n_share(trades, n_pos, top=10):
    """Share of profit from the best `top` trades (equal-weight 1/n_pos approximation of P&L)."""
    pnl = (trades.ret / n_pos).sort_values(ascending=False)
    gross = pnl[pnl > 0].sum()
    return dict(gross=float(pnl.iloc[:top].sum() / gross) if gross > 0 else np.nan,
                net=float(pnl.iloc[:top].sum() / pnl.sum()) if pnl.sum() != 0 else np.nan, idx=list(pnl.index[:top]))
