"""INVENTION 3b - late price feed fixed two ways at once: predict where the price is now (velocity forecast, navigation-style)
AND charge for the remaining uncertainty (GARCH). Stronger uncertainty levels tested too."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import garch, ema
def designs(c):
    P = c['P']; s_ = c['stale']; r = np.r_[0.0, np.diff(np.log(P))]
    sd = garch(r, 0.05, 0.94)
    lr = np.r_[0.0, np.diff(np.log(s_))]; v = ema(lr, 3.0)
    Of = s_ * np.exp(v + lr * 0)  # forecast of current price from stale feed
    out = []
    for z in [1.5, 2.0]:
        out.append((f'Gap fee 0.9 stale + GARCH uncertainty z={z}', dict(base=np.clip(0.003 + z * sd, 0.003, 0.05), alpha=0.9, O=s_)))
    for z in [1.0, 1.5]:
        out.append((f'Gap fee 0.9 stale + forecast + GARCH z={z}', dict(base=np.clip(0.003 + z * sd, 0.003, 0.05), alpha=0.9, O=Of)))
    out.append(('Gap fee 0.9 stale + GARCH z=1 + quarter hedge', dict(base=np.clip(0.003 + sd, 0.003, 0.05), alpha=0.9, O=s_, hedge=1, ratio=0.25)))
    return out
