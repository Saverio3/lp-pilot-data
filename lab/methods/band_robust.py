"""Robustness check of the 30% no-trade band (battery idea): wider/narrower bands, other smoothing speeds, combinations."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import lowpass_price, ann_vol
def designs(c):
    P = c['P']; v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03); F = dict(base=vf, gamma=1.0)
    out = []
    for b in [0.25, 0.35, 0.40, 0.50]:
        out.append((f'Band {b:.0%} + low-pass 1d', dict(F, hedge=1, Hp=lowpass_price(P, 1440), band=b)))
    for hl, nm in [(360, '6h'), (10080, '7d')]:
        out.append((f'Band 30% + low-pass {nm}', dict(F, hedge=1, Hp=lowpass_price(P, hl), band=0.30)))
    out.append(('Band 30% + no smoothing (plain hedge)', dict(F, hedge=1, band=0.30)))
    Hp = lowpass_price(P, 1440)
    out.append(('Band 30% + low-pass 1d + homeostasis b=0.02', dict(F, beta=0.02, hedge=1, Hp=Hp, band=0.30)))
    out.append(('Band 30% + low-pass 1d + pair-volatility (full at 60%/yr)', dict(F, hedge=1, Hp=Hp, band=0.30, ratio=np.clip(ann_vol(P) / 0.6, 0, 1))))
    return out
