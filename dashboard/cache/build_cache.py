"""Precompute the submitted Task 2 backtest so the dashboard opens instantly: python dashboard/cache/build_cache.py"""
import hashlib
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import harness_public as H  # noqa: E402

root = os.path.dirname(os.path.dirname(HERE))
m = H.load_module(os.path.join(root, 'task2.py'))
D = H.load_stocks([os.path.join(H.DATA, 'stocks_daily_train_2021-04-26_2024-06-30.csv')], [os.path.join(H.DATA, 'nifty50_daily_2021-04-26_2024-06-30.csv')])
res = H.task2_backtest(m, D, dict(m.PARAMS), H.T2_START, H.T2_END)
stats, eq = H.task2_stats(res)
with open(os.path.join(HERE, 't2_base.pkl'), 'wb') as f:
    pickle.dump(dict(stats=stats, eq=eq, trades=res['trades'], gross=res['gross'], src_md5=hashlib.md5(open(os.path.join(root, 'task2.py'), 'rb').read()).hexdigest()), f)
print('saved', stats['sharpe'], stats['trades'])
