"""From your list (C14, battery state-of-charge bands / no-trade zone): only re-hedge when the hedge is far off target.
Fewer re-hedges = less of the bleed that hurts in calm years."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _tools import lowpass_price
def designs(c):
    Hp = lowpass_price(c['P'], 1440)
    out = []
    for b in [0.05, 0.10, 0.20, 0.30]:
        out.append((f'Gap fee fast + low-pass 1d, band {b:.0%}', dict(base=0.003, alpha=0.9, hedge=1, Hp=Hp, band=b)))
    out.append(('Gap fee fast + full hedge, band 10%', dict(base=0.003, alpha=0.9, hedge=1, band=0.10)))
    return out
