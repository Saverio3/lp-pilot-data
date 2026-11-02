"""From your list (shear-thickening / non-Newtonian fluid): fee rises sharply with how fast the price just moved.
Needs NO price feed (oracle-free): uses the pool's own recent move. Slow trades pay 0.30%, violent moves pay much more."""
import numpy as np
def designs(c):
    P = c['P']; r = np.abs(np.r_[0.0, np.diff(np.log(P))]); rp = np.r_[0.0, r[:-1]]  # last minute's move (known)
    s = np.median(rp[rp > 0]) + 1e-12
    out = []
    for k in [0.0005, 0.001]:
        out.append((f'Shear-thickening fee k={k}', dict(base=np.clip(0.003 + k * (rp / s) ** 2, 0.003, 0.05))))
    return out
