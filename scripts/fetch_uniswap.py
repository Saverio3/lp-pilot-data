"""Download REAL Uniswap pool data via The Graph (needs GitHub secret GRAPH_API_KEY).
For the biggest Uniswap v3 pools matching our coins: daily volume, liquidity (TVL), fees and swap counts since 2022.
This replaces the lab's assumed normal-trader turnover (10%/day) with real numbers.
Saves data/uniswap_pooldays.parquet and data/uniswap_pools.csv; prints a summary."""
import os, json, time, urllib.request, urllib.error, pandas as pd

KEY = os.environ.get('GRAPH_API_KEY', '').strip()
print('API key present:', bool(KEY), '| length:', len(KEY), flush=True)
UA = {'Content-Type': 'application/json', 'User-Agent': 'lp-pilot-research/1.0', 'Accept': 'application/json'}
SUBGRAPHS = {  # official Uniswap v3 subgraphs on The Graph network (IDs); failures are reported, not fatal
    'ethereum': '5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV',
    'arbitrum': 'FbCGRftH4a3yZugY7TnbYgPJVEv2LvMT6oF1fxPe9aJM',
    'base': '43Hwfi3dJSoGpyas9VwNoDAv55yjgGrPpNSmbQZArzMG',
}
COINS = {'WETH': 'ETH', 'ETH': 'ETH', 'WBTC': 'BTC', 'cbBTC': 'BTC', 'tBTC': 'BTC', 'LINK': 'LINK', 'SOL': 'SOL', 'WSOL': 'SOL',
         'XRP': 'XRP', 'BNB': 'BNB', 'WBNB': 'BNB', 'DOGE': 'DOGE', 'ADA': 'ADA', 'TRX': 'TRX', 'AVAX': 'AVAX', 'WAVAX': 'AVAX',
         'USDC': 'USD', 'USDT': 'USD', 'USDC.e': 'USD', 'DAI': 'USD'}


def q(sub, query):
    body = json.dumps({'query': query}).encode()
    tries = [(f'https://gateway.thegraph.com/api/{KEY}/subgraphs/id/{sub}', UA),
             (f'https://gateway.thegraph.com/api/subgraphs/id/{sub}', dict(UA, Authorization=f'Bearer {KEY}'))]
    err = None
    for attempt in range(3):
        for url, hd in tries:
            try:
                r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=hd), timeout=60).read())
                if 'errors' in r: raise RuntimeError(str(r['errors'])[:300])
                return r['data']
            except urllib.error.HTTPError as e:
                err = RuntimeError(f'HTTP {e.code}: ' + e.read()[:300].decode('utf-8', 'ignore'))
            except Exception as e:
                err = e
        time.sleep(3 * (attempt + 1))
    raise err


pools, days = [], []
for chain, sub in SUBGRAPHS.items():
    try:
        d = q(sub, '{pools(first: 300, orderBy: totalValueLockedUSD, orderDirection: desc) {id feeTier totalValueLockedUSD token0 {symbol} token1 {symbol}}}')
    except Exception as e:
        print(chain, 'FAILED pools:', str(e)[:200], flush=True); continue
    for p in d['pools']:
        a, b = COINS.get(p['token0']['symbol']), COINS.get(p['token1']['symbol'])
        if not a or not b or a == b: continue
        pair = '_'.join(sorted([a, b], key=lambda s: (s == 'USD', s)))
        pools.append(dict(chain=chain, pool=p['id'], pair=pair, fee=int(p['feeTier']) / 1e6, tvl_now=float(p['totalValueLockedUSD']),
                          t0=p['token0']['symbol'], t1=p['token1']['symbol']))
pl = pd.DataFrame(pools)
print('matched pools:', len(pl), flush=True)
if len(pl):
    pl = pl[pl.tvl_now > 200_000].sort_values('tvl_now', ascending=False).groupby(['chain', 'pair']).head(3)
    for _, p in pl.iterrows():
        last = 1640995200  # 2022-01-01
        while True:
            try:
                d = q(SUBGRAPHS[p.chain], '{poolDayDatas(first: 1000, orderBy: date, where: {pool: "%s", date_gt: %d}) {date volumeUSD tvlUSD feesUSD txCount close}}' % (p.pool, last))
            except Exception as e:
                print(p.chain, p.pair, 'FAILED days:', str(e)[:150], flush=True); break
            rows = d['poolDayDatas']
            for r in rows:
                days.append(dict(chain=p.chain, pool=p.pool, pair=p.pair, fee=p.fee, date=int(r['date']), volume=float(r['volumeUSD']),
                                 tvl=float(r['tvlUSD']), fees=float(r['feesUSD']), swaps=int(r['txCount']), close=float(r['close'])))
            if len(rows) < 1000: break
            last = int(rows[-1]['date'])
        print(p.chain, p.pair, p.fee, 'days so far', len(days), flush=True)
os.makedirs('data', exist_ok=True)
pl.to_csv('data/uniswap_pools.csv', index=False)
dd = pd.DataFrame(days)
dd.to_parquet('data/uniswap_pooldays.parquet', index=False)
if len(dd):
    dd = dd[dd.tvl > 100_000]
    dd['turnover'] = dd.volume / dd.tvl; dd['fee_apr'] = dd.fees / dd.tvl * 365
    s = dd.groupby(['chain', 'pair', 'fee']).agg(days=('date', 'size'), median_daily_turnover=('turnover', 'median'),
                                                  median_fee_apr=('fee_apr', 'median'), median_tvl=('tvl', 'median')).round(4)
    print(s.to_string()); s.to_csv('data/uniswap_summary.csv')
