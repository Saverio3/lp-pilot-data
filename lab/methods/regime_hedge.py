"""From your list (B9 Bayesian regime switching, B10 vol-of-vol): hedge more in the high-volatility regime / when
volatility itself is unstable; less in calm regimes."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import hmm_high_vol_prob, lowpass_price, ann_vol
def designs(c):
    P = c['P']; r = np.r_[0.0, np.diff(np.log(P))]
    s = np.median(np.abs(r[r != 0])) * 1.4826 + 1e-9
    ph = hmm_high_vol_prob(r, s * 0.7, s * 2.5, 0.999)
    import pandas as pd
    ph_s = pd.Series(ph).rolling(1440, min_periods=1).mean().values   # smooth the regime probability over a day
    Hp = lowpass_price(P, 1440)
    v = ann_vol(P, 10080); vv = pd.Series(v).rolling(43200, min_periods=1440).std().shift(1).bfill().values
    vvr = np.clip(vv / (np.median(vv) + 1e-12), 0.25, 1.0)
    return [('Gap fee fast + regime hedge (HMM)', dict(base=0.003, alpha=0.9, hedge=1, ratio=0.25 + 0.75 * ph_s, Hp=Hp)),
            ('Gap fee fast + vol-of-vol hedge', dict(base=0.003, alpha=0.9, hedge=1, ratio=vvr, Hp=Hp))]
