"""Pool simulator (numba). One engine for every method; methods only choose the inputs.

sim(P, O, fund, base, alpha, beta, auction, capture, hedge, ratio, ...)
  P      CEX price each step (Binance close)
  O      price the pool's fee logic can see (oracle). O = P means a fast oracle; P shifted = stale.
  fund   perp funding rate paid by longs at each step (0 elsewhere)
  base   base fee per step (0.003 = 0.30%)
  alpha  gap fee: arb-direction trades pay alpha * |ln(O / pool price)| extra
  beta   inventory fee: trades pushing pool price further from its start pay beta * |ln(pool / start)| extra
  auction  CoW-style: arbitrage is auctioned, pool keeps `capture` of the profit
  decay  Dutch-auction gap fee: the extra gap fee falls to zero over `decay` steps while the pool stays off-market,
         so the pool always catches up (0 = off)
  gamma  trade-size fee (oracle-free, Ledrov et al. 2026 style): extra fee = gamma * trade size / pool reserve
  hedge  0 none, 1 spot-first hedge (spot bought from 10% reserve, perp for the rest), 2 perp only,
         3 CPPI hedge: hedge ratio = 1 - clip(m * (current LP-vs-HODL - floor)), i.e. hedge only as losses near the floor
  band   no-trade band for the hedge (fraction of initial token amount)
  ratio  hedge ratio per step (1 = full)
  Hp     price the hedge is computed from (default P). A smoothed price = hedge the trend, ignore wiggles.
Returns (final vs HODL, worst moment vs HODL, funding paid / capital, average pool-vs-market price gap,
share of time the pool price is >1% off market). A pool far off the market would lose its normal traders. Retail flow not modelled.
"""
import math
import numpy as np
from numba import njit

# Bump ONLY when existing features change meaning (forces every method to re-run). Adding new options does not.
ENGINE_VERSION = "3"  # 2: pool-price drift metrics; 3: re-run all so every design has them


@njit(cache=True)
def _sim(P, O, fund, base, alpha, beta, auction, capture, hedge, ratio, Hp, gamma, floor, m, decay,
         gas, cex_fee, perp_fee, spot_fee, band, cap):
    n = len(P)
    f = 0.9 if hedge > 0 else 1.0
    P0 = P[0]; E0 = 0.5 * cap / P0
    x = f * cap / 2 / P0; y = f * cap / 2; x0 = x
    usd = cap - f * cap; eth = 0.0; h = 0.0
    worst = 0.0; funding = 0.0; V = cap; H = cap
    gsum = 0.0; goff = 0; age = 0
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
                        a_eff = alpha
                        if decay > 0.0:
                            a_eff = alpha * max(0.0, 1.0 - age / decay)
                        extra += a_eff * abs(gap)
                if beta > 0.0:
                    away = (buy and pp >= P0) or ((not buy) and pp <= P0)
                    if away:
                        extra += beta * abs(math.log(pp / P0))
                fe = fb + extra
                if fe > 0.5:
                    fe = 0.5
                if gamma > 0.0:  # trade-size fee: estimate the arb's trade size at the current fee, charge for it
                    g0 = 1 - fe
                    if buy:
                        ye0 = math.sqrt(k * p * g0); sz = (x - k / ye0) / x
                    else:
                        xe0 = math.sqrt(k * g0 / p); sz = (xe0 - x) / x
                    if sz > 0:
                        fe += gamma * sz
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
            xh = x * math.sqrt(p / Hp[i])  # pool inventory if the price were Hp (CPMM: x ~ 1/sqrt(p))
            rt = ratio[i]
            if hedge == 3:  # CPPI: unhedged share grows with the cushion above the floor
                rel = (x * p + y + usd + eth * p + h * 0.0) / (E0 * p + cap / 2) - 1
                cush = (rel - floor) * m
                if cush < 0.0:
                    cush = 0.0
                if cush > 1.0:
                    cush = 1.0
                rt = ratio[i] * (1.0 - cush)
            need = (E0 - x0) + rt * (x0 - xh)
            if abs(need - (eth + h)) > band * E0:
                te = 0.0
                if hedge != 2 and need > 0:
                    te = min(need, max(0.0, (usd + eth * p) * 0.95 / p))
                de = te - eth
                usd -= de * p + abs(de) * p * spot_fee; eth = te
                dh = (need - eth) - h
                usd -= abs(dh) * p * perp_fee; h += dh
        dg = abs(math.log((y / x) / p))   # how far the pool's price is from the market after this step
        gsum += dg
        if dg > base[i] + 0.001:
            age += 1
        else:
            age = 0
        if dg > 0.01:
            goff += 1
        V = x * p + y + usd + eth * p
        H = E0 * p + cap / 2
        rr = V / H - 1
        if rr < worst:
            worst = rr
    return V / H - 1, worst, funding / cap, gsum / n, goff / n


def sim(P, O=None, fund=None, base=0.003, alpha=0.0, beta=0.0, auction=False, capture=0.8,
        hedge=0, ratio=1.0, Hp=None, gamma=0.0, floor=-0.02, m=20.0, decay=0.0, gas=0.05, cex_fee=0.0002, perp_fee=0.0003, spot_fee=0.0005,
        band=0.02, cap=10e6):
    n = len(P)
    P = np.ascontiguousarray(P, dtype=np.float64)
    O = P if O is None else np.ascontiguousarray(O, dtype=np.float64)
    fund = np.zeros(n) if fund is None else np.ascontiguousarray(fund, dtype=np.float64)
    base = np.full(n, base) if np.isscalar(base) else np.ascontiguousarray(base, dtype=np.float64)
    ratio = np.full(n, float(ratio)) if np.isscalar(ratio) else np.ascontiguousarray(ratio, dtype=np.float64)
    Hp = P if Hp is None else np.ascontiguousarray(Hp, dtype=np.float64)
    return _sim(P, O, fund, base, float(alpha), float(beta), bool(auction), float(capture), int(hedge), ratio, Hp,
                float(gamma), float(floor), float(m), float(decay), gas, cex_fee, perp_fee, spot_fee, band, cap)
