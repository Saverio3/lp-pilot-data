"""Attack test: bots split each big trade into 10 or 50 small ones to dodge a per-trade size fee.
'per-block' = the fix: fee charged on the total move within the block (what the other designs assume)."""
import numpy as np
def designs(c):
    v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03)
    return [(f'Earn, bots split trades x{k} (naive per-trade fee)', dict(base=vf, gamma=1.0, split=k)) for k in [10, 50]] + \
           [('Earn, per-block size fee (immune to splitting)', dict(base=vf, gamma=1.0))]
