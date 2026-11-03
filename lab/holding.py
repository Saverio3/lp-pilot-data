"""How long LPs stay: deposits starting at the beginning of every month, held 30, 90 or 365 days.
Usage: python lab/holding.py ETHUSDT [BTCUSDT]  -> results/holding_out/<PAIR>.csv"""
import sys, os, glob
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lab')); sys.path.insert(0, os.path.join(ROOT, 'lab', 'methods'))
from engine import sim
from _tools import lowpass_price
DATA = os.path.join(ROOT, 'data')
A = sys.argv[1]; B = sys.argv[2] if len(sys.argv) > 2 else None
PAIR = A.replace('USDT', '') + '_' + (B.replace('USDT', '') if B else 'USD')
def load(s):
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f'{DATA}/{s}_1m_*.parquet'))]); return d.drop_duplicates('t').set_index('t').sort_index()
def funding(s, idx):
    f = pd.read_parquet(f'{DATA}/{s}_funding.parquet'); pos = np.searchsorted(idx, f.t.values)
    arr = np.zeros(len(idx)); ok = pos < len(idx); np.add.at(arr, pos[ok], f.rate.values[ok]); return arr
a = load(A)
if B:
    b = load(B); j = a.join(b, lsuffix='_a', rsuffix='_b', how='inner'); px = pd.DataFrame({'close': j.close_a / j.close_b, 'qv': j.qv_a}, index=j.index)
else:
    px = a[['close', 'qv']]
px = px[px.close > 0]; fr = funding(A, px.index.values) - (funding(B, px.index.values) if B else 0)
p = px.close.values.astype(float); qv = px.qv.values.astype(float); t = pd.to_datetime(px.index.values, unit='ms')
r = np.r_[0.0, np.diff(np.log(p))]; rv60 = pd.Series(r ** 2).rolling(60).mean().shift(1).bfill().values
starts = np.searchsorted(px.index.values, pd.date_range(t[0].normalize(), t[-1], freq='MS').as_unit('ms').asi8)
starts = np.unique(starts)
rows = []
for s0 in starts:
    for H in [30, 90, 365]:
        e = s0 + H * 1440
        if e > len(p): continue
        P = p[s0:e]; v = np.sqrt(rv60[s0:e]); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03)
        ret = qv[s0:e] / max(qv[s0:e].sum(), 1) * 0.10 * 10e6 * H
        past = r[max(0, s0 - 525600):s0]; pv = np.std(past) * np.sqrt(525600) if len(past) > 200000 else np.nan
        shield = dict(base=vf, gamma=1.0, hedge=1, Hp=lowpass_price(P, 10080), band=0.30)
        D = {'Uniswap 0.30%': dict(base=0.003), 'Earn (fee only)': dict(base=vf, gamma=1.0),
             'Shield band 5%': dict(base=vf, gamma=1.0, hedge=1, Hp=lowpass_price(P, 1440), band=0.05),
             'Band 30% + 7d': shield,
             'Per-pair rule (365d vol < 50% -> Earn)': (dict(base=vf, gamma=1.0) if (not np.isnan(pv) and pv < 0.5) else shield),
             'FLAT Earn (0.30% + size fee)': dict(base=0.003, gamma=1.0),
             'FLAT Band 30% + 7d': dict(base=0.003, gamma=1.0, hedge=1, Hp=lowpass_price(P, 10080), band=0.30),
             'FLAT Per-pair rule': (dict(base=0.003, gamma=1.0) if (not np.isnan(pv) and pv < 0.5) else dict(base=0.003, gamma=1.0, hedge=1, Hp=lowpass_price(P, 10080), band=0.30))}
        for dn, kw in D.items():
            o = sim(P, fund=fr[s0:e], retail=ret, **kw)
            rows.append(dict(pair=PAIR, start=str(t[s0].date()), days=H, design=dn, final=o[0], worst=o[1], final_r1=o[5], final_r2=o[7]))
    print(PAIR, t[s0].date(), flush=True)
os.makedirs(os.path.join(ROOT, 'results', 'holding_out'), exist_ok=True)
pd.DataFrame(rows).to_csv(os.path.join(ROOT, 'results', 'holding_out', f'{PAIR}.csv'), index=False)
