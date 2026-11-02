"""INVENTION 1 - Fourier low-pass hedge: a price path = slow trend + fast wiggles (like a curve built from circles).
Wiggles come back, so hedging them only costs money. Hedge the low-pass (slow) part only. Combined with gap fee."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _tools import lowpass_price
def designs(c):
    out = []
    for hl, nm in [(360, '6h'), (1440, '1d'), (10080, '7d'), (43200, '30d')]:
        Hp = lowpass_price(c['P'], hl)
        out.append((f'Gap fee 0.9 fast + low-pass hedge {nm}', dict(base=0.003, alpha=0.9, hedge=1, ratio=1.0, Hp=Hp)))
    Hp = lowpass_price(c['P'], 10080)
    out.append(('Gap fee 0.9 stale + low-pass hedge 7d', dict(base=0.003, alpha=0.9, O=c['stale'], hedge=1, ratio=1.0, Hp=Hp)))
    return out
