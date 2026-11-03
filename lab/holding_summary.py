import os, glob, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(ROOT, 'results', 'holding', '*.csv'))])
d = d.groupby(['pair', 'start', 'days', 'design'], as_index=False).mean(numeric_only=True)
# re-scale normal-trader income to REAL Uniswap turnover (half of real 0.30%-pool volume; linear in turnover)
REAL = {'ETH_USD': 0.093, 'BTC_USD': 0.035, 'BTC_ETH': 0.042, 'LINK_ETH': 0.120, 'LINK_USD': 0.108, 'SOL_ETH': 0.107}
T = d.pair.map(lambda p: REAL.get(p, float(np.median(list(REAL.values()))))) * 0.5
d['final_real'] = d.final + (d.final_r2 - d.final) * T / 0.10
u = d[d.design == 'Uniswap 0.30%'].set_index(['pair', 'start', 'days'])
out = []
for col, lab in [('final_real', 'with normal traders at REAL Uniswap volumes (strong fee reaction)'), ('final', 'without normal traders (bots only)')]:
    for (days, des), g in d.groupby(['days', 'design']):
        gi = g.set_index(['pair', 'start', 'days'])[col] * 100; ui = u[col].reindex(gi.index) * 100
        out.append(dict(scenario=lab, days=days, design=des, median=gi.median(), mean=gi.mean(), p5_worst_case=gi.quantile(0.05),
                        pct_positive=(gi > 0).mean() * 100, pct_beats_uniswap=(gi > ui).mean() * 100, n=len(gi)))
s = pd.DataFrame(out)
with open(os.path.join(ROOT, 'results', 'HOLDING.md'), 'w') as f:
    f.write('# Holding period test\n\nDeposits starting every month, held 30/90/365/730 days, 16 pairs. % vs HODL.\n\n')
    for sc in s.scenario.unique():
        f.write(f'## {sc}\n\n' + s[s.scenario == sc].drop(columns='scenario').round(2).to_markdown(index=False) + '\n\n')
print(s.round(2).to_string())
