"""(1) RSI / Stochastic RSI as the switch: strong momentum (RSI far from 50) = trending -> hedge; middle = ranging -> no hedge.
(2) Per-pair rule known in advance: if the pair's volatility over the PREVIOUS 365 days is low (pairs that move together),
use Earn (fee only); otherwise use the best Shield (band 30% + 7-day smoothing). Same usable oracle-free fee throughout."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
from _tools import lowpass_price


def rsi(close, n=14):
    d = close.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / (dn + 1e-12))


def designs(c):
    P = c['P']; n = len(P); v = np.sqrt(c['rv60']); vf = np.clip(0.003 * v / np.median(v), 0.003, 0.03); F = dict(base=vf, gamma=1.0)
    Hp7 = lowpass_price(P, 10080); Hp1 = lowpass_price(P, 1440)
    # daily RSI from the year's own past (first 14 days neutral), applied the NEXT day (no look-ahead)
    s = pd.Series(P); day = np.arange(n) // 1440
    dc = s.groupby(day).last(); r = rsi(dc).shift(1).fillna(50.0)
    lo, hi = dc.rolling(14, min_periods=1).min(), dc.rolling(14, min_periods=1).max()
    srsi = ((rsi(dc) - rsi(dc).rolling(14, min_periods=1).min()) / (rsi(dc).rolling(14, min_periods=1).max() - rsi(dc).rolling(14, min_periods=1).min() + 1e-12)).shift(1).fillna(0.5)
    rm = r.values[day]; sm = srsi.values[day]
    trend_rsi = ((rm > 65) | (rm < 35)).astype(float)
    trend_srsi = ((sm > 0.8) | (sm < 0.2)).astype(float)
    out = [('RSI switch: hedge when RSI>65 or <35', dict(F, hedge=1, Hp=Hp1, band=0.05, ratio=np.maximum(trend_rsi, 0.25))),
           ('RSI switch + band 30% 7d', dict(F, hedge=1, Hp=Hp7, band=0.30, ratio=np.maximum(trend_rsi, 0.25))),
           ('Stochastic RSI switch: hedge when >0.8 or <0.2', dict(F, hedge=1, Hp=Hp1, band=0.05, ratio=np.maximum(trend_srsi, 0.25))),
           ('RSI strength-scaled hedge', dict(F, hedge=1, Hp=Hp1, band=0.05, ratio=np.clip(np.abs(rm - 50) / 25, 0.0, 1.0)))]
    # per-pair rule: trailing 365-day volatility of this pair, measured BEFORE this year starts
    Pa, Ya = c['P_all'], c['yr_all']; prev = Pa[Ya < c['year']][-525600:]
    pv = np.std(np.diff(np.log(prev))) * np.sqrt(525600) if len(prev) > 100000 else np.nan
    for thr in [0.5, 0.6]:
        if np.isnan(pv) or pv < thr:   # no history (first year) -> treat as unknown -> Earn only if measured low; first year uses Shield
            kw = dict(F) if not np.isnan(pv) else dict(F, hedge=1, Hp=Hp7, band=0.30)
        else:
            kw = dict(F, hedge=1, Hp=Hp7, band=0.30)
        out.append((f'Per-pair rule: Earn if last-year vol < {thr:.0%}, else Shield band30 7d', kw))
    return out
