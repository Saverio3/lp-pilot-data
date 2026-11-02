"""Shared helpers for method files (files starting with _ are not run as methods). All past-only."""
import math
import numpy as np
from numba import njit


@njit(cache=True)
def ema(x, halflife):
    a = 1 - 0.5 ** (1.0 / halflife); out = np.empty_like(x); acc = x[0]
    for i in range(len(x)):
        out[i] = acc            # value known BEFORE step i (past-only)
        acc = (1 - a) * acc + a * x[i]
    return out


@njit(cache=True)
def garch(r, a, b):
    """GARCH(1,1) filter on 1-minute returns: s2 = w + a*r^2 + b*s2, with w tied to the running average variance.
    Returns the forecast standard deviation for each minute using only earlier returns."""
    n = len(r); out = np.empty(n); s2 = 1e-6; cum = 0.0
    for i in range(n):
        out[i] = math.sqrt(s2)
        cum += r[i] * r[i]; vbar = cum / (i + 1)
        s2 = (1 - a - b) * vbar + a * r[i] * r[i] + b * s2
    return out


def lowpass_price(P, halflife_min):
    """Fourier-style low-pass filter of the price (causal EMA on log price): keeps slow trend, drops fast wiggles."""
    return np.exp(ema(np.log(P), float(halflife_min)))


def variance_ratio(P, window=43200, short=60, long=1440):
    """Fractal persistence test (Lo-MacKinlay variance ratio ~ Hurst): >1 trending ('leans one way'), <1 bouncing.
    Rolling 30-day window, past-only."""
    import pandas as pd
    lp = pd.Series(np.log(P))
    rs = lp.diff(short); rl = lp.diff(long)
    vr = rl.pow(2).rolling(window, min_periods=4320).mean() / (long / short * rs.pow(2).rolling(window, min_periods=4320).mean())
    return vr.shift(1).fillna(1.0).values
