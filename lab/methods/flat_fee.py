"""Same designs WITHOUT the volatility fee: flat 0.30% + per-block trade-size fee. The volatility fee raises the price for
normal traders in busy times; if they leave (strong reaction), it costs more than it earns. This keeps normal traders' fee
at Uniswap's level and only bots pay more."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from _tools import lowpass_price
def designs(c):
    P = c['P']; F = dict(base=0.003, gamma=1.0)
    shield = dict(F, hedge=1, Hp=lowpass_price(P, 10080), band=0.30)
    Pa, Ya = c['P_all'], c['yr_all']; start = np.argmax(Ya == c['year']); ra = np.diff(np.log(Pa[:start + 1]))
    out = [('FLAT Earn (0.30% + size fee)', dict(F)),
           ('FLAT Shield band 5% + low-pass 1d', dict(F, hedge=1, Hp=lowpass_price(P, 1440), band=0.05)),
           ('FLAT Band 30% + low-pass 7d', shield)]
    for L, nm in [(365, '365d'), (180, '180d'), (7, '7d')]:
        past = ra[-L * 1440:] if start > L * 1440 * 0.5 else np.array([])
        vol = np.std(past) * np.sqrt(525600) if len(past) else np.nan
        out.append((f'FLAT Per-pair rule (yearly, lookback {nm})', dict(F) if (not np.isnan(vol) and vol < 0.5) else shield))
    out.append(('FLAT size fee g=1.5', dict(base=0.003, gamma=1.5)))
    return out
