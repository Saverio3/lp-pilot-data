"""INVENTION 3 - GARCH uncertainty fee: when the price feed is late, the true price may have moved ~ sigma*sqrt(delay).
Charge that expected unseen move on top of the gap fee (sigma from a GARCH(1,1) forecast, past-only).
Also GARCH volatility fee vs AI / simple volatility."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import garch
def designs(c):
    P = c['P']; r = np.r_[0.0, np.diff(np.log(P))]
    s = garch(r, 0.05, 0.94)                       # 1-minute forecast st. dev.
    m = np.median(s)
    out = [('GARCH volatility fee', dict(base=np.clip(0.003 * s / m, 0.003, 0.03)))]
    for z in [0.5, 1.0]:
        out.append((f'Gap fee 0.9 stale + GARCH uncertainty z={z}', dict(base=np.clip(0.003 + z * s, 0.003, 0.05), alpha=0.9, O=c['stale'])))
    out.append(('Gap fee 0.9 fast + GARCH uncertainty z=0.5', dict(base=np.clip(0.003 + 0.5 * s, 0.003, 0.05), alpha=0.9)))
    return out
