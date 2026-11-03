"""Brand-new 2026 papers, tested on our data:
- Partially Active AMM (Ko, Feb 2026, arXiv 2602.09887): only a fraction lambda of reserves is exposed to each block,
  so bots can take less per block; the rest re-joins after. Tested alone and with our per-block size fee.
- Optimal dynamic fee as variance feedback (Ghasemlu, Jun 2026, arXiv 2606.21769): fee rises with instantaneous
  VARIANCE (not volatility), with a dead-band. Tested alone and with the size fee."""
import numpy as np
def designs(c):
    rv = c['rv60']; m = np.median(rv)
    vfee = np.clip(0.003 * (1 + np.maximum(rv / m - 1.5, 0.0)), 0.003, 0.03)   # dead-band: only above 1.5x normal variance
    out = []
    for lam in [0.5, 0.25]:
        out.append((f'Partially active AMM lambda={lam}', dict(base=0.003, lam=lam)))
        out.append((f'Partially active AMM lambda={lam} + size fee', dict(base=0.003, gamma=1.0, lam=lam)))
    out.append(('Variance-feedback fee (2026 optimal fee)', dict(base=vfee)))
    out.append(('Variance-feedback fee + size fee', dict(base=vfee, gamma=1.0)))
    return out
