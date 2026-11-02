"""Gap fee as a Dutch auction (idea used by Uniswap's StablePair hook): the extra fee on bots starts at 90% of the gap and
falls to zero over a few minutes while the pool is off-market, so the pool always catches up (stays usable for traders)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import lowpass_price, garch
def designs(c):
    P = c['P']; Hp = lowpass_price(P, 1440)
    sd = garch(np.r_[0.0, np.diff(np.log(P))], 0.05, 0.94); gb = np.clip(0.003 + 1.5 * sd, 0.003, 0.05)
    out = []
    for T in [2, 5, 10]:
        out.append((f'Dutch gap fee fast, decay {T}m', dict(base=0.003, alpha=0.9, decay=T)))
        out.append((f'Dutch gap fee fast, decay {T}m + low-pass 1d band 20%', dict(base=0.003, alpha=0.9, decay=T, hedge=1, Hp=Hp, band=0.20)))
    out.append(('REALISTIC: Dutch gap fee stale feed decay 5m + GARCH fee + low-pass 1d band 20%',
                dict(base=gb, alpha=0.9, decay=5, O=c['stale'], hedge=1, Hp=Hp, band=0.20)))
    return out
