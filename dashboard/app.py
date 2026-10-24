"""Overview page. Run:  .venv/bin/streamlit run dashboard/app.py"""
import pandas as pd
import streamlit as st

from core import charts, loaders as L, metrics as M, t1_engine as E1, t2_engine as E2, ui

ui.page_setup('Overview')
H = L.H
st.caption('Task 1: Nifty futures, 15-minute bars. Task 2: NSE stocks, daily, long-only. Harness results.')
ui.scope_note()

s1 = ui.t1_state()
r1 = E1.run(s1['approach'], s1['pj'], s1['delay'], s1['cost'], s1['start'], s1['end'])
r2, stale = ui.t2_current()
s2 = ui.t2_state()
st2, e2 = E2.window_stats(r2, s2['start'], s2['end'])
ui.stale_banner(stale)

a, b = st.columns(2)
with a:
    st.subheader('Task 1: Nifty futures (15-minute bars)')
    st.caption('%s | delay %d bar(s) | cost x%s | %s to %s' % (E1.APPROACHES[s1['approach']], s1['delay'], s1['cost'], s1['start'], s1['end']))
    st1 = r1['stats']
    ui.stat_row(st1, '6% cash')
    st.markdown('Bar: Sharpe > 1.0 (%s), max drawdown better than -15%% (%s). Reference: Sharpe 1.22, DD -12.8%%, CAGR 23.3%%.' %
                (ui.badge(st1['sharpe'] > 1.0), ui.badge(st1['max_dd'] > -0.15)))
    bm = E1.benchmark_curve()
    bm = bm[(bm.index >= r1['eq'].index[0]) & (bm.index <= r1['eq'].index[-1])]
    st.plotly_chart(charts.equity({'Strategy': r1['eq'], 'Nifty spot': bm}, 'Equity (start = 1)', height=300), width='stretch')
with b:
    st.subheader('Task 2: NSE momentum (daily, long-only)')
    p = s2['params']
    st.caption('n=%d lb=%d rebal=%d sma=%d volq=%.2f | cost %.2f%% per side | %s to %s' % (
        p['n'], p['lb'], p['rebal'], p['sma'], p['volq'], 100 * s2['cost'], s2['start'], s2['end']))
    ui.stat_row(st2, '0% cash')
    st.markdown('Bar: Sharpe > 1.9 (%s), max drawdown better than -25%% (%s). Reference: Sharpe 1.93, DD -23.9%%, CAGR 51.6%%.' %
                (ui.badge(st2['sharpe'] > 1.9), ui.badge(st2['max_dd'] > -0.25)))
    nif = L.stocks()['nifty']['close']
    nif = nif[(nif.index >= e2.index[0]) & (nif.index <= e2.index[-1])]
    st.plotly_chart(charts.equity({'Strategy': e2, 'Nifty 50': nif}, 'Equity (start = 1)', height=300), width='stretch')

st.subheader('Year-wise returns')
c1, c2 = st.columns(2)
y1, y2 = M.yearly(r1['eq']), M.yearly(e2)
c1.plotly_chart(charts.bars(y1.index, y1.values, 'Task 1'), width='stretch')
c2.plotly_chart(charts.bars(y2.index, y2.values, 'Task 2 (2024 = first half)'), width='stretch')
