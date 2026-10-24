import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import streamlit as st

from core import charts, loaders as L, ui

ui.page_setup('Benchmarks and Stress')
RZ = L.text_file('research/realism.json') and __import__('json').loads(L.text_file('research/realism.json'))
if not RZ:
    st.error('research/realism.json not found.')
    st.stop()
t2, t1, V = RZ['t2'], RZ['t1'], RZ['t2_variants']

st.caption('In-sample, visible data.')

st.subheader('Task 2: how much of the Sharpe is the stock list?')
rows = [('Submitted strategy (0.2% per side)', t2['strategy']['sharpe'], t2['strategy']['cagr'], t2['strategy']['dd']),
        ('Equal-weight of all liquid stocks in the file (daily rebalanced, no costs)', t2['equal_weight']['sharpe'], t2['equal_weight']['cagr'], t2['equal_weight']['dd']),
        ('10 random liquid stocks, rebalanced every 21 days, same costs (12 seeds, mean)', t2['random']['sharpe_mean'], t2['random']['cagr_mean'], t2['random']['dd_worst']),
        ('Nifty 50', t2['nifty']['sharpe'], t2['nifty']['cagr'], t2['nifty']['dd'])]
df = pd.DataFrame(rows, columns=['Portfolio', 'Sharpe', 'CAGR', 'Max DD'])
c1, c2 = st.columns([3, 2])
c1.dataframe(df.style.format({'Sharpe': '{:.2f}', 'CAGR': '{:.0%}', 'Max DD': '{:.0%}'}), hide_index=True, width='stretch')
c2.plotly_chart(charts.bars(['Strategy', 'Equal-weight', 'Random 10', 'Nifty'], list(df.Sharpe), 'Sharpe by portfolio', height=240, fmt='.2f'), width='stretch')
st.caption('Equal-weight basket of the same stocks: Sharpe %.2f. Random 10-stock books: %.1f. Strategy vs basket: information ratio %.2f, alpha %.0f%% a year, beta %.2f.' % (t2['equal_weight']['sharpe'], t2['random']['sharpe_mean'], t2['info_ratio'], 100 * t2['alpha_ann'], t2['beta']))

st.subheader('Task 2: variants tried, judged against the basket')
st.caption('Adoption rule set in advance: stripped-universe Sharpe (0.4%/side) up 0.10 or more, 2022 Sharpe down no more than 0.2, full-window Sharpe at least 1.5. About 90 configurations (about 200 harness runs) scored on this window.')
names = {'base': 'First version: breadth brake, 10 cr floor', 'liq25': 'Liquidity floor Rs 25 cr', 'invvol': 'Inverse-volatility sizing', 'liq25+invvol': 'Floor 25 cr + inverse-vol',
         'volcap90': 'Exclude top 10% volatile', 'volcap75': 'Top-25% cap + breadth brake', 'volcap75+invvol': 'Top-25% cap + brake + inverse-vol',
         'volcap75_nosma': 'Top-25% cap, no trend filter', 'volcap75_nobreadth': 'SUBMITTED: top-25% cap, no breadth brake'}
rows = []
for k, n in names.items():
    r = V[k]
    rows.append({'Variant': n, 'Sharpe': r['full']['sharpe'], 'Max DD': r['full']['dd'], 'Info ratio vs basket': r['full']['ir'], 'Excess CAGR': r['full']['excess_cagr'],
                 'Sharpe at 0.4%': r['cost4']['sharpe'], '2022 Sharpe': r['w2022']['sharpe'], 'Stripped universe (0.4%)': r['stripped']['sharpe']})
st.dataframe(pd.DataFrame(rows).style.format({'Sharpe': '{:.2f}', 'Max DD': '{:.0%}', 'Info ratio vs basket': '{:.2f}', 'Excess CAGR': '{:+.0%}', 'Sharpe at 0.4%': '{:.2f}', '2022 Sharpe': '{:.2f}', 'Stripped universe (0.4%)': '{:.2f}'}),
             hide_index=True, width='stretch')
st.caption('Rs 25 cr liquidity floor (unrestricted version): almost no edge over the basket left.')

st.subheader('Task 2: dependence on the rebalance calendar')
AUD = L.text_file('research/audit/p1_results.json') and __import__('json').loads(L.text_file('research/audit/p1_results.json'))
if AUD and 'phase_baseline' in AUD:
    ph = AUD['phase_baseline']
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(charts.bars(['offset %d' % o for o in ph['offsets']], ph['sharpe'], 'Sharpe by rebalance start offset (0 = submitted)', height=260, fmt='.2f'), width='stretch')
    c2.metric('Mean / median Sharpe across 21 offsets', '%.2f / %.2f' % (ph['mean'], ph['median']))
    c2.metric('Range', '%.2f to %.2f' % (ph['min'], ph['max']))
    c2.metric('Rank of the submitted offset', '%d of 21' % ph['submitted_rank'])
    stg = AUD['E-T2-3']
    st.caption('Staggered tranches, research only: Sharpe %.2f to %.2f, mean %.2f at 0.2%% per side; range %.2f against the 0.30 rule. Not adopted.' % (stg['c02']['min'], stg['c02']['max'], stg['c02']['mean'], stg['c02']['range']))
    with st.expander('Other pre-registered experiments (research/audit/p1_results.json)'):
        rows = [{'Experiment': k, 'Rule (fixed before running)': v['rule'], 'Passed': 'yes' if v['passed'] else 'NO'} for k, v in AUD.items() if isinstance(v, dict) and 'rule' in v]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')

st.subheader('Task 1: execution stress')
sc = t1['scenarios']
d1 = pd.DataFrame([(k, v['sharpe'], v['cagr'], v['dd']) for k, v in sc.items()], columns=['Scenario', 'Sharpe', 'CAGR', 'Max DD'])
c1, c2 = st.columns([3, 2])
c1.dataframe(d1.style.format({'Sharpe': '{:.2f}', 'CAGR': '{:.0%}', 'Max DD': '{:.1%}'}), hide_index=True, width='stretch')
g = t1['grid54']
c2.metric('Median Sharpe of 54 nearby settings (delay 1 + 2x costs)', '%.2f' % g['real_median'])
c2.metric('Share of those above 1.0', '%.0f%%' % (100 * g['share_real_gt1']))
c2.metric('Median in the harsh case (delay 2 + 3x costs)', '%.2f' % g['harsh_median'])
dc = t1['decomposition']
st.caption('Gap +%.1f bp a night vs about 5 bp round-trip cost. Costs take %.0f%% and carry %.0f%% of gross profit; 2020 is %.0f%% of total P&L. Futures executability untested.' % (dc['gap_bp'], -100 * dc['costs'], -100 * dc['carry'], 100 * dc['year_2020_share']))

st.subheader('Working ranges')
st.markdown("""
| | In-sample | Working range | Basis |
|---|---|---|---|
| Task 1 Sharpe | 2.17 | about 1.0 to 1.5 | delay 1 + 2x costs; median of nearby settings |
| Task 2 Sharpe | 2.10 | about 0.8 to 1.6 | basket 2.09, random 1.5, best 15% removed 1.25 to 1.40 |
""")
