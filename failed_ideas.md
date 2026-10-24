# Failed ideas

Harness numbers on the visible data. Task 1: Apr 2017 to Jan 2022, Sharpe over 6% cash. Task 2: 2 Mar 2022 to 28 Jun 2024, 0.2% per side.
Baselines: Task 1 buy-and-hold Sharpe 0.53, DD -38.3%; MA(50/200) Sharpe 0.54, DD -18.6%. Task 2 template Sharpe 1.64, DD -22.2%.

## Task 1

| # | Idea | Result | Why it failed |
|---|---|---|---|
| 1 | Daily SMA(n) long/short | n=50: Sharpe 0.41, DD -25.5%; n=100: 0.10, -27.1%; n=200: -0.12, -32.3% | Short leg loses in the 2017-21 uptrend; long/flat n=50 scored 0.83. |
| 2 | Daily trend long/flat family (SMA, momentum, Donchian, volatility and drawdown filters) | Best Sharpe 0.86 (SMA50, 20-day vol < 35%), DD -12.5%; others 0.03-0.83 | Earns mainly in 2020; 2019 Sharpe 0.18, 2021 0.03. |
| 3 | RSI(2-5) pullback buys in an uptrend | Sharpe -0.26 to 0.31, 10-23% in market | Too few trades and a small average gain. |
| 4 | Pure overnight gap: last bar plus gap, SMA100 filter | Sharpe 3.01, DD -6.5%; -4.86 at 1-bar delay, -4.43 at 2-bar | The edge sits on one bar boundary; any delay loses it. |
| 5 | Kill-switch on the last W qualifying nights | Sharpe 1.80 (W=20), 2.04 (40), 2.14 (60), 2.17 (100); base 2.17 | Lowers return; no gain shown. |
| 6 | Volatility cap on the overnight filter (20-day vol < 15 / 20 / 30%) | Sharpe 1.23 / 2.23 / 2.17 | Best gain 0.06, within noise. |

## Task 2

| # | Idea | Result | Why it failed |
|---|---|---|---|
| 1 | Nifty above SMA100 / SMA50 as regime switch, else cash | SMA100: CAGR 29.0%, DD -24.6%, Sharpe 1.36; SMA50: 28.9%, -24.2%, 1.60 | Late exits and entries; cash earns 0%. |
| 2 | Breadth switch, breadth > 40% on 50-day averages | CAGR 28%, DD -21.8%, Sharpe 1.32 | Whipsaw around the threshold. |
| 3 | 12-1 month momentum (252-day lookback, skip 21) | CAGR 43.3%, DD -33.4%, Sharpe 1.56; 2022 -9% | Too slow for the window. |
| 4 | Volatility-normalised momentum | CAGR 57.4%, DD -22.8%, Sharpe 1.81 (raw 1.94) | Removes the high-volatility winners. |
| 5 | Weekly rebalance | Sharpe 1.70, 246 trades | Turnover cost. |
| 6 | Trailing stop 8-12% below the 20-day high | Sharpe 2.05-2.08, DD -20.7% to -23.6% (-19.6% without) | No risk-adjusted gain. |
| 7 | Breadth brake (100-day, 30%), first submitted version | Sharpe 2.04, DD -18.1%; best-15%-removed universe 0.31 (0.4% per side); 2022 Sharpe 1.21 | Replaced by the volatility cap (rows 10-12); uses two parameters. |
| 8 | Liquidity floor Rs 25 cr | Sharpe 1.34, DD -27%, excess CAGR over equal-weight basket -2% | Edge sits in the less liquid names. |
| 9 | Inverse-volatility sizing | Sharpe 1.98; best-15%-removed 0.37; 2022 1.08 | No robustness gain. |
| 10 | Exclude the top 10% most volatile names | Sharpe 1.76; 2022 0.44; best-15%-removed 0.71 | 2022 Sharpe fell by more than 0.2. |
| 11 | Top-25% volatility cap plus breadth brake | Sharpe 2.01, DD -15%; 2022 0.77 | Seven parameters; 2022 check failed. |
| 12 | Top-25% volatility cap without the trend filter | Sharpe 1.76, DD -19%, excess CAGR +2%; 2022 0.75 | The trend filter keeps the book above the basket. |

About 90 Task 2 configurations (about 200 harness runs) were scored on the visible window.
