"""AI storm fee: ML predicts chaotic minutes; 2-level and 5-level (surge pricing) fees."""
import numpy as np
def designs(c):
    s = c['score']
    storm = np.where(s > np.quantile(s, 0.9), 0.01, 0.003)
    q = np.quantile(s, [0.7, 0.9, 0.97, 0.995])
    surge = np.select([s > q[3], s > q[2], s > q[1], s > q[0]], [0.03, 0.02, 0.01, 0.005], 0.003)
    return [('AI storm fee', dict(base=storm)), ('AI surge fee (5 levels)', dict(base=surge))]
