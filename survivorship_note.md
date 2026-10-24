# Survivorship bias, Task 2 universe

The 555 stocks are those with a 60-day median traded value of at least Rs 10 crore in October 2026. Stocks liquid in 2022 that later fell, merged, were delisted or lost liquidity are missing, which flatters long-only strategies. The median stock gained 98% from 2 Mar 2022 to 28 Jun 2024 (Nifty +44.6%). An equal-weight basket of all 555 scores Sharpe 2.09; random 10-stock books score about 1.5.

| Test | Result | Limit |
|---|---|---|
| Best 15% of names by realised return removed | Strategy Sharpe 1.40 (0.2% per side) | Hindsight and one-sided: removing the worst 15% gives 2.20 |
| Random 30% of names removed (6 seeds) | Mean Sharpe 2.17 (min 1.94) | Does not remove delisted losers |
| 3% of trades replaced by a -60% outcome | Median Sharpe 1.46 | Not calibrated to real delisting rates |

None of these is a point-in-time estimate. Estimation: rebuild each rebalance date's liquidity universe from historical bhavcopy, including delisted names with delisting returns; run the same code on both universes; the difference in Sharpe and CAGR is the bias. Without that data, inject missing losers (2-4% of positions a year at -50%) for a first-order drag.

Hidden window: the universe is defined at its end, so names that left the liquid set during it are excluded. The look-ahead horizon is up to 2.3 years (4.6 for the visible window). The bias is smaller, not absent.
