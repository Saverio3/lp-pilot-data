"""The realistic full product: price feed 1 minute late (pessimistic) + GARCH uncertainty fee + low-pass hedge variants."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import garch, lowpass_price
def designs(c):
    P = c['P']; r = np.r_[0.0, np.diff(np.log(P))]; sd = garch(r, 0.05, 0.94)
    base = np.clip(0.003 + 1.5 * sd, 0.003, 0.05); Hp = lowpass_price(P, 1440)
    return [('REALISTIC: stale feed + GARCH fee + low-pass 1d hedge', dict(base=base, alpha=0.9, O=c['stale'], hedge=1, Hp=Hp)),
            ('REALISTIC: stale feed + GARCH fee + low-pass 1d, band 10%', dict(base=base, alpha=0.9, O=c['stale'], hedge=1, Hp=Hp, band=0.10)),
            ('REALISTIC: stale feed + GARCH fee + CPPI low-pass floor -2%', dict(base=base, alpha=0.9, O=c['stale'], hedge=3, floor=-0.02, m=25, Hp=Hp))]
