"""From your list (A4, Adaptive Portfolio Insurance / CPPI): keep a loss floor. While the pool is comfortably above the floor
(e.g. calm years, fees piling up) hedge little and keep the round-trip gains; as it nears the floor, hedge fully."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from _tools import lowpass_price
def designs(c):
    Hp = lowpass_price(c['P'], 1440)
    out = []
    for fl, m in [(-0.01, 50), (-0.02, 25), (-0.03, 20)]:
        out.append((f'Gap fee fast + CPPI hedge floor {fl:.0%} m={m}', dict(base=0.003, alpha=0.9, hedge=3, floor=fl, m=m)))
        out.append((f'Gap fee fast + CPPI + low-pass 1d floor {fl:.0%} m={m}', dict(base=0.003, alpha=0.9, hedge=3, floor=fl, m=m, Hp=Hp)))
    return out
