"""Cached loading of data, strategy modules and precomputed results. Imports the harness unchanged."""
import json
import os
import sys

import streamlit as st

DASH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(DASH)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import harness_public as H  # noqa: E402

DATA = H.DATA
T1_BARS_FILE = os.path.join(DATA, 'nifty50_15min_train_2017-04-03_2022-01-31.csv')
T1_EXP_FILE = os.path.join(DATA, 'nifty_monthly_expiries_2017-01_2022-01.csv')
T2_STOCK_FILE = os.path.join(DATA, 'stocks_daily_train_2021-04-26_2024-06-30.csv')
T2_NIFTY_FILE = os.path.join(DATA, 'nifty50_daily_2021-04-26_2024-06-30.csv')


@st.cache_resource(show_spinner='Loading Nifty 15-minute bars...')
def bars():
    return H.load_bars(T1_BARS_FILE)


@st.cache_resource
def expiries():
    return H.load_expiries(T1_EXP_FILE)


@st.cache_resource(show_spinner='Loading stock universe...')
def stocks():
    return H.load_stocks([T2_STOCK_FILE], [T2_NIFTY_FILE])


@st.cache_resource
def strategy(task: int):
    """The submitted strategy module, loaded from the project root, unmodified."""
    return H.load_module(os.path.join(ROOT, 'task%d.py' % task))


def submitted_params(task: int) -> dict:
    return dict(strategy(task).PARAMS)


def _json(name):
    p = os.path.join(ROOT, 'research', name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


@st.cache_data
def t1_results():
    return _json('t1_results.json')


@st.cache_data
def t2_results():
    return _json('t2_results.json')


@st.cache_data
def text_file(name):
    p = os.path.join(ROOT, name)
    return open(p, encoding='utf-8').read() if os.path.exists(p) else None
