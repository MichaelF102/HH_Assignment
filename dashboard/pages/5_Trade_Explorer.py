import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import streamlit as st

from core import charts, loaders as L, t1_engine as E1, t2_engine as E2, ui

ui.page_setup('Trade Explorer')
task = st.radio('Task', ['Task 1', 'Task 2'], horizontal=True)

if task == 'Task 1':
    s = ui.t1_state()
    r = E1.run(s['approach'], s['pj'], s['delay'], s['cost'], s['start'], s['end'])
    st.caption('%s | delay %d | cost x%s' % (E1.APPROACHES[s['approach']], s['delay'], s['cost']))
    t = r['trades'].copy()
    t['year'] = t.entry.dt.year
    f1, f2 = st.columns(2)
    yrs = f1.multiselect('Year', sorted(t.year.unique()), default=sorted(t.year.unique()))
    out = f2.radio('Outcome', ['All', 'Winners', 'Losers'], horizontal=True)
    t = t[t.year.isin(yrs)]
    t = t[t.ret > 0] if out == 'Winners' else t[t.ret <= 0] if out == 'Losers' else t
    t = t.sort_values('entry', ascending=False).reset_index(drop=True)
    ev = st.dataframe(t.style.format({'ret': '{:.3%}'}), hide_index=True, width='stretch', height=300, on_select='rerun', selection_mode='single-row')
    st.download_button('Download (CSV)', t.to_csv(index=False), 'task1_trades.csv', 'text/csv')
    sel = ev.selection.rows
    if sel:
        row = t.iloc[sel[0]]
        d = row.entry.normalize()
        bars = L.bars()
        chunk = bars[(bars.index >= d - pd.Timedelta(days=2)) & (bars.index < d + pd.Timedelta(days=4))]
        st.plotly_chart(charts.intraday(chunk, r['pos'], 'Trade entered %s, return %.3f%%' % (row.entry, 100 * row.ret)), width='stretch')
    else:
        st.caption('Select a row for the 15-minute chart.')
else:
    res, stale = ui.t2_current()
    ui.stale_banner(stale)
    T = res['trades'].copy()
    T['year'] = T.entry_date.dt.year
    f1, f2, f3, f4 = st.columns(4)
    syms = f1.multiselect('Symbol', sorted(T.symbol.unique()))
    yrs = f2.multiselect('Entry year', sorted(T.year.unique()), default=sorted(T.year.unique()))
    out = f3.radio('Outcome', ['All', 'Winners', 'Losers'], horizontal=True)
    why = f4.multiselect('Exit reason', sorted(T.why.unique()), default=sorted(T.why.unique()))
    T = T[T.year.isin(yrs) & T.why.isin(why)]
    if syms:
        T = T[T.symbol.isin(syms)]
    T = T[T.ret > 0] if out == 'Winners' else T[T.ret <= 0] if out == 'Losers' else T
    T = T.sort_values('ret', ascending=False).reset_index(drop=True)
    m = st.columns(4)
    m[0].metric('Trades shown', len(T)); m[1].metric('Win rate', ui.pct((T.ret > 0).mean(), 0) if len(T) else 'n/a')
    m[2].metric('Average trade', ui.pct(T.ret.mean()) if len(T) else 'n/a'); m[3].metric('Avg days held', '%.0f' % T.days.mean() if len(T) else 'n/a')
    ev = st.dataframe(T.drop(columns=['year']).style.format({'ret': '{:.1%}'}), hide_index=True, width='stretch', height=320, on_select='rerun', selection_mode='single-row')
    st.download_button('Download (CSV)', T.to_csv(index=False), 'task2_trades.csv', 'text/csv')
    sel = ev.selection.rows
    if sel:
        row = T.iloc[sel[0]]
        c = L.stocks()['close'][row.symbol].dropna()
        lo, hi = row.entry_date - pd.Timedelta(days=45), row.exit_date + pd.Timedelta(days=45)
        c = c[(c.index >= lo) & (c.index <= hi)]
        st.plotly_chart(charts.price_with_trade(c, row.entry_date, row.exit_date, '%s: %s to %s, return %.1f%% (%s exit)' % (row.symbol, str(row.entry_date.date()), str(row.exit_date.date()), 100 * row.ret, row.why)), width='stretch')
    else:
        st.caption('Select a row for the price chart.')
