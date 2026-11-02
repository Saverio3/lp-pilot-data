"""INVENTION 2 - Fractal 'lean' hedge: measure persistence (variance ratio ~ Hurst exponent, 30-day window).
Trending ('branch leans one way') -> hedge fully; bouncing (mean-reverting) -> hedge little. Combined with gap fee."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import variance_ratio, lowpass_price
def designs(c):
    vr = variance_ratio(c['P'])
    scaled = np.clip(vr - 0.5, 0.0, 1.0)            # VR 0.5 -> 0, VR 1.5 -> full
    switch = np.where(vr > 1.0, 1.0, 0.25)
    Hp = lowpass_price(c['P'], 10080)
    return [('Gap fee 0.9 fast + fractal hedge (scaled)', dict(base=0.003, alpha=0.9, hedge=1, ratio=scaled)),
            ('Gap fee 0.9 fast + fractal hedge (switch)', dict(base=0.003, alpha=0.9, hedge=1, ratio=switch)),
            ('Gap fee 0.9 fast + fractal + low-pass 7d', dict(base=0.003, alpha=0.9, hedge=1, ratio=scaled, Hp=Hp))]
