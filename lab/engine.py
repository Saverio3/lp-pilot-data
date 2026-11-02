"""Pool simulator (numba). One engine for every method; methods only choose the inputs.

sim(P, O, fund, base, alpha, beta, auction, capture, hedge, ratio, ...)
  P      CEX price each step (Binance close)
  O      price the pool's fee logic can see (oracle). O = P means a fast oracle; P shifted = stale.
  fund   perp funding rate paid by longs at each step (0 elsewhere)
  base   base fee per step (0.003 = 0.30%)
  alpha  gap fee: arb-direction trades pay alpha * |ln(O / pool price)| extra
  beta   inventory fee: trades pushing pool price further from its start pay beta * |ln(pool / start)| extra
  auction  CoW-style: arbitrage is auctioned, pool keeps `capture` of the profit
  hedge  0 none, 1 spot-first hedge (spot bought from 10% reserve, perp for the rest), 2 perp only
  ratio  hedge ratio per step (1 = full)
Returns (final vs HODL, worst moment vs HODL, funding paid / capital). Retail flow not modelled.
"""
import math
import numpy as np
from numba import njit


@njit(cache=True)
def _sim(P, O, fund, base, alpha, beta, auction, capture, hedge, ratio,
         gas, cex_fee, perp_fee, spot_fee, band, cap):
    n = len(P)
    f = 0.9 if hedge > 0 else 1.0
    P0 = P[0]; E0 = 0.5 * cap / P0
    x = f * cap / 2 / P0; y = f * cap / 2; x0 = x
    usd = cap - f * cap; eth = 0.0; h = 0.0
    worst = 0.0; funding = 0.0; V = cap; H = cap
    for i in range(n):
        p = P[i]
        if h != 0.0 and i > 0:
            usd += h * (p - P[i - 1])
            r = fund[i]
            if r != 0.0:
                usd -= h * p * r; funding += h * p * r
        k = x * y
        if auction:
            sk = math.sqrt(k * p); profit = x * p + y - 2 * sk; xn = sk / p
            c = gas + cex_fee * abs(x - xn) * p
            if profit > c:
                x = xn; y = sk + capture * (profit - c)
        else:
            pp = y / x
            fb = base[i]
            if pp < p * (1 - fb) or pp > p / (1 - fb):
                buy = pp < p
                extra = 0.0
                if alpha > 0.0:
                    gap = math.log(O[i] / pp)
                    if (gap > 0) == buy:
                        extra += alpha * abs(gap)
                if beta > 0.0:
                    away = (buy and pp >= P0) or ((not buy) and pp <= P0)
                    if away:
                        extra += beta * abs(math.log(pp / P0))
                fe = fb + extra
                if fe > 0.5:
                    fe = 0.5
                g1 = 1 - fe
                if pp < p * g1:
                    ye = math.sqrt(k * p * g1); dy = ye - y; xn = k / ye
                    if (x - xn) * p - dy / g1 > gas + cex_fee * (x - xn) * p:
                        y += dy / g1; x = xn
                elif pp > p / g1:
                    xe = math.sqrt(k * g1 / p); dx = xe - x; yn = k / xe
                    if (y - yn) - dx / g1 * p > gas + cex_fee * dx / g1 * p:
                        x += dx / g1; y = yn
        if hedge > 0:
            need = (E0 - x0) + ratio[i] * (x0 - x)
            if abs(need - (eth + h)) > band * E0:
                te = 0.0
                if hedge == 1 and need > 0:
                    te = min(need, max(0.0, (usd + eth * p) * 0.95 / p))
                de = te - eth
                usd -= de * p + abs(de) * p * spot_fee; eth = te
                dh = (need - eth) - h
                usd -= abs(dh) * p * perp_fee; h += dh
        V = x * p + y + usd + eth * p
        H = E0 * p + cap / 2
        rr = V / H - 1
        if rr < worst:
            worst = rr
    return V / H - 1, worst, funding / cap


def sim(P, O=None, fund=None, base=0.003, alpha=0.0, beta=0.0, auction=False, capture=0.8,
        hedge=0, ratio=1.0, gas=0.05, cex_fee=0.0002, perp_fee=0.0003, spot_fee=0.0005,
        band=0.02, cap=10e6):
    n = len(P)
    P = np.ascontiguousarray(P, dtype=np.float64)
    O = P if O is None else np.ascontiguousarray(O, dtype=np.float64)
    fund = np.zeros(n) if fund is None else np.ascontiguousarray(fund, dtype=np.float64)
    base = np.full(n, base) if np.isscalar(base) else np.ascontiguousarray(base, dtype=np.float64)
    ratio = np.full(n, float(ratio)) if np.isscalar(ratio) else np.ascontiguousarray(ratio, dtype=np.float64)
    return _sim(P, O, fund, base, float(alpha), float(beta), bool(auction), float(capture), int(hedge), ratio,
                gas, cex_fee, perp_fee, spot_fee, band, cap)
