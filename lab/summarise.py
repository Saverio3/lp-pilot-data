"""Combine results/raw/*.csv into results/SUMMARY.md and results/compounded.csv."""
import os, glob, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(ROOT, 'results', 'raw', '*.csv'))])
comp = d.groupby(['pair', 'design']).final.apply(lambda s: (np.prod(1 + s) - 1) * 100).unstack()
worst = d.groupby(['pair', 'design']).worst.min().unstack() * 100
by = d.pivot_table(index=['pair', 'year'], columns='design', values='final') * 100
UNI, COW = 'Uniswap 0.30%', 'CoW-style auction 80%'
bad = by[by[UNI] < -3]; calm = by[by[UNI] >= -3]
meth = d.drop_duplicates('design').set_index('design').method
s = pd.DataFrame({
    'method file': meth,
    'avg compounded %': comp.mean(),
    'beats Uniswap': (comp.gt(comp[UNI], axis=0)).sum().astype(str) + f'/{len(comp)}',
    'beats CoW': (comp.gt(comp[COW], axis=0)).sum().astype(str) + f'/{len(comp)}',
    'bad years %': bad.mean(), 'calm years %': calm.mean(),
    'avg worst moment %': worst.mean(), 'worst pair %': comp.min(),
    'avg pool-vs-market gap %': d.groupby('design').gap.mean() * 100 if 'gap' in d else np.nan,
    'pool off market >1% (time %)': d.groupby('design').off1pct.mean() * 100 if 'off1pct' in d else np.nan,
}).sort_values('avg compounded %', ascending=False)
os.makedirs(os.path.join(ROOT, 'results'), exist_ok=True)
comp.round(2).to_csv(os.path.join(ROOT, 'results', 'compounded.csv'))
with open(os.path.join(ROOT, 'results', 'SUMMARY.md'), 'w') as f:
    f.write('# Lab results\n\nCompounded LP result vs HODL, each year a fresh deposit, Jan 2022 to latest data. '
            f'{len(comp)} pairs. Bad years = years where Uniswap 0.30% lost >3% ({len(bad)} pair-years). '
            'Retail fees not modelled.\n\n')
    f.write(s.round(2).to_markdown() + '\n\n## Per pair (compounded %)\n\n')
    f.write(comp.T.loc[s.index].round(1).to_markdown() + '\n')
print(s.round(2).to_string())
