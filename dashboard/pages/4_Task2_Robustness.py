import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import streamlit as st

from core import charts, loaders as L, metrics as M, t2_engine as E2, ui

ui.page_setup('Task 2 Robustness')
H = L.H
s = ui.t2_controls()
R = L.t2_results()
res, stale = ui.t2_current()
ui.stale_banner(stale)
st.caption('Precomputed from the submitted task2.py, other parameters at submitted values. Best-year and top-trade tabs use the result selected in the sidebar.')


st.header('Sensitivity')
with st.container():
    grids = {'volq x sma': ('g_volq_sma', 'volq', [0.6, 0.75, 0.9], 'sma', [40, 50, 70]), 'n x lb': ('g_n_lb', 'n', [8, 10, 12], 'lb', [84, 126, 168]),
             'rebal x volq': ('g_rebal_volq', 'rebal', [10, 21, 30], 'volq', [0.6, 0.75, 0.9])}
    sel = st.radio('Grid', list(grids), horizontal=True)
    key, a1, v1, a2, v2 = grids[sel]
    metric = st.radio('Show', ['Sharpe', 'Max drawdown', 'CAGR', 'Time in market'], horizontal=True)
    pick = {'Sharpe': 'sharpe', 'Max drawdown': 'max_dd', 'CAGR': 'cagr', 'Time in market': 'time_in_market'}[metric]
    z = np.full((len(v1), len(v2)), np.nan)
    for row in R[key]:
        z[v1.index(row['kw'][a1]), v2.index(row['kw'][a2])] = row[pick]
    sub_p = L.submitted_params(2)
    hi = (v1.index(sub_p[a1]), v2.index(sub_p[a2])) if sub_p[a1] in v1 and sub_p[a2] in v2 else None
    st.plotly_chart(charts.heatmap(z, v2, v1, a2, a1, '%s: %s' % (sel, metric), pct=pick != 'sharpe', highlight=hi, reverse=pick == 'max_dd'), width='stretch')
    st.caption('Orange box: submitted setting. n x lb is flat (Sharpe 2.0 to 2.5); volq is not: 0.75 is a peak (0.60: 1.5 to 1.7; 0.90: 1.7 to 2.1). Same data the parameters were chosen on.')

st.header('Costs and sub-windows')
with st.container():
    c1, c2 = st.columns(2)
    cost = pd.DataFrame([{'Cost per side': '%.1f%%' % (100 * r['extra']['cost']), 'Sharpe': r['sharpe'], 'Max DD': r['max_dd'], 'CAGR': r['cagr']} for r in R['cost']])
    c1.markdown('**Cost sweep** (per side)')
    c1.dataframe(cost.style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.1%}', 'CAGR': '{:.1%}'}), hide_index=True, width='stretch')
    win = pd.DataFrame([{'Window': '%s to %s' % (r['extra']['start'][:7], r['extra']['end'][:7]), 'Sharpe': r['sharpe'], 'Max DD': r['max_dd'], 'Return': r['total_return'], 'Trades': r['trades']} for r in R['window']])
    c2.markdown('**Sub-windows**')
    c2.dataframe(win.style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.1%}', 'Return': '{:.1%}'}), hide_index=True, width='stretch')
    st.caption('2022 and 2024 H1 are the weakest windows (Sharpe about 1.4).')

st.header('Best year removed')
with st.container():
    e = res['eq']
    dy = M.drop_year(e.pct_change().dropna(), 0.0)
    st.dataframe(dy.style.format({'Sharpe': '{:.2f}', 'AnnReturn': '{:.1%}'}), hide_index=True, width='stretch')
    st.caption('Daily-return Sharpe without each calendar year (2022 from March, 2024 to June).')

st.header('Top trades')
with st.container():
    T = res['trades']
    n = s['params']['n']
    sh = M.top_n_share(T, n)
    c1, c2, c3 = st.columns(3)
    c1.metric('Top 10 trades: share of gross profit', ui.pct(sh['gross'], 0))
    c2.metric('Top 10 trades: share of net P&L', ui.pct(sh['net'], 0))
    c3.metric('Trades', len(T))
    pnl = (T.ret / n).sort_values(ascending=False)
    top = T.loc[pnl.index[:20]]
    fig = charts.bars(['%s %s' % (r.symbol, str(r.entry_date.date())[:7]) for r in top.itertuples()], (pnl.iloc[:20]).values, 'Contribution to portfolio return, top 20 trades (return / n)', height=320, fmt='.1%')
    st.plotly_chart(fig, width='stretch')
    cum = pnl.cumsum() / pnl[pnl > 0].sum()
    st.plotly_chart(charts.line({'Cumulative share of gross profit': pd.Series(cum.values, index=range(1, len(cum) + 1))}, 'Concentration: best k trades vs share of gross profit', yfmt='.0%', height=240), width='stretch')
    st.caption('Equal-weight approximation (return / n).')

st.header('Universe stress and survivorship')
with st.container():
    base = R['base'][0]
    d30 = R['drop30']
    st.markdown('**Random 30% of names removed** (6 seeds, 0.2% per side)')
    df = pd.DataFrame([{'Seed': r['extra']['drop_seed'], 'Sharpe': r['sharpe'], 'Max DD': r['max_dd'], 'CAGR': r['cagr']} for r in d30])
    c1, c2 = st.columns([1, 1])
    c1.dataframe(df.style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.1%}', 'CAGR': '{:.1%}'}), hide_index=True, width='stretch')
    c1.caption('Full universe: Sharpe %.2f, DD %s, CAGR %s. Mean of drops: Sharpe %.2f (min %.2f), worst DD %s.' % (
        base['sharpe'], ui.pct(base['max_dd']), ui.pct(base['cagr']), df.Sharpe.mean(), df.Sharpe.min(), ui.pct(df['Max DD'].min())))
    c2.plotly_chart(charts.bars(['full'] + ['seed %d' % x for x in df.Seed], [base['sharpe']] + list(df.Sharpe), 'Sharpe by universe', height=260, fmt='.2f'), width='stretch')
    ex = R['excl_winners'][0]
    st.markdown('**Best 15% of names by realised return removed** (hindsight, 0.2% per side)')
    st.write('Sharpe %.2f, max DD %s, CAGR %s' % (ex['sharpe'], ui.pct(ex['max_dd']), ui.pct(ex['cagr'])))
    st.caption('Universe = stocks liquid in October 2026; delisted, merged and illiquid names are missing. Neither removal test is a survivorship estimate. The bias is smaller in the hidden window, not absent.')
