"""From your list (D16, reinforcement learning), simplest honest form: a contextual bandit. Each day it picks a hedge of
0%, 50% or 100% based on the market state (volatility level, trend strength, persistence). It learns, from OTHER years
only, which choice earned the most in each state; then acts on the unseen year. Same usable oracle-free fee throughout."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from engine import sim
from _tools import lowpass_price
_cache = {}
ACTS = [0.0, 0.5, 1.0]


def _fee(P):
    r = np.r_[0.0, np.diff(np.log(P))]
    v = np.sqrt(pd.Series(r ** 2).rolling(60).mean().shift(1).bfill().values); return np.clip(0.003 * v / np.median(v), 0.003, 0.03)


def _days(c):
    if c['pair'] in _cache: return _cache[c['pair']]
    P, F, Y = c['P_all'], c['fund_all'], c['yr_all']
    lp = pd.Series(np.log(P)); r = lp.diff().fillna(0)
    vol = r.rolling(10080, min_periods=1440).std().shift(1)
    trend = lp.diff(10080).abs().shift(1)
    rs = lp.diff(60); rl = lp.diff(1440)
    vr = (rl.pow(2).rolling(43200, min_periods=4320).mean() / (24 * rs.pow(2).rolling(43200, min_periods=4320).mean())).shift(1)
    rows = []
    for y in np.unique(Y):
        idx = np.where(Y == y)[0]
        if len(idx) < 20000: continue
        s0 = idx[0]; Py = P[idx]; fe = _fee(Py)
        for a in range(0, len(Py) - 1440, 1440):
            seg = Py[a:a + 1440]; g = s0 + a
            res = [sim(seg, fund=F[g:g + 1440], base=fe[a:a + 1440], gamma=1.0, hedge=1, ratio=act, band=0.05)[0] for act in ACTS]
            rows.append(dict(year=y, a=a, vol=vol.iloc[g], trend=trend.iloc[g], vr=vr.iloc[g], r0=res[0], r1=res[1], r2=res[2]))
    d = pd.DataFrame(rows); _cache[c['pair']] = d; return d


def designs(c):
    d = _days(c); tr = d[d.year != c['year']].dropna(); te = d[d.year == c['year']]
    qs = {f: np.nanquantile(tr[f], [1 / 3, 2 / 3]) for f in ['vol', 'trend', 'vr']}
    def state(df):
        return sum(np.digitize(df[f].fillna(np.nanmedian(tr[f])), qs[f]) * m for f, m in [('vol', 9), ('trend', 3), ('vr', 1)])
    tr = tr.assign(s=state(tr)); te = te.assign(s=state(te))
    best = tr.groupby('s')[['r0', 'r1', 'r2']].mean().idxmax(axis=1).map({'r0': 0.0, 'r1': 0.5, 'r2': 1.0})
    n = c['n']; ratio = np.full(n, 0.5)
    for a, s in te[['a', 's']].values: ratio[int(a):int(a) + 1440] = best.get(s, 0.5)
    P = c['P']; v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03)
    return [('RL bandit: daily hedge 0/50/100% by market state', dict(base=vf, gamma=1.0, hedge=1, ratio=ratio, band=0.05)),
            ('RL bandit + low-pass 1d', dict(base=vf, gamma=1.0, hedge=1, ratio=ratio, Hp=lowpass_price(P, 1440), band=0.05))]
