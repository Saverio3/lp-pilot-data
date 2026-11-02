"""Run every method file in lab/methods on one pair, year by year (fresh deposit each year vs HODL).
Usage: python lab/run.py ETHUSDT [BTCUSDT]      (second symbol = quote coin for crypto/crypto pairs)
Env METHODS="gap_fee,ai_storm" limits which method files run (default: all).
Writes results/raw/<PAIR>.csv"""
import sys, os, glob, importlib.util, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lab'))
from engine import sim  # noqa: E402

DATA = os.path.join(ROOT, 'data')
A = sys.argv[1]; B = sys.argv[2] if len(sys.argv) > 2 else None
PAIR = A.replace('USDT', '') + '_' + (B.replace('USDT', '') if B else 'USD')


def load(s):
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f'{DATA}/{s}_1m_*.parquet'))])
    return d.drop_duplicates('t').set_index('t').sort_index()


def funding(s, idx):
    f = pd.read_parquet(f'{DATA}/{s}_funding.parquet')
    pos = np.searchsorted(idx, f.t.values)
    arr = np.zeros(len(idx)); ok = pos < len(idx)
    np.add.at(arr, pos[ok], f.rate.values[ok])
    return arr


a = load(A)
if B:
    b = load(B); j = a.join(b, lsuffix='_a', rsuffix='_b', how='inner')
    px = pd.DataFrame({'close': j.close_a / j.close_b, 'qv': j.qv_a}, index=j.index)
else:
    px = a[['close', 'qv']]
px = px[px.close > 0]
fr = funding(A, px.index.values) - (funding(B, px.index.values) if B else 0)
px = px.reset_index(); px['dt'] = pd.to_datetime(px.t, unit='ms', utc=True)
yr = px.dt.dt.year
p = px.close.values.astype(np.float64)
r = np.r_[0, np.diff(np.log(p))]; R = pd.Series(r); V = px.qv.astype(float)

# AI storm score: gradient boosting on past-only features, leave-one-year-out
F = pd.DataFrame(index=px.index)
for w in [1, 3, 5, 15, 60, 240, 1440]: F[f'vol{w}'] = np.log(R.pow(2).rolling(w).mean() + 1e-12).shift(1)
for w in [1, 5, 15, 60]: F[f'vrel{w}'] = np.log((V.rolling(w).mean() + 1) / (V.rolling(1440).mean() + 1)).shift(1)
for w in [5, 15, 60]: F[f'mom{w}'] = R.rolling(w).sum().abs().shift(1)
F['hour'] = px.dt.dt.hour; F['dow'] = px.dt.dt.dayofweek; F['minute'] = px.dt.dt.minute; F['volratio'] = F.vol5 - F.vol240
ok = F.notna().all(axis=1); r2 = pd.Series(r ** 2); score = pd.Series(0.0, index=px.index)
for y in sorted(yr.unique()):
    tr = ok & (yr != y); te = ok & (yr == y)
    if te.sum() < 10000: continue
    sub = tr[tr].index[::3]
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=63)
    clf.fit(F.loc[sub], (r2[sub] > r2[tr].quantile(0.9)).astype(int))
    score[te[te].index] = clf.predict_proba(F[te])[:, 1]
rv60 = R.pow(2).rolling(60).mean().shift(1).bfill().values  # past-only realised variance, 1h

# load method files
want = [m for m in os.environ.get('METHODS', '').split(',') if m]
mods = []
for f in sorted(glob.glob(os.path.join(ROOT, 'lab', 'methods', '*.py'))):
    nm = os.path.basename(f)[:-3]
    if nm.startswith('_') or (want and nm not in want): continue
    spec = importlib.util.spec_from_file_location(nm, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    mods.append((nm, m))

rows = []
for y in sorted(yr.unique()):
    msk = (yr == y).values
    if msk.sum() < 20000: continue
    P = p[msk]
    ctx = dict(P=P, n=len(P), fund=fr[msk], score=score.values[msk], rv60=rv60[msk],
               stale=np.r_[P[0], P[:-1]], pair=PAIR, year=int(y))
    for nm, m in mods:
        for dn, kw in m.designs(ctx):
            t0 = time.time()
            fin, worst, fund = sim(P, fund=ctx['fund'], **kw)
            rows.append(dict(pair=PAIR, year=int(y), method=nm, design=dn, final=fin, worst=worst,
                             funding=fund, move=P[-1] / P[0] - 1, secs=round(time.time() - t0, 2)))
    print(PAIR, y, 'done', flush=True)
os.makedirs(os.path.join(ROOT, 'results', 'raw'), exist_ok=True)
out = pd.DataFrame(rows); path = os.path.join(ROOT, 'results', 'raw', f'{PAIR}.csv')
if os.path.exists(path):  # keep earlier results of method files not re-run this time
    old = pd.read_csv(path); out = pd.concat([old[~old.method.isin(out.method.unique())], out])
out.to_csv(path, index=False)
os.makedirs(os.path.join(ROOT, 'results', 'out'), exist_ok=True)
out.to_csv(os.path.join(ROOT, 'results', 'out', f'{PAIR}.csv'), index=False)  # only this pair, for upload
