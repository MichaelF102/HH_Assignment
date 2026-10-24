import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import streamlit as st

from core import charts, loaders as L, metrics as M, t1_engine as E1, ui

ui.page_setup('Task 1 Robustness')
H = L.H
s = ui.t1_controls(show_scenario=False)
R = L.t1_results()
st.caption('Approach %s, params %s. Precomputed tables: submitted strategy, full visible window.' % (s['approach'], s['params']))


st.header('Delay and costs')
with st.container():
    st.markdown('Each approach (default parameters) under every scenario. Delay shifts fills by whole bars; costs scale 0.025% per side and the roll.')
    frames = []
    for k in E1.APPROACHES:
        t = E1.scenario_table(k, E1.pj(E1.default_params(k)))
        t.insert(0, 'Approach', k)
        frames.append(t)
    all_ = pd.concat(frames)
    metric = st.radio('Metric', ['Sharpe', 'MaxDD', 'CAGR'], horizontal=True)
    piv = all_.pivot(index='Approach', columns='Scenario', values=metric)[list(E1.SCENARIOS)]
    fmt = '{:.2f}' if metric == 'Sharpe' else '{:.1%}'
    st.dataframe(piv.style.format(fmt).background_gradient(cmap='RdYlGn', axis=None), width='stretch')
    st.markdown('**Selected approach (%s)**' % s['approach'])
    cur = E1.scenario_table(s['approach'], s['pj'], s['start'], s['end'])
    st.dataframe(cur.style.format({'Sharpe': '{:.2f}', 'MaxDD': '{:.1%}', 'CAGR': '{:.1%}'}), hide_index=True, width='stretch')
    st.caption('Delay of 3 or more bars puts the entry after the close.')

st.header('Sensitivity')
with st.container():
    sub = st.radio('Grid', ['sma x mom', 'p x q', 'sma x p'], horizontal=True)
    key = {'sma x mom': 'grid_sma_mom', 'p x q': 'grid_p_q', 'sma x p': 'grid_sma_p'}[sub]
    G = R[key]
    metric = st.radio('Show', ['Sharpe', 'Sharpe with 1-bar delay', 'Max drawdown', 'CAGR'], horizontal=True, key='sens_metric')
    pick = {'Sharpe': 'sharpe', 'Sharpe with 1-bar delay': 'd1', 'Max drawdown': 'dd', 'CAGR': 'cagr'}[metric]
    z = np.array([[c[pick] for c in row] for row in G['cells']])
    sub_p = L.submitted_params(1)
    hi = (G['v1'].index(sub_p[G['ax1']]) if sub_p[G['ax1']] in G['v1'] else None, G['v2'].index(sub_p[G['ax2']]) if sub_p[G['ax2']] in G['v2'] else None)
    st.plotly_chart(charts.heatmap(z, G['v2'], G['v1'], G['ax2'], G['ax1'], '%s: %s' % (sub, metric), pct=pick in ('dd', 'cagr'),
                                   highlight=hi if None not in hi else None, reverse=pick == 'dd'), width='stretch')
    st.caption('Orange box: submitted setting. Same data the parameters were chosen on.')
    with st.expander('Live grid (recompute with the harness)'):
        opts = {'sma': [50, 100, 150, 200], 'p': [0, 1, 2, 3], 'q': [1, 2, 3], 'mom': [-0.002, 0.0, 0.002]}
        c1, c2, c3 = st.columns(3)
        a1 = c1.selectbox('Rows', list(opts), index=0)
        a2 = c2.selectbox('Columns', [k for k in opts if k != a1], index=1)
        dl = c3.select_slider('Fill delay', [0, 1, 2], value=0)
        if st.button('Compute live grid'):
            z = E1.live_grid(E1.pj(L.submitted_params(1)), a1, opts[a1], a2, opts[a2], dl)
            m = st.radio('Live metric', ['Sharpe', 'Max drawdown', 'CAGR'], horizontal=True, key='live_m')
            i = {'Sharpe': 0, 'Max drawdown': 1, 'CAGR': 2}[m]
            st.plotly_chart(charts.heatmap(z[:, :, i], opts[a2], opts[a1], a2, a1, 'Live: %s (delay %d)' % (m, dl), pct=i > 0, reverse=i == 1), width='stretch')

st.header('Walk-forward')
with st.container():
    W, sc = R['walk_forward'], pd.DataFrame(R['wf_scores'])
    st.markdown('72 settings scored on each half (split %s). Each point is one setting.' % R['wf_split'])
    st.plotly_chart(charts.scatter(sc.h1_base, sc.h2_base, sc.apply(lambda r: 'sma %d p %d q %d mom %.3f' % (r.sma, r.p, r.q, r.mom), axis=1),
                                   'Sharpe: first half vs second half', 'first half Sharpe', 'second half Sharpe'), width='stretch')
    c1, c2 = st.columns(2)
    for col, name, key in ((c1, 'Chosen on first half, tested on second', 'train_first'), (c2, 'Chosen on second half, tested on first', 'train_second')):
        w = W[key]
        col.markdown('**%s**' % name)
        col.write('Setting (sma, p, q, mom): %s' % w['par'])
        col.metric('In-sample Sharpe', '%.2f' % w['in_sample_sharpe'])
        col.metric('Out-of-sample Sharpe', '%.2f' % w['oos_sharpe'])
        col.caption('Held-out half, 1-bar delay: %.2f, max DD %s' % (w['oos_d1'], ui.pct(w['oos_dd'])))
    st.caption('Stability check, not out-of-sample: setting ranks are uncorrelated across halves (0.02) and every setting is better in the second half (median %.2f vs %.2f). Submitted setting: %.2f first half, %.2f second.' % (
        W['median_h2'], W['median_h1'], W['fixed_choice']['first_half'], W['fixed_choice']['second_half']))
    st.dataframe(sc.sort_values('h1_base', ascending=False).style.format({c: '{:.2f}' for c in sc.columns if c.startswith('h') and 'dd' not in c} | {'h1_dd': '{:.1%}', 'h2_dd': '{:.1%}', 'mom': '{:.3f}'}),
                 hide_index=True, width='stretch', height=300)

st.header('Sub-periods and best year')
with st.container():
    r = E1.run(s['approach'], s['pj'], 0, 1)
    rows = []
    for name, (lo, hi) in {'2017-18': ('2017-04-01', '2018-12-31'), '2019': ('2019-01-01', '2019-12-31'), '2020': ('2020-01-01', '2020-12-31'), '2021 to Jan 2022': ('2021-01-01', '2022-01-31')}.items():
        x = E1.run(s['approach'], s['pj'], 0, 1, lo, hi)['stats']
        rows.append({'Period': name, 'Sharpe': x['sharpe'], 'Max DD': x['max_dd'], 'CAGR': x['cagr'], 'Trades': x['trades']})
    st.markdown('**Sub-periods**')
    st.dataframe(pd.DataFrame(rows).style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.1%}', 'CAGR': '{:.1%}'}), hide_index=True, width='stretch')
    dy = M.drop_year(r['daily'], H.R_CASH)
    st.markdown('**Sharpe excluding each year**')
    st.dataframe(dy.style.format({'Sharpe': '{:.2f}', 'AnnReturn': '{:.1%}'}), hide_index=True, width='stretch')
    st.caption('2022 is January only.')

st.header('Overnight-gap diagnostic')
with st.container():
    inbar, by_year, gap_bp, t = E1.tod_profile()
    st.markdown('Overnight gap vs session return.')
    c1, c2, c3 = st.columns(3)
    c1.metric('Mean overnight gap', '%.1f bp' % gap_bp); c2.metric('t-statistic', '%.1f' % t); c3.metric('Positive full years', '%d of %d' % ((by_year.iloc[:-1] > 0).sum(), len(by_year) - 1))
    st.plotly_chart(charts.bars(inbar.index, (inbar / 1e4).values, 'Average return by 15-minute bar of the day (the 09:15 bar gives back the gap)', height=300, fmt='.2%'), width='stretch')
    st.plotly_chart(charts.bars(by_year.index.astype(str), (by_year / 1e4).values, 'Average overnight gap by year (2022 = January only)', height=260, fmt='.2%'), width='stretch')
    st.caption('Spot-index gap; futures executability untested.')
