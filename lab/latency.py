"""How much does a slow price feed cost the gap fee? Uses Binance 1-SECOND prices (downloaded inside GitHub).
Usage: python lab/latency.py ETHUSDT      Writes results/latency/<COIN>.csv
Arbitrage can act once per block (2s = L2 like Base/Unichain, 12s = Ethereum mainnet).
The fee logic sees the Binance price `lag` seconds old (oracle delay); the bot sees the current price."""
import sys, os, io, zipfile, urllib.request, datetime as dt
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lab'))
from engine import sim  # noqa: E402

S = sys.argv[1]; NMONTHS = int(os.environ.get('NMONTHS', '12'))
today = dt.date.today(); m = today.replace(day=1)
months = []
for _ in range(NMONTHS):
    m = (m - dt.timedelta(days=1)).replace(day=1); months.append(m)
months = sorted(months)
parts = []
for mo in months:
    url = f'https://data.binance.vision/data/spot/monthly/klines/{S}/1s/{S}-1s-{mo:%Y-%m}.zip'
    try:
        raw = urllib.request.urlopen(url, timeout=300).read()
    except Exception as e:
        print('missing', url, e, flush=True); continue
    z = zipfile.ZipFile(io.BytesIO(raw))
    with z.open(z.namelist()[0]) as f:
        k = pd.read_csv(f, header=None, usecols=[0, 4])
    k = k[pd.to_numeric(k[0], errors='coerce').notna()]
    t = k[0].astype('int64'); t = t.where(t < 1e14, t // 1000) // 1000  # -> seconds
    parts.append(pd.DataFrame({'t': t.values, 'p': k[4].astype('float64').values}))
    print(S, mo, len(k), flush=True)
d = pd.concat(parts).drop_duplicates('t').sort_values('t')
grid = np.arange(d.t.iloc[0], d.t.iloc[-1] + 1)
P = pd.Series(d.p.values, index=d.t.values).reindex(grid).ffill().values
print(S, 'seconds', len(P), 'coverage', round(len(d) / len(grid), 4), flush=True)

rows = []
for B in [2, 12]:
    idx = np.arange(120, len(P), B)
    Pb = P[idx]
    fin, worst = sim(Pb, base=0.003)[:2]
    rows.append(dict(coin=S, block=B, design='Uniswap 0.30%', lag=np.nan, alpha=0, final=fin, worst=worst))
    for a in [0.75, 0.9]:
        for L in [0, 1, 2, 3, 5, 10, 30, 60]:
            fin, worst = sim(Pb, O=P[idx - L], base=0.003, alpha=a)[:2]
            rows.append(dict(coin=S, block=B, design=f'Gap fee a={a}', lag=L, alpha=a, final=fin, worst=worst))
    print(S, 'block', B, 'done', flush=True)
os.makedirs(os.path.join(ROOT, 'results', 'latency'), exist_ok=True)
pd.DataFrame(rows).assign(start=str(months[0]), months=len(parts)).to_csv(
    os.path.join(ROOT, 'results', 'latency', f'{S}.csv'), index=False)
