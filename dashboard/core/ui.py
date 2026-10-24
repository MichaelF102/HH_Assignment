"""Sidebar controls and shared widgets. Settings live in st.session_state['store'] / ['scn'] (not in widget keys),
because Streamlit drops widget state for widgets that are not rendered on the current page."""
import datetime as dt

import pandas as pd
import streamlit as st

from . import loaders as L, t1_engine as E1, t2_engine as E2

H = L.H
T1_TESTED = {'sma': (50, 200), 'p': (1, 3), 'q': (1, 3), 'mom': (-0.002, 0.002)}
T2_TESTED = {'n': (8, 12), 'lb': (84, 168), 'rebal': (10, 30), 'sma': (40, 70), 'volq': (0.6, 1.0)}
T1_RANGE = (dt.date(2017, 4, 3), dt.date(2022, 1, 31))
T2_RANGE = (dt.date(2022, 3, 2), dt.date(2024, 6, 28))


def page_setup(title, icon=None):
    st.set_page_config(page_title='%s | Quant take-home' % title, page_icon=icon, layout='wide')
    st.session_state.setdefault('mode', 'Submitted')
    st.session_state.setdefault('store', {})
    st.session_state.setdefault('scn', {})
    global_sidebar()
    st.title(title)


def _reset():
    for k in [k for k in st.session_state if k.startswith('w_')]:
        del st.session_state[k]
    st.session_state['store'] = {}
    st.session_state['mode'] = 'Submitted'


def global_sidebar():
    with st.sidebar:
        st.markdown('### Strategy parameters')
        st.radio('Source', ['Submitted', 'Custom'], key='mode', horizontal=True,
                 help='Submitted: parameters locked to task1.py / task2.py. Custom: sliders unlocked.')
        st.button('Reset to submitted', on_click=_reset, width='stretch')
        st.divider()


# ------------------------------------------------------------------ persistence helpers
def locked():
    return st.session_state['mode'] == 'Submitted'


def _param_widget(name, label, default, lo, hi, step, tested=None, scale=1.0, fmt=None, is_int=True):
    """Slider for a strategy parameter. Locked (shows the submitted value) in Submitted mode."""
    store, key = st.session_state['store'], 'w_' + name
    if locked():
        st.session_state[key] = default * scale
    elif key not in st.session_state:
        st.session_state[key] = store.get(name, default) * scale
    help_ = ('Tested range: %s to %s' % (tested[0] * scale, tested[1] * scale)) if tested else None
    v = st.slider(label, lo, hi, step=step, key=key, disabled=locked(), help=help_, format=fmt)
    v = v / scale
    if not locked():
        store[name] = int(round(v)) if is_int else v
    if tested and not locked() and not (tested[0] - 1e-12 <= v <= tested[1] + 1e-12):
        st.caption(':orange[outside tested range]')
    return int(round(v)) if is_int else v


def _free_widget(kind, name, label, default, **kw):
    scn, key = st.session_state['scn'], 'w_' + name
    if key not in st.session_state:
        st.session_state[key] = scn.get(name, default)
    v = getattr(st, kind)(label, key=key, **kw)
    scn[name] = v
    return v


def _read(name, default, params=True):
    if params:
        return default if locked() else st.session_state['store'].get(name, default)
    return st.session_state['scn'].get(name, default)


# ------------------------------------------------------------------ Task 1
def t1_state():
    """Current Task 1 configuration (works on any page, whether or not the widgets are rendered)."""
    appr = _read('approach', 'C', params=False)
    base = E1.default_params(appr)
    params = {k: _read('t1_%s_%s' % (appr, k), v) for k, v in base.items()} if not locked() else dict(base)
    rng = _read('t1_range', T1_RANGE, params=False)
    return dict(approach=appr, params=params, delay=_read('delay', 0, False), cost=_read('cost_mult', 1, False),
                start=str(rng[0]), end=str(rng[1]), pj=E1.pj(params))


def t1_controls(show_scenario=True, allow_approach=True):
    with st.sidebar:
        st.markdown('### Task 1 setup')
        if allow_approach:
            appr = _free_widget('selectbox', 'approach', 'Approach', 'C', options=list(E1.APPROACHES), format_func=E1.APPROACHES.get)
        else:
            appr = 'C'
        d = E1.default_params(appr)
        # parameter widgets keep their own store entries per approach
        def pw(name, *a, **k):
            return _t1_param(appr, name, d[name], *a, **k)
        if appr == 'C':
            pw('sma', 'sma: trend length (days)', 20, 250, 5, tested=T1_TESTED['sma'])
            pw('p', 'p: extra bars before the last bar', 0, 4, 1, tested=T1_TESTED['p'])
            pw('q', 'q: morning bars still held', 1, 4, 1, tested=T1_TESTED['q'])
            pw('mom', 'mom: min return on the day (%)', -0.5, 0.5, 0.05, tested=T1_TESTED['mom'], scale=100.0, fmt='%.2f', is_int=False)
        elif appr == 'A':
            pw('sma', 'sma: trend length (days)', 20, 250, 5)
        else:
            pw('sma', 'sma: trend length (days)', 20, 250, 5)
            pw('vol', 'vol: 20d volatility cap', 0.10, 0.60, 0.05, is_int=False, fmt='%.2f')
        if show_scenario:
            st.markdown('### Scenario')
            _free_widget('slider', 'delay', 'Extra fill delay (bars)', 0, min_value=0, max_value=3, step=1)
            _free_widget('select_slider', 'cost_mult', 'Cost multiplier', 1, options=[0, 1, 2, 3, 4, 6])
            _free_widget('slider', 't1_range', 'Date range', T1_RANGE, min_value=T1_RANGE[0], max_value=T1_RANGE[1], format='YYYY-MM-DD')
    return t1_state()


def _t1_param(appr, name, default, label, lo, hi, step, **kw):
    return _param_widget('t1_%s_%s' % (appr, name), label, default, lo, hi, step, **kw)


# ------------------------------------------------------------------ Task 2
def t2_params():
    base = L.submitted_params(2)
    return dict(base) if locked() else {k: _read('t2_' + k, v) for k, v in base.items()}


def t2_state():
    p = t2_params()
    rng = _read('t2_range', T2_RANGE, params=False)
    cost = _read('t2_cost', H.T2_COST * 100, params=False) / 100
    return dict(params=p, pj=E2.params_json(p), cost=round(cost, 6), start=str(rng[0]), end=str(rng[1]))


def t2_controls(with_run=False):
    d = L.submitted_params(2)
    with st.sidebar:
        st.markdown('### Task 2 setup')
        _param_widget('t2_n', 'n: positions', d['n'], 5, 15, 1, tested=T2_TESTED['n'])
        _param_widget('t2_lb', 'lb: momentum lookback (days)', d['lb'], 40, 252, 6, tested=T2_TESTED['lb'])
        _param_widget('t2_rebal', 'rebal: days between rebalances', d['rebal'], 5, 42, 1, tested=T2_TESTED['rebal'])
        _param_widget('t2_sma', 'sma: per-stock trend filter (days)', d['sma'], 20, 100, 5, tested=T2_TESTED['sma'])
        _param_widget('t2_volq', 'volq: volatility cap (quantile kept)', d['volq'], 0.40, 1.0, 0.05, tested=T2_TESTED['volq'], is_int=False, fmt='%.2f')
        st.markdown('### Scenario')
        _free_widget('slider', 't2_cost', 'Cost per side (%)', H.T2_COST * 100, min_value=0.0, max_value=0.8, step=0.05, format='%.2f')
        _free_widget('slider', 't2_range', 'Display range', T2_RANGE, min_value=T2_RANGE[0], max_value=T2_RANGE[1], format='YYYY-MM-DD')
        if with_run:
            s = t2_state()
            if st.button('Run backtest', type='primary', width='stretch',
                         help='The submitted configuration is precomputed.'):
                with st.spinner('Running the harness backtest...'):
                    res = E2.run(s['pj'], s['cost'])
                st.session_state['t2_last'] = dict(res=res, key=(s['pj'], s['cost']))
    return t2_state()


def t2_current():
    """(result, stale). stale=True when the settings differ from the result shown (press Run)."""
    s = t2_state()
    key = (s['pj'], s['cost'])
    sub_key = (E2.params_json(L.submitted_params(2)), round(H.T2_COST, 6))
    if key == sub_key:
        return E2.base_result(), False
    last = st.session_state.get('t2_last')
    if last and last['key'] == key:
        return last['res'], False
    return (last['res'] if last else E2.base_result()), True


# ------------------------------------------------------------------ small display helpers
def pct(x, d=1):
    return '%.*f%%' % (d, 100 * x)


def badge(ok):
    return ':green[met]' if ok else ':red[not met]'


def stat_row(s, rf_label):
    c = st.columns(6)
    c[0].metric('Sharpe', '%.2f' % s['sharpe'], help='Daily returns, annualised, in excess of %s' % rf_label)
    c[1].metric('Max drawdown', pct(s['max_dd']))
    c[2].metric('CAGR', pct(s['cagr']))
    c[3].metric('Trades', '%d' % s['trades'])
    c[4].metric('Win rate', pct(s['win_rate'], 0) if s['trades'] else 'n/a')
    c[5].metric('Time in market', pct(s['time_in_market'], 0))


def scope_note():
    st.info('In-sample, visible data only; hidden windows are not shown. Task 2 universe is survivor-biased. See Benchmarks.')


def stale_banner(stale):
    if stale:
        st.warning('Settings changed since the last run. Showing the previous result; press Run backtest on the Task 2 Strategy page.')
