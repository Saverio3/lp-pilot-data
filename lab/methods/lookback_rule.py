"""Earn/Shield rule with different volatility lookbacks. Shield = band 30% + 7-day smoothing; Earn = fee only.
'yearly' = decided once at the start of the year from the last L days; 'daily' = re-decided every day from the last L days.
Threshold: annualised volatility 50%."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from _tools import lowpass_price
def designs(c):
    P = c['P']; n = len(P); v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03); F = dict(base=vf, gamma=1.0)
    Hp = lowpass_price(P, 10080); shield = dict(F, hedge=1, Hp=Hp, band=0.30)
    Pa, Ya = c['P_all'], c['yr_all']; start = np.argmax(Ya == c['year'])
    ra = np.r_[0.0, np.diff(np.log(Pa))]
    out = []
    for L, nm in [(1, '1d'), (7, '7d'), (30, '30d'), (60, '60d'), (90, '90d'), (180, '180d'), (365, '365d')]:
        w = L * 1440
        # yearly decision
        past = ra[max(0, start - w):start]
        vol = np.std(past) * np.sqrt(525600) if len(past) > 0.5 * w else np.nan
        kw = shield if (np.isnan(vol) or vol >= 0.5) else dict(F)
        out.append((f'Rule yearly, lookback {nm}', kw))
        # daily decision (switches inside the year)
        rv = pd.Series(ra ** 2).rolling(w, min_periods=max(60, w // 2)).mean().shift(1)
        dv = np.sqrt(rv.values[start:start + n] * 525600)
        day = np.arange(n) // 1440; first = np.r_[0, np.where(np.diff(day))[0] + 1]
        dvd = dv[first][day]  # value known at the start of each day
        ratio = np.where(np.isnan(dvd) | (dvd >= 0.5), 1.0, 0.0)
        out.append((f'Rule daily, lookback {nm}', dict(shield, ratio=ratio)))
    return out
