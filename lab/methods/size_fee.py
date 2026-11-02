"""Trade-size-aware fee (Ledrov et al., Aug 2026) - oracle-free: big trades pay more, because the pool's biggest trades are
bots fixing a stale price. Tested alone and with the low-pass hedge."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _tools import lowpass_price
def designs(c):
    Hp = lowpass_price(c['P'], 1440)
    out = [(f'Trade-size fee g={g}', dict(base=0.003, gamma=g)) for g in [1.0, 2.0, 4.0]]
    out.append(('Trade-size fee g=2 + low-pass hedge 1d', dict(base=0.003, gamma=2.0, hedge=1, Hp=Hp)))
    out.append(('Gap fee fast + trade-size fee g=1', dict(base=0.003, alpha=0.9, gamma=1.0)))
    return out
