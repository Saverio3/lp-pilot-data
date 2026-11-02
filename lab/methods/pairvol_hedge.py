"""Fix for where we lose (pairs that move together, calm years): hedge in proportion to how volatile the pair is.
Calm/correlated pairs (BTC/ETH ~ 30-40%/yr) get a light hedge, wild pairs (SOL ~ 80-100%) a full one."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import ann_vol, lowpass_price
def designs(c):
    v = ann_vol(c['P']); Hp = lowpass_price(c['P'], 1440)
    out = []
    for ref in [0.6, 0.9]:
        out.append((f'Gap fee fast + pair-volatility hedge (full at {ref:.0%}/yr)', dict(base=0.003, alpha=0.9, hedge=1, ratio=np.clip(v / ref, 0.0, 1.0), Hp=Hp)))
    return out
