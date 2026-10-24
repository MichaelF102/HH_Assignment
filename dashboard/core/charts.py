"""Plotly figure builders: one consistent style, colours distinguishable without relying on hue alone."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PRIMARY, GREY, ACCENT, NEG = '#2a6fdb', '#8a8f98', '#e08a1e', '#c0392b'
MARGIN = dict(l=10, r=10, t=40, b=10)


def _base(fig, title, height=340):
    fig.update_layout(title=dict(text=title, font=dict(size=14)), height=height, margin=MARGIN, hovermode='x unified',
                      legend=dict(orientation='h', y=1.12, x=0))
    return fig


def equity(series: dict, title, log=False, height=340):
    fig = go.Figure()
    styles = [(PRIMARY, 'solid'), (GREY, 'dot'), (ACCENT, 'dash'), (NEG, 'dashdot')]
    for (name, s), (col, dash) in zip(series.items(), styles):
        s = s / s.iloc[0]
        fig.add_scatter(x=s.index, y=s.values, name=name, line=dict(color=col, dash=dash, width=2 if dash == 'solid' else 1.4))
    fig.update_yaxes(type='log' if log else 'linear', title='growth of 1')
    return _base(fig, title, height)


def drawdown_chart(dd: dict, title='Drawdown', height=240):
    fig = go.Figure()
    for (name, s), col in zip(dd.items(), [PRIMARY, GREY, ACCENT]):
        fig.add_scatter(x=s.index, y=s.values, name=name, fill='tozeroy' if len(dd) == 1 else None, line=dict(color=col, width=1.4))
    fig.update_yaxes(tickformat='.0%')
    return _base(fig, title, height)


def bars(labels, values, title, height=260, fmt='.1%'):
    cols = [PRIMARY if v >= 0 else NEG for v in values]
    fig = go.Figure(go.Bar(x=list(labels), y=list(values), marker_color=cols, text=[format(v, fmt) for v in values], textposition='outside'))
    fig.update_yaxes(tickformat='.0%')
    fig.update_layout(hovermode='closest')
    return _base(fig, title, height)


def heatmap(z, xlabels, ylabels, xtitle, ytitle, title, fmt='.2f', pct=False, highlight=None, height=300, reverse=False):
    text = [[format(v, '.0%' if pct else fmt) for v in row] for row in z]
    fig = go.Figure(go.Heatmap(z=z, x=[str(x) for x in xlabels], y=[str(y) for y in ylabels], text=text, texttemplate='%{text}',
                               colorscale='Blues_r' if reverse else 'Blues', showscale=False, hovertemplate=f'{xtitle}=%{{x}}<br>{ytitle}=%{{y}}<br>%{{text}}<extra></extra>'))
    if highlight is not None:
        i, j = highlight
        fig.add_shape(type='rect', x0=j - .5, x1=j + .5, y0=i - .5, y1=i + .5, line=dict(color=ACCENT, width=3))
    fig.update_xaxes(title=xtitle, type='category')
    fig.update_yaxes(title=ytitle, type='category', autorange='reversed')
    fig.update_layout(hovermode='closest')
    return _base(fig, title, height)


def line(series: dict, title, yfmt=None, height=240, hline=None):
    fig = go.Figure()
    for (name, s), col in zip(series.items(), [PRIMARY, ACCENT, GREY]):
        fig.add_scatter(x=s.index, y=s.values, name=name, line=dict(color=col, width=1.6))
    if hline is not None:
        fig.add_hline(y=hline, line=dict(color=NEG, dash='dash', width=1))
    if yfmt:
        fig.update_yaxes(tickformat=yfmt)
    return _base(fig, title, height)


def intraday(bars_df, pos: pd.Series, title, height=420):
    """Candlesticks with the position shaded; entry/exit markers where the position changes."""
    fig = go.Figure(go.Candlestick(x=bars_df.index, open=bars_df.open, high=bars_df.high, low=bars_df.low, close=bars_df.close, name='Nifty 15m',
                                   increasing_line_color=PRIMARY, decreasing_line_color=GREY))
    p = pos.reindex(bars_df.index).fillna(0).values
    step = bars_df.index[1] - bars_df.index[0] if len(bars_df) > 1 else pd.Timedelta(minutes=15)
    i = 0
    while i < len(p):
        if p[i] != 0:
            j = i
            while j + 1 < len(p) and p[j + 1] == p[i]:
                j += 1
            fig.add_vrect(x0=bars_df.index[i], x1=bars_df.index[j] + step, fillcolor=ACCENT if p[i] > 0 else NEG, opacity=.18, line_width=0)
            fig.add_scatter(x=[bars_df.index[i]], y=[bars_df.open.iloc[i]], mode='markers', marker=dict(symbol='triangle-up', size=11, color='#1a8f4c'), name='entry', showlegend=False)
            if j + 1 < len(p):
                fig.add_scatter(x=[bars_df.index[j + 1]], y=[bars_df.open.iloc[j + 1]], mode='markers', marker=dict(symbol='triangle-down', size=11, color=NEG), name='exit', showlegend=False)
            i = j + 1
        else:
            i += 1
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(bounds=['sat', 'mon']), dict(bounds=[15.5, 9.25], pattern='hour')])
    fig.update_layout(hovermode='x unified')
    return _base(fig, title, height)


def price_with_trade(close: pd.Series, entry, exit_, title, height=300):
    fig = go.Figure()
    fig.add_scatter(x=close.index, y=close.values, line=dict(color=PRIMARY, width=1.6), name='close')
    fig.add_scatter(x=[entry], y=[close.get(entry, np.nan)], mode='markers', marker=dict(symbol='triangle-up', size=13, color='#1a8f4c'), name='entry')
    fig.add_scatter(x=[exit_], y=[close.get(exit_, np.nan)], mode='markers', marker=dict(symbol='triangle-down', size=13, color=NEG), name='exit')
    return _base(fig, title, height)


def scatter(x, y, text, title, xtitle, ytitle, height=340):
    fig = go.Figure(go.Scatter(x=x, y=y, mode='markers', text=text, marker=dict(size=8, color=PRIMARY, opacity=.7), hovertemplate='%{text}<br>%{x:.2f}, %{y:.2f}<extra></extra>'))
    fig.add_hline(y=0, line=dict(color=GREY, dash='dot'))
    fig.add_vline(x=0, line=dict(color=GREY, dash='dot'))
    fig.update_xaxes(title=xtitle)
    fig.update_yaxes(title=ytitle)
    fig.update_layout(hovermode='closest')
    return _base(fig, title, height)
