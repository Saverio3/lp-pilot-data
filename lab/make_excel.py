"""Build results/LP_results.xlsx from the lab's raw results (results/raw, results/holding, data/uniswap_*).
Run: python lab/make_excel.py"""
import os, glob
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda *p: os.path.join(ROOT, *p)
FONT = 'Arial'
HEAD = PatternFill('solid', start_color='1F3A5F'); HFONT = Font(name=FONT, bold=True, color='FFFFFF')
KEY = PatternFill('solid', start_color='E8F1FB'); THIN = Side(style='thin', color='C9D3E0')

# real Uniswap turnover (median daily volume / liquidity of 0.30% pools, The Graph); normal traders = 50% of it
REAL = {'ETH_USD': 0.093, 'BTC_USD': 0.035, 'BTC_ETH': 0.042, 'LINK_ETH': 0.120, 'LINK_USD': 0.108, 'SOL_ETH': 0.107}
DEFAULT = float(np.median(list(REAL.values())))
U = 'Uniswap 0.30%'
KEYS = {  # lab design name -> name shown in the workbook
    'Uniswap 0.30%': 'Uniswap 0.30% (benchmark)',
    'CoW-style auction 80%': 'CoW-style batch auction',
    'FLAT Earn (0.30% + size fee)': 'EARN: 0.30% + per-block size fee (the hook)',
    'FLAT Per-pair rule (yearly, lookback 365d)': 'Balanced: Earn + hedge on volatile pairs',
    'FLAT Shield band 5% + low-pass 1d': 'Shield: Earn + tight hedge',
    'Partially active AMM lambda=0.5': 'Partially Active AMM (2026 paper)',
    'Variance-feedback fee (2026 optimal fee)': 'Variance-feedback fee (2026 paper)',
    'Volatility-scaled fee (no AI)': 'Volatility-based fee (like vol-fee hooks)',
}


def load():
    d = pd.concat([pd.read_csv(f) for f in glob.glob(R('results', 'raw', '*.csv'))])
    T = d.pair.map(lambda p: REAL.get(p, DEFAULT)) * 0.5
    d['real'] = d.final + (d.final_r2 - d.final) * T / 0.10   # normal-trader income is linear in turnover
    return d


def comp(s):
    return (np.prod(1 + s) - 1)


def style_table(ws, top, ncols, nrows, pct_cols=(), int_cols=(), widths=None):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=top, column=c); cell.fill = HEAD; cell.font = HFONT
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    for r in range(top + 1, top + 1 + nrows):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=r, column=c); cell.font = Font(name=FONT, size=10)
            cell.border = Border(bottom=THIN)
            if c in pct_cols: cell.number_format = '0.0%;[Red]-0.0%;0.0%'
            if c in int_cols: cell.number_format = '0'
    ws.row_dimensions[top].height = 42
    for i, w in enumerate(widths or [], 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_df(ws, df, top=1, pct_cols=(), int_cols=(), widths=None, index=True):
    df = df.reset_index() if index else df
    for j, c in enumerate(df.columns, 1): ws.cell(row=top, column=j, value=str(c))
    for i, row in enumerate(df.itertuples(index=False), top + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, (float, np.floating)) and np.isnan(v): v = None
            elif isinstance(v, np.generic): v = v.item()
            ws.cell(row=i, column=j, value=v)
    style_table(ws, top, len(df.columns), len(df), pct_cols, int_cols, widths)
    ws.freeze_panes = ws.cell(row=top + 1, column=2)
    return top + len(df)


def main():
    d = load()
    wb = Workbook()

    # --- README
    ws = wb.active; ws.title = 'README'
    lines = [
        ('LP results: Earn hook vs Uniswap and other designs', True),
        ('All numbers are simulated LP results versus simply holding the two tokens (HODL), from the open lab in this repository.', False),
        ('', False),
        ('Data', True),
        ('Prices: Binance public 1-minute data (data.binance.vision), Jan 2022 to latest month, 10 coins and 6 crypto/crypto pairs (16 pairs).', False),
        ('Funding rates: Binance USD-M perpetual funding (used by hedged designs).', False),
        ('Real Uniswap trading levels: Uniswap v3 subgraphs via The Graph (Ethereum, Arbitrum, Base), 76 pools, 2022 to now.', False),
        ('', False),
        ('Assumptions', True),
        ('Pool: $10M, full-range constant-product. Arbitrage bots trade whenever profitable after 2bp exchange cost and $0.05 gas (L2).', False),
        ('Normal traders: 50% of the real Uniswap 0.30%-pool volume for each pair (median of available pairs when Uniswap has no pool).', False),
        ('Normal traders react strongly to fees: their volume falls with (0.30% / fee)^2. Their fee income is credited to the LP.', False),
        ('"5-year" = Jan 2022 to latest month, each calendar year a fresh deposit, compounded. "Bad years" = years where Uniswap lost >3% before trader fees.', False),
        ('Hedged designs: spot + perpetual hedge with 3-5bp fees and funding; keeper realism tested separately (every 5-60 min, extra slippage).', False),
        ('', False),
        ('Sheets', True),
        ('Headline: main designs, 16-pair averages.  Per pair: 5-year result per pair.  Per year: each pair and year.', False),
        ('Holding periods: deposits started every month and held 1, 3, 12 or 24 months.  Real Uniswap data: turnover and fee income.', False),
        ('All designs: every design tested in the lab (about 150), including the ones that failed, with the pool-drift safety check.', False),
        ('', False),
        ('Caveats', True),
        ('Simulation, not live trading. The split between bot and normal-trader volume and how strongly traders react to fees are modelled.', False),
        ('The hook is untested with real funds and not audited.', False),
    ]
    for i, (t, b) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t); c.font = Font(name=FONT, bold=b, size=13 if i == 1 else 10)
    ws.column_dimensions['A'].width = 150

    # --- Headline
    ws = wb.create_sheet('Headline')
    base = d.pivot_table(index=['pair', 'year'], columns='design', values='final')
    rows = []
    for k, nm in KEYS.items():
        g = d[d.design == k]
        if g.empty: continue
        cr = g.groupby('pair').real.apply(comp); cb = g.groupby('pair').final.apply(comp)
        ur = d[d.design == U].groupby('pair').real.apply(comp)
        by = g.set_index(['pair', 'year']).real
        bad = by[base[U].reindex(by.index) < -0.03].mean(); calm = by[base[U].reindex(by.index) >= -0.03].mean()
        rows.append({'Design': nm, '5-yr LP result, with normal traders (avg of 16 pairs)': cr.mean(),
                     '5-yr LP result, bots only (no trader fees)': cb.mean(),
                     'Pairs beating Uniswap (of 16)': int((cr > ur.reindex(cr.index)).sum()),
                     'Pairs ending negative': int((cr < 0).sum()), 'Worst pair, 5-yr': cr.min(),
                     'Avg in bad years': bad, 'Avg in calm years': calm,
                     'Pool >1% off market (share of time)': g.off1pct.mean()})
    h = pd.DataFrame(rows)
    ws.cell(row=1, column=1, value='Main designs: 16-pair averages, Jan 2022 to latest month').font = Font(name=FONT, bold=True, size=12)
    last = write_df(ws, h, top=3, pct_cols=(2, 3, 6, 7, 8, 9), int_cols=(4, 5), index=False,
                    widths=[44, 18, 18, 14, 12, 14, 14, 14, 16])
    # difference vs Uniswap as formulas (row 4 is Uniswap)
    ws.cell(row=3, column=10, value='Difference vs Uniswap (with traders)')
    style_table(ws, 3, 10, len(h), pct_cols=(2, 3, 6, 7, 8, 9, 10), int_cols=(4, 5))
    for r in range(4, last + 1):
        ws.cell(row=r, column=10, value=f'=B{r}-$B$4').number_format = '+0.0%;[Red]-0.0%;0.0%'
    ws.column_dimensions['J'].width = 16
    for r in range(4, last + 1):
        if 'EARN' in str(ws.cell(row=r, column=1).value):
            for c in range(1, 11): ws.cell(row=r, column=c).fill = KEY
    ws.cell(row=last + 2, column=1, value='Results are simulated vs holding the tokens. Source: lab/ in this repo; assumptions on README sheet.').font = Font(name=FONT, italic=True, size=9)

    # --- Per pair
    ws = wb.create_sheet('Per pair')
    pp = d[d.design.isin(KEYS)].groupby(['pair', 'design']).real.apply(comp).unstack()[[k for k in KEYS if k in set(d.design)]]
    pp.columns = [KEYS[c] for c in pp.columns]; pp.index.name = 'Pair'
    ws.cell(row=1, column=1, value='5-year LP result per pair, with normal traders at real Uniswap volumes').font = Font(name=FONT, bold=True, size=12)
    n = len(pp.columns)
    last = write_df(ws, pp, top=3, pct_cols=tuple(range(2, n + 2)), widths=[12] + [20] * n)
    ws.cell(row=3, column=n + 2, value='EARN minus Uniswap')
    style_table(ws, 3, n + 2, len(pp), pct_cols=tuple(range(2, n + 3)))
    ce = get_column_letter(list(pp.columns).index(KEYS['FLAT Earn (0.30% + size fee)']) + 2)
    cu = get_column_letter(list(pp.columns).index(KEYS[U]) + 2)
    for r in range(4, last + 1):
        ws.cell(row=r, column=n + 2, value=f'={ce}{r}-{cu}{r}').number_format = '+0.0%;[Red]-0.0%;0.0%'
    ws.cell(row=last + 1, column=1, value='Average')
    for c in range(2, n + 3):
        L = get_column_letter(c)
        x = ws.cell(row=last + 1, column=c, value=f'=AVERAGE({L}4:{L}{last})'); x.number_format = '0.0%;[Red]-0.0%'; x.font = Font(name=FONT, bold=True)
    ws.cell(row=last + 1, column=1).font = Font(name=FONT, bold=True)
    ws.column_dimensions[get_column_letter(n + 2)].width = 16

    # --- Per year
    ws = wb.create_sheet('Per year')
    k3 = ['Uniswap 0.30%', 'FLAT Earn (0.30% + size fee)', 'FLAT Per-pair rule (yearly, lookback 365d)', 'FLAT Shield band 5% + low-pass 1d']
    py = d[d.design.isin(k3)].pivot_table(index=['pair', 'year'], columns='design', values=['real', 'final'])
    py.columns = [f"{KEYS[dz]} | {'with traders' if v == 'real' else 'bots only'}" for v, dz in py.columns]
    mv = d[d.design == U].set_index(['pair', 'year']).move.rename('Price move of the pair in the year')
    py = py.join(mv)
    ws.cell(row=1, column=1, value='Each pair and calendar year (fresh deposit each year)').font = Font(name=FONT, bold=True, size=12)
    write_df(ws, py.reset_index(), top=3, pct_cols=tuple(range(3, 3 + len(py.columns))), index=False,
             widths=[12, 8] + [18] * len(py.columns))

    # --- Holding periods
    ws = wb.create_sheet('Holding periods')
    hf = glob.glob(R('results', 'holding', '*.csv'))
    if hf:
        hd = pd.concat([pd.read_csv(f) for f in hf]).groupby(['pair', 'start', 'days', 'design'], as_index=False).mean(numeric_only=True)
        T = hd.pair.map(lambda p: REAL.get(p, DEFAULT)) * 0.5
        hd['real'] = hd.final + (hd.final_r2 - hd.final) * T / 0.10
        u = hd[hd.design == U].set_index(['pair', 'start', 'days']).real
        out = []
        for (days, des), g in hd.groupby(['days', 'design']):
            gi = g.set_index(['pair', 'start', 'days']).real
            out.append({'Held for (days)': days, 'Design': des, 'Typical result (median)': gi.median(),
                        'Bad case (worst 5%)': gi.quantile(0.05), 'Worst case': gi.min(),
                        'Share of deposits ending positive': (gi > 0).mean(),
                        'Share of deposits beating Uniswap': (gi > u.reindex(gi.index)).mean(), 'Number of deposits': len(gi)})
        ho = pd.DataFrame(out)
        ws.cell(row=1, column=1, value='Deposits started at the beginning of every month, held 1, 3, 12 or 24 months; with normal traders at real Uniswap volumes').font = Font(name=FONT, bold=True, size=12)
        write_df(ws, ho, top=3, pct_cols=(3, 4, 5, 6, 7), int_cols=(1, 8), index=False, widths=[12, 40, 16, 16, 14, 18, 18, 12])

    # --- Real Uniswap data
    ws = wb.create_sheet('Real Uniswap data')
    if os.path.exists(R('data', 'uniswap_pooldays.parquet')):
        u = pd.read_parquet(R('data', 'uniswap_pooldays.parquet'))
        u = u[u.tvl > 100_000]; u['turn'] = u.volume / u.tvl; u['apr'] = u.fees / u.tvl * 365
        s = u.groupby(['chain', 'pair', 'fee']).agg(days=('date', 'size'), turn=('turn', 'median'), apr=('apr', 'median'), tvl=('tvl', 'median')).reset_index()
        s.columns = ['Chain', 'Pair', 'Fee tier', 'Days of data', 'Median daily volume / liquidity', 'Median fee income per year', 'Median liquidity ($)']
        ws.cell(row=1, column=1, value='Real Uniswap v3 pools (The Graph), 2022 to now').font = Font(name=FONT, bold=True, size=12)
        last = write_df(ws, s, top=3, pct_cols=(3, 5, 6), int_cols=(4,), index=False, widths=[12, 12, 10, 10, 18, 18, 18])
        for r in range(4, last + 1): ws.cell(row=r, column=7).number_format = '$#,##0'
        ws.cell(row=r, column=3).number_format = '0.00%'

    # --- All designs
    ws = wb.create_sheet('All designs')
    c = d.groupby(['pair', 'design']).final.apply(comp).unstack(); cr = d.groupby(['pair', 'design']).real.apply(comp).unstack()
    al = pd.DataFrame({'Method file (lab/methods)': d.drop_duplicates('design').set_index('design').method,
                       '5-yr result, bots only': c.mean(), '5-yr result, with normal traders': cr.mean(),
                       'Pairs beating Uniswap (bots only)': c.gt(c[U], axis=0).sum(),
                       'Worst pair (bots only)': c.min(),
                       'Pool >1% off market (share of time)': d.groupby('design').off1pct.mean()})
    al['Usable pool?'] = np.where(al['Pool >1% off market (share of time)'] < 0.02, 'yes', 'NO: price drifts from market')
    al = al.sort_values('5-yr result, bots only', ascending=False); al.index.name = 'Design'
    ws.cell(row=1, column=1, value='Every design tested (unusable = pool price drifts from the market, so real traders would avoid it)').font = Font(name=FONT, bold=True, size=12)
    write_df(ws, al, top=3, pct_cols=(3, 4, 6, 7), int_cols=(5,), widths=[62, 20, 14, 14, 12, 12, 14, 26])

    wb.calculation.fullCalcOnLoad = True
    os.makedirs(R('results'), exist_ok=True)
    wb.save(R('results', 'LP_results.xlsx'))
    print('saved results/LP_results.xlsx')


if __name__ == '__main__':
    main()
