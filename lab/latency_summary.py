import os, glob, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(ROOT, 'results', 'latency', '*.csv'))])
d['final'] *= 100
uni = d[d.design == 'Uniswap 0.30%'].set_index(['coin', 'block']).final
g = d[d.design != 'Uniswap 0.30%'].pivot_table(index=['coin', 'block', 'alpha'], columns='lag', values='final')
g.insert(0, 'Uniswap', [uni[(c, b)] for c, b, _ in g.index])
with open(os.path.join(ROOT, 'results', 'LATENCY.md'), 'w') as f:
    f.write('# Price-feed delay test (1-second Binance data)\n\nLP result vs HODL over the test window (%). '
            f'Window starts {d.start.iloc[0]}, {int(d.months.max())} months. Columns = oracle delay in seconds. '
            'block = seconds between blocks (2 = L2, 12 = Ethereum).\n\n')
    f.write(g.round(2).to_markdown() + '\n')
print(g.round(2).to_string())
