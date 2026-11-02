"""Only designs that keep the pool near the market price (usable for normal traders), combined:
trade-size fee (oracle-free), Dutch-auction gap fee, volatility fee, low-pass hedge with no-trade bands."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import lowpass_price
def designs(c):
    P = c['P']; Hp = lowpass_price(P, 1440)
    v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03)
    out = [('Trade-size fee g=1.5', dict(base=0.003, gamma=1.5)),
           ('Trade-size fee g=1 + Dutch gap fee 10m', dict(base=0.003, gamma=1.0, alpha=0.9, decay=10)),
           ('Trade-size fee g=1 + vol fee', dict(base=vf, gamma=1.0)),
           ('Dutch gap fee 20m', dict(base=0.003, alpha=0.9, decay=20)),
           ('Dutch gap fee 30m', dict(base=0.003, alpha=0.9, decay=30))]
    for b in [0.02, 0.05, 0.20]:
        out.append((f'Trade-size fee g=1 + low-pass 1d hedge band {b:.0%}', dict(base=0.003, gamma=1.0, hedge=1, Hp=Hp, band=b)))
    out.append(('Trade-size g=1 + Dutch 10m + low-pass 1d band 5%', dict(base=0.003, gamma=1.0, alpha=0.9, decay=10, hedge=1, Hp=Hp, band=0.05)))
    out.append(('ORACLE-FREE: trade-size g=1 + vol fee + low-pass 1d band 5%', dict(base=vf, gamma=1.0, hedge=1, Hp=Hp, band=0.05)))
    out.append(('Dutch gap fee 10m + low-pass 1d band 5%', dict(base=0.003, alpha=0.9, decay=10, hedge=1, Hp=Hp, band=0.05)))
    return out
