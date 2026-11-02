"""From your list (A1-A3, weighted variance swap / convexity replication, Fukasawa et al. 2023): a constant-product pool
loses pool value x variance / 8 over time. Add a variance swap that pays realised variance minus a strike.
Strike = past 30-day variance x markup (1.0 = fair, 1.2 = typical market markup). No such on-chain market exists today;
this measures what it would be worth."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from _tools import lowpass_price
def designs(c):
    P = c['P']; r = np.r_[0.0, np.diff(np.log(P))]
    v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03); F = dict(base=vf, gamma=1.0)
    k = pd.Series(r ** 2).rolling(43200, min_periods=1440).mean().shift(1).bfill().values
    Hp = lowpass_price(P, 1440); out = []
    for mk in [1.0, 1.2]:
        out.append((f'Earn + variance swap (markup {mk})', dict(F, vsn=1.0, vsk=k * mk)))
        out.append((f'Full hedge + variance swap (markup {mk})', dict(F, hedge=1, vsn=1.0, vsk=k * mk)))
        out.append((f'Shield band 30% + variance swap (markup {mk})', dict(F, hedge=1, Hp=Hp, band=0.30, vsn=1.0, vsk=k * mk)))
    return out
