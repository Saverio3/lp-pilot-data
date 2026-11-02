"""Physics-style 'temperature' fee without AI: fee scales with the last hour's realised volatility.
Checks whether the AI adds anything over a simple rule."""
import numpy as np
def designs(c):
    v = np.sqrt(c['rv60']); m = np.median(v)
    return [('Volatility-scaled fee (no AI)', dict(base=np.clip(0.003 * v / m, 0.003, 0.03)))]
