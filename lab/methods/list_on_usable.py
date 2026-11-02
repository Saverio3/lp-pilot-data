"""Chris's pasted methods re-tested FAIRLY on the usable oracle-free fee (trade-size g=1 + volatility fee), so the pool
stays near market. Compare with 'ORACLE-FREE: ... low-pass 1d band 5%' (Shield) and 'Trade-size fee g=1 + vol fee' (Earn)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from _tools import lowpass_price, hmm_high_vol_prob, ann_vol
def designs(c):
    P = c['P']; Hp = lowpass_price(P, 1440)
    v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03)
    F = dict(base=vf, gamma=1.0)
    r = np.r_[0.0, np.diff(np.log(P))]; s = np.median(np.abs(r[r != 0])) * 1.4826 + 1e-9
    ph = pd.Series(hmm_high_vol_prob(r, s * 0.7, s * 2.5, 0.999)).rolling(1440, min_periods=1).mean().values
    av = ann_vol(P, 10080); vv = pd.Series(av).rolling(43200, min_periods=1440).std().shift(1).bfill().values
    vvr = np.clip(vv / (np.median(vv) + 1e-12), 0.25, 1.0); pv = ann_vol(P)
    out = []
    for fl, m in [(-0.02, 25), (-0.03, 20)]:
        out.append((f'USABLE + CPPI floor {fl:.0%} (list A4)', dict(F, hedge=3, floor=fl, m=m, Hp=Hp, band=0.05)))
    for b in [0.10, 0.20, 0.30]:
        out.append((f'USABLE + low-pass hedge band {b:.0%} (list C14 battery bands)', dict(F, hedge=1, Hp=Hp, band=b)))
    out.append(('USABLE + regime hedge HMM (list B9)', dict(F, hedge=1, ratio=0.25 + 0.75 * ph, Hp=Hp, band=0.05)))
    out.append(('USABLE + vol-of-vol hedge (list B10)', dict(F, hedge=1, ratio=vvr, Hp=Hp, band=0.05)))
    for ref in [0.6, 0.9]:
        out.append((f'USABLE + pair-volatility hedge, full at {ref:.0%}/yr', dict(F, hedge=1, ratio=np.clip(pv / ref, 0, 1), Hp=Hp, band=0.05)))
    out.append(('USABLE + inventory fee b=0.02 (list C12/C13 homeostasis)', dict(F, beta=0.02, hedge=1, Hp=Hp, band=0.05)))
    out.append(('USABLE + shear fee + low-pass band 5% (list 1 #14)', dict(base=np.clip(vf + 0.0005 * (np.r_[0.0, np.abs(r[:-1])] / (np.median(np.abs(r[r != 0])) + 1e-12)) ** 2, 0.003, 0.05), gamma=1.0, hedge=1, Hp=Hp, band=0.05)))
    return out
