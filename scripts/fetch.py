"""Download free Binance public data (data.binance.vision) and save compact Parquet files.
Spot 1-minute closes + quote volume, and USD-M futures funding rates, 2022 -> today."""
import io, zipfile, datetime as dt, urllib.request, os, pandas as pd

SYMS = os.environ.get('SYMS', 'BTCUSDT ETHUSDT XRPUSDT BNBUSDT SOLUSDT DOGEUSDT ADAUSDT TRXUSDT LINKUSDT AVAXUSDT').split()
START = dt.date(2022, 1, 1)
BASE = 'https://data.binance.vision/data'
os.makedirs('data', exist_ok=True)

def get_zip_csv(url, names=None):
    try:
        raw = urllib.request.urlopen(url, timeout=120).read()
    except Exception:
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    with z.open(z.namelist()[0]) as f:
        return pd.read_csv(f, header=None, names=names)

def months(until):
    d = START
    while d <= until:
        yield d
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

KCOLS = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qv', 'n', 'tbv', 'tbq', 'ign']
today = dt.date.today()
last_full = today.replace(day=1) - dt.timedelta(days=1)
for s in SYMS:
    frames = []
    for m in months(last_full):
        df = get_zip_csv(f'{BASE}/spot/monthly/klines/{s}/1m/{s}-1m-{m:%Y-%m}.zip', KCOLS)
        if df is not None: frames.append(df)
    d = today.replace(day=1)
    while d < today:  # current month from daily files
        df = get_zip_csv(f'{BASE}/spot/daily/klines/{s}/1m/{s}-1m-{d:%Y-%m-%d}.zip', KCOLS)
        if df is not None: frames.append(df)
        d += dt.timedelta(days=1)
    k = pd.concat(frames)
    k = k[pd.to_numeric(k.open_time, errors='coerce').notna()]
    t = k.open_time.astype('int64')
    t = t.where(t < 1e14, t // 1000)  # 2025+ files use microseconds
    out = pd.DataFrame({'t': t, 'close': k.close.astype('float64'), 'qv': k.qv.astype('float32')})
    out = out.drop_duplicates('t').sort_values('t')
    yr = pd.to_datetime(out.t, unit='ms').dt.year
    for y, g in out.groupby(yr):
        g.to_parquet(f'data/{s}_1m_{y}.parquet', index=False)
    fr = []
    for m in months(last_full):
        df = get_zip_csv(f'{BASE}/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m:%Y-%m}.zip')
        if df is not None: fr.append(df)
    if fr:
        f = pd.concat(fr)
        f = f[pd.to_numeric(f.iloc[:, 0], errors='coerce').notna()]
        pd.DataFrame({'t': f.iloc[:, 0].astype('int64'), 'rate': f.iloc[:, 2].astype(float)}).to_parquet(f'data/{s}_funding.parquet', index=False)
    print(s, len(out), 'minutes', len(fr), 'funding months', flush=True)
