"""Space/navigation idea (Kalman-style tracking): when the oracle is 1 minute stale, predict the current price
from the stale price plus a smoothed velocity, then charge the gap fee against the prediction."""
import numpy as np
def designs(c):
    s = c['stale']; lr = np.r_[0, np.diff(np.log(s))]
    out = []
    for hl in [3, 15]:
        a = 1 - 0.5 ** (1 / hl); v = np.empty_like(lr); acc = 0.0
        for i in range(len(lr)):
            acc = (1 - a) * acc + a * lr[i]; v[i] = acc
        out.append((f'Gap fee 0.9 stale + velocity forecast hl={hl}', dict(base=0.003, alpha=0.9, O=s * np.exp(v))))
    return out
