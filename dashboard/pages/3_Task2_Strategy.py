import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import streamlit as st

from core import charts, loaders as L, metrics as M, t2_engine as E2, ui

ui.page_setup('Task 2 Strategy')
H = L.H
s = ui.t2_controls(with_run=True)
res, stale = ui.t2_current()
ui.stale_banner(stale)
st2, e2 = E2.window_stats(res, s['start'], s['end'])
p = s['params']

st.caption('n=%d lb=%d rebal=%d sma=%d volq=%.2f | cost %.2f%% per side | %s to %s. Submitted configuration is precomputed; other settings need Run backtest.' % (
    p['n'], p['lb'], p['rebal'], p['sma'], p['volq'], 100 * s['cost'], s['start'], s['end']))
ui.stat_row(st2, '0% (idle cash earns nothing)')
st.markdown('Bar: Sharpe > 1.9 (%s), max drawdown better than -25%% (%s). Average hold %.0f days; turnover %.1fx per year.' % (
    ui.badge(st2['sharpe'] > 1.9), ui.badge(st2['max_dd'] > -0.25), st2['avg_hold_days'], res['stats'].get('turnover_per_yr', float('nan'))))

tab_eq, tab_year, tab_br, tab_hold = st.tabs(['Equity and drawdown', 'Year-wise and monthly', 'Volatility cap and exposure', 'Holdings and candidates'])
nif = L.stocks()['nifty']['close']
nif = nif[(nif.index >= e2.index[0]) & (nif.index <= e2.index[-1])]

with tab_eq:
    log = st.toggle('Log scale', value=False)
    st.plotly_chart(charts.equity({'Strategy': e2, 'Nifty 50 (price only)': nif}, 'Equity (start = 1)', log=log), width='stretch')
    st.plotly_chart(charts.drawdown_chart({'Strategy': M.drawdown(e2), 'Nifty 50': M.drawdown(nif)}), width='stretch')
    win = st.select_slider('Rolling Sharpe window (trading days)', [42, 63, 126], value=63)
    rs = M.rolling_sharpe(e2.pct_change().dropna(), 0.0, win).dropna()
    st.plotly_chart(charts.line({'Rolling Sharpe': rs}, 'Rolling Sharpe (0% risk-free)', hline=0), width='stretch')

with tab_year:
    y = M.yearly(e2)
    c1, c2 = st.columns(2)
    c1.plotly_chart(charts.bars(y.index, y.values, 'Calendar-year return (2022 from March, 2024 to June)'), width='stretch')
    c2.markdown('**Sharpe excluding each year**')
    c2.dataframe(M.drop_year(e2.pct_change().dropna(), 0.0).style.format({'Sharpe': '{:.2f}', 'AnnReturn': '{:.1%}'}), hide_index=True, width='stretch')
    st.markdown('**Monthly returns**')
    st.dataframe(M.monthly_table(e2).style.format('{:.1%}', na_rep='').background_gradient(cmap='RdYlGn', vmin=-.1, vmax=.1, axis=None), width='stretch')

with tab_br:
    cap, med = E2.vol_cap_series(p['volq'])
    cap, med = [x[(x.index >= e2.index[0]) & (x.index <= e2.index[-1])] for x in (cap, med)]
    st.plotly_chart(charts.line({'Cap (stocks above it are ignored)': cap, 'Universe median': med}, '60-day volatility of liquid stocks: the cap at quantile %.2f vs the median' % p['volq'], yfmt='.0%', height=280), width='stretch')
    g = res['gross'][(res['gross'].index >= e2.index[0]) & (res['gross'].index <= e2.index[-1])]
    st.plotly_chart(charts.line({'Invested fraction': g}, 'Invested fraction of equity (the rest is idle cash earning 0%)', yfmt='.0%', height=240), width='stretch')
    st.caption('No market-level brake; almost always fully invested. The sample has no long bear market.')

with tab_hold:
    dates = list(e2.index)
    d = st.select_slider('As of the close of', options=[x.date() for x in dates], value=dates[-1].date())
    c1, c2 = st.columns(2)
    h = E2.holdings_on(res, d)
    c1.markdown('**Open positions at that close** (closed trades only; positions open at the end are not listed)')
    c1.dataframe(h[['symbol', 'entry_date', 'exit_date', 'days', 'ret', 'why']].rename(columns={'ret': 'final trade return'}).style.format({'final trade return': '{:.1%}'}), hide_index=True, width='stretch')
    cand, any_ = E2.candidates(d, p)
    c2.markdown('**Target portfolio if rebalanced that day** (orders() on an empty book)')
    if len(cand):
        c2.dataframe(cand.style.format({'momentum': '{:.1%}', 'close': '{:.2f}'}), hide_index=True, width='stretch')
    else:
        c2.info('No buys: too few names pass the filters.')
