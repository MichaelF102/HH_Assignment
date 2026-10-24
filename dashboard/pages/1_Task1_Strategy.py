import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import streamlit as st

from core import charts, loaders as L, metrics as M, t1_engine as E1, ui

ui.page_setup('Task 1 Strategy')
H = L.H
s = ui.t1_controls()
r = E1.run(s['approach'], s['pj'], s['delay'], s['cost'], s['start'], s['end'])
st1 = r['stats']

st.caption('%s | params %s | delay %d bar(s) | cost x%s' % (E1.APPROACHES[s['approach']], s['params'], s['delay'], s['cost']))
if s['approach'] == 'C':
    bad = E1.lookahead_status(s['pj'])
    st.caption('Look-ahead check: ' + (':green[OK]' if not bad else ':red[FAILED at %s]' % ', '.join(bad)))
ui.stat_row(st1, '6% cash')
st.markdown('Bar: Sharpe > 1.0 (%s), max drawdown better than -15%% (%s)' % (ui.badge(st1['sharpe'] > 1.0), ui.badge(st1['max_dd'] > -0.15)))

tab_eq, tab_year, tab_intra, tab_trades, tab_cmp = st.tabs(['Equity and drawdown', 'Year-wise and monthly', 'Intraday view', 'Trades', 'Compare approaches'])

with tab_eq:
    bm = E1.benchmark_curve()
    bm = bm[(bm.index >= r['eq'].index[0]) & (bm.index <= r['eq'].index[-1])]
    log = st.toggle('Log scale', value=False)
    st.plotly_chart(charts.equity({'Strategy': r['eq'], 'Nifty spot (buy and hold, price only)': bm}, 'Equity (start = 1)', log=log), width='stretch')
    st.plotly_chart(charts.drawdown_chart({'Strategy': M.drawdown(r['eq']), 'Nifty spot': M.drawdown(bm)}), width='stretch')
    win = st.select_slider('Rolling Sharpe window (trading days)', [63, 126, 252], value=126)
    rs = M.rolling_sharpe(r['daily'], H.R_CASH, win).dropna()
    st.plotly_chart(charts.line({'Rolling Sharpe': rs}, 'Rolling Sharpe (excess over 6% cash)', hline=0), width='stretch')

with tab_year:
    y = M.yearly(r['eq'])
    c1, c2 = st.columns([1, 1])
    c1.plotly_chart(charts.bars(y.index, y.values, 'Calendar-year return (2022 = January only)'), width='stretch')
    dy = M.drop_year(r['daily'], H.R_CASH)
    c2.markdown('**Sharpe excluding each year**')
    c2.dataframe(dy.style.format({'Sharpe': '{:.2f}', 'AnnReturn': '{:.1%}'}), hide_index=True, width='stretch')
    mt = M.monthly_table(r['eq'])
    st.markdown('**Monthly returns**')
    st.dataframe(mt.style.format('{:.1%}', na_rep='').background_gradient(cmap='RdYlGn', vmin=-.06, vmax=.06, axis=None), width='stretch')
    st.caption('Turnover %.0f per year (sum of |position changes|). In market %s.' % (st1['turnover_per_yr'], ui.pct(st1['time_in_market'])))

with tab_intra:
    bars = L.bars()
    days = sorted(set(bars.index.normalize()))
    days = [d for d in days if pd.Timestamp(s['start']) <= d <= pd.Timestamp(s['end'])]
    c1, c2 = st.columns([2, 1])
    first_trade = r['trades'].entry.iloc[0].normalize() if len(r['trades']) else days[0]
    d0 = c1.date_input('Centre date', value=first_trade.date(), min_value=days[0].date(), max_value=days[-1].date())
    span = c2.slider('Trading days shown', 1, 10, 3)
    i = max(min(days.index(min(days, key=lambda x: abs(x - pd.Timestamp(d0)))), len(days) - 1), 0)
    lo, hi = days[max(i - span // 2, 0)], days[min(i + (span + 1) // 2, len(days) - 1)]
    chunk = bars[(bars.index >= lo) & (bars.index < hi + pd.Timedelta(days=1))]
    st.plotly_chart(charts.intraday(chunk, r['pos'], 'Position (shaded) with entry (green) and exit (red) fills'), width='stretch')
    st.caption('Fills at the open of the bar after the decision bar.')

with tab_trades:
    t = r['trades'].copy()
    t['year'] = t.entry.dt.year
    f1, f2, f3 = st.columns(3)
    yrs = f1.multiselect('Year', sorted(t.year.unique()), default=sorted(t.year.unique()))
    side = f2.radio('Outcome', ['All', 'Winners', 'Losers'], horizontal=True)
    t = t[t.year.isin(yrs)]
    t = t[t.ret > 0] if side == 'Winners' else t[t.ret <= 0] if side == 'Losers' else t
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Trades shown', len(t)); m2.metric('Win rate', ui.pct((t.ret > 0).mean()) if len(t) else 'n/a')
    m3.metric('Average trade', ui.pct(t.ret.mean(), 3) if len(t) else 'n/a'); m4.metric('Best / worst', '%s / %s' % (ui.pct(t.ret.max()), ui.pct(t.ret.min())) if len(t) else 'n/a')
    st.dataframe(t.sort_values('entry', ascending=False).style.format({'ret': '{:.3%}'}), hide_index=True, width='stretch', height=380)
    st.download_button('Download trades (CSV)', t.to_csv(index=False), 'task1_trades.csv', 'text/csv')
    st.caption('Per-trade return excludes carry and roll; the equity curve includes them.')

with tab_cmp:
    rows = []
    for k in E1.APPROACHES:
        p = E1.default_params(k)
        rr = E1.run(k, E1.pj(p), s['delay'], s['cost'], s['start'], s['end'])['stats']
        rows.append({'Approach': E1.APPROACHES[k], 'Params': str(p), 'Sharpe': rr['sharpe'], 'Max DD': rr['max_dd'], 'CAGR': rr['cagr'], 'Trades': rr['trades'], 'In market': rr['time_in_market']})
    st.caption('Default parameters of each approach; delay, cost and date range from the sidebar.')
    st.dataframe(pd.DataFrame(rows).style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.1%}', 'CAGR': '{:.1%}', 'In market': '{:.1%}'}), hide_index=True, width='stretch')
    st.caption('A: pure overnight gap. B: daily trend, long/flat. C: submitted.')
