import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os

import pandas as pd
import streamlit as st

from core import loaders as L, ui

ui.page_setup('Notes')
tab_fail, tab_surv, tab_break, tab_rep = st.tabs(['Failed ideas', 'Survivorship note', 'What would break each strategy', 'Report'])


def parse_tables(md):
    rows, task = [], None
    for line in md.splitlines():
        if line.startswith('## '):
            task = 'Task 1' if 'Task 1' in line else 'Task 2' if 'Task 2' in line else None
        elif line.startswith('|') and task and not line.startswith('|---') and not line.startswith('| #'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 4:
                rows.append({'Task': task, '#': cells[0], 'Idea': cells[1], 'Result': cells[2], 'Why it failed': ' '.join(cells[3:])})
    return pd.DataFrame(rows)


with tab_fail:
    md = L.text_file('failed_ideas.md')
    if md:
        df = parse_tables(md)
        c1, c2 = st.columns([1, 2])
        t = c1.radio('Task', ['All', 'Task 1', 'Task 2'], horizontal=True)
        q = c2.text_input('Search ideas, numbers, reasons')
        if t != 'All':
            df = df[df.Task == t]
        if q:
            df = df[df.apply(lambda r: q.lower() in ' '.join(r.astype(str)).lower(), axis=1)]
        st.caption('%d ideas. Harness numbers, visible data.' % len(df))
        st.dataframe(df, hide_index=True, width='stretch', column_config={'Why it failed': st.column_config.TextColumn(width='large'), 'Result': st.column_config.TextColumn(width='medium')})
    else:
        st.error('failed_ideas.md not found.')

with tab_surv:
    md = L.text_file('survivorship_note.md')
    st.markdown(md if md else 'survivorship_note.md not found.')

with tab_break:
    st.markdown("""
**Task 1**
- Overnight premium disappears or reverses.
- Futures open differently from the spot-index gap used by the harness.
- Costs: Sharpe 0.25 at 3x, -0.74 at 4x.
- Special sessions with unusual bar times can trigger an unintended 1-bar trade.

**Task 2**
- Momentum crash: no market-level brake, and the sample has no long bear market.
- Volatility cap is a peak (volq 0.60: Sharpe 1.5 to 1.7; 0.90: 1.7 to 2.1).
- Sideways market with repeated leader reversals at 0.4% round trip.
- Liquidity worse than the Rs 10 cr floor implies.
- Data jumps outside the guard (it checks one-day drops over 40% only).
- Rebalance calendar: Sharpe 1.26 to 2.33 across start offsets.
""")

with tab_rep:
    p = os.path.join(L.ROOT, 'report.pdf')
    if os.path.exists(p):
        st.download_button('Download report.pdf', open(p, 'rb').read(), 'report.pdf', 'application/pdf')
        st.caption('3 pages.')
    else:
        st.info('report.pdf not found.')
