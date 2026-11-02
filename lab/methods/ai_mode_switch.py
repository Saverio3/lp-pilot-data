"""AI mode switcher: every window (7 or 30 days) choose EARN (fee only, no hedge) or SHIELD (fee + low-pass hedge).
Same oracle-free fee in both modes (trade-size g=1 + volatility fee). The classifier learns, from OTHER years only,
which mode wins the next window given what is known at its start (volatility, trend, persistence, funding, last winner).
Also: perfect-hindsight switch (impossible upper bound) and a simple 'last window's winner' rule."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from engine import sim
from _tools import lowpass_price

_cache = {}


def _fee(P):
    r = np.r_[0.0, np.diff(np.log(P))]
    rv = pd.Series(r ** 2).rolling(60).mean().shift(1).bfill().values
    v = np.sqrt(rv); return np.clip(0.003 * v / np.median(v), 0.003, 0.03)


def _windows(c, W):
    key = (c['pair'], W)
    if key in _cache: return _cache[key]
    P, F, Y = c['P_all'], c['fund_all'], c['yr_all']
    lp = pd.Series(np.log(P)); r = lp.diff().fillna(0)
    vol7 = r.rolling(10080, min_periods=1440).std().shift(1) * np.sqrt(525600)
    vol30 = r.rolling(43200, min_periods=1440).std().shift(1) * np.sqrt(525600)
    m7 = lp.diff(10080).abs().shift(1); m30 = lp.diff(43200).abs().shift(1)
    rs = lp.diff(60); rl = lp.diff(1440)
    vr = (rl.pow(2).rolling(43200, min_periods=4320).mean() / (24 * rs.pow(2).rolling(43200, min_periods=4320).mean())).shift(1)
    fu = pd.Series(F).rolling(43200, min_periods=1).sum().shift(1)
    rows = []
    for y in np.unique(Y):
        idx = np.where(Y == y)[0]
        if len(idx) < 20000: continue
        s0, e0 = idx[0], idx[-1] + 1
        Py = P[s0:e0]; fee_y = _fee(Py)
        for k in range(0, len(Py), W):
            a, b = k, min(k + W, len(Py))
            if b - a < W // 2: break
            seg = Py[a:b]; fe = fee_y[a:b]; fd = F[s0 + a:s0 + b]
            earn = sim(seg, fund=fd, base=fe, gamma=1.0)[0]
            shield = sim(seg, fund=fd, base=fe, gamma=1.0, hedge=1, Hp=lowpass_price(seg, 1440), band=0.05)[0]
            g = s0 + a
            rows.append(dict(year=y, a=a, b=b, vol7=vol7.iloc[g], vol30=vol30.iloc[g], m7=m7.iloc[g], m30=m30.iloc[g],
                             vr=vr.iloc[g], fund=fu.iloc[g], label=int(shield > earn), edge=shield - earn))
    w = pd.DataFrame(rows)
    w['prev'] = w.groupby('year').label.shift(1).fillna(0.5)
    w['prev_edge'] = w.groupby('year').edge.shift(1).fillna(0.0)
    _cache[key] = w
    return w


def designs(c):
    P = c['P']; n = len(P); Hp = lowpass_price(P, 1440); fee = _fee(P)
    out = []
    for W, nm in [(10080, '7-day'), (43200, '30-day')]:
        w = _windows(c, W)
        feats = ['vol7', 'vol30', 'm7', 'm30', 'vr', 'fund', 'prev', 'prev_edge']
        tr = w[w.year != c['year']].dropna(subset=['vol7']); te = w[w.year == c['year']]
        X = te[feats].fillna(te[feats].median())
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3)
        clf.fit(tr[feats].fillna(tr[feats].median()), tr.label)
        prob = clf.predict_proba(X)[:, 1]
        def arr(vals):
            ra = np.ones(n)
            for (a, b), v in zip(te[['a', 'b']].values, vals): ra[a:b] = v
            if len(te): ra[te.b.values[-1]:] = vals[-1]
            return ra
        kw = dict(base=fee, gamma=1.0, hedge=1, Hp=Hp, band=0.05)
        out.append((f'AI mode switch ({nm})', dict(kw, ratio=arr((prob > 0.5).astype(float)))))
        out.append((f'AI mode switch, probability-weighted ({nm})', dict(kw, ratio=arr(prob))))
        out.append((f'Rule: last window winner ({nm})', dict(kw, ratio=arr(te.prev.values.round()))))
        out.append((f'Perfect hindsight switch ({nm}) - impossible upper bound', dict(kw, ratio=arr(te.label.values.astype(float)))))
    return out
