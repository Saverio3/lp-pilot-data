"""Off-chain hedge bot realism: the keeper only checks every 5 or 60 minutes, pays a real perp taker fee (4.5bp, e.g.
Hyperliquid) and extra slippage. Applied to Shield (band 5%) and the band 30% + 7-day design."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import lowpass_price
def designs(c):
    P = c['P']; v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03); F = dict(base=vf, gamma=1.0)
    out = []
    for ev, sl in [(5, 0.0003), (60, 0.0010)]:
        R = dict(hevery=ev, hslip=sl, perp_fee=0.00045)
        out.append((f'Shield band 5%, keeper every {ev}m, slippage {sl*1e4:.0f}bp', dict(F, hedge=1, Hp=lowpass_price(P, 1440), band=0.05, **R)))
        out.append((f'Band 30% + 7d, keeper every {ev}m, slippage {sl*1e4:.0f}bp', dict(F, hedge=1, Hp=lowpass_price(P, 10080), band=0.30, **R)))
    return out
