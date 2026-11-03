# Earn hook: an oracle-free, split-proof bot fee for Uniswap v4 LPs

**Summary.** Liquidity providers (LPs) lose money to arbitrage bots, which trade against a pool every time its price is out
of date. We tested about 150 pool designs on 5 years of minute-level data for 16 trading pairs, including the newest
2026 research designs, and built the best simple one as a Uniswap v4 hook. Normal traders pay the usual 0.30%. Trades
that push the pool's price hard in one direction **within a block** (what bots do) pay extra, in proportion to how far
the block has moved the pool. The hook needs **no price feed**, and **splitting a trade into pieces does not lower
the fee** (proven in tests).

| 16 pairs, Jan 2022 – Nov 2026, LP result vs just holding | Uniswap 0.30% | **Earn hook** |
|---|---|---|
| 5-year result, with normal traders at real Uniswap volumes | +13.6% | **+19.1%** |
| 5-year result, bots only (the pure "leak") | -11.8% | **-5.8%** (about half the leak removed) |
| Pairs where it beats Uniswap | – | **15 of 16** |
| Monthly deposits held 2 years that beat Uniswap | – | **97%** (560 deposits) |
| Monthly deposits held 1 year that beat Uniswap | – | **89%** (752 deposits) |

## 1. The problem
When the Binance price moves, a pool's price is briefly stale. Arbitrage bots buy the cheap side, and that profit comes
out of LPs' pockets (known as loss-versus-rebalancing, LVR). A flat fee cannot tell a bot from a normal trader. So
either everyone pays more (normal traders leave) or bots pay too little.

## 2. The design
* **Base fee:** 0.30% for every swap, the same as a standard Uniswap pool.
* **Block-impact fee:** each block, the hook tracks the pool's net one-directional flow as a fraction of its depth.
  A swap that pushes that flow further pays `fee = 0.30% + γ × (|flow before| + |flow after|)`, capped at 10%.
  * One swap moving the pool by 1% pays 0.30% + 1%. A normal trade (0.001% of the pool) pays 0.301%.
  * Swaps that **reduce** the block's imbalance pay only 0.30%, so normal traders going the other way are untouched.
  * The `before + after` rule makes the total fee the same for one big swap or many small ones in the same block.
    A naive per-trade size fee loses almost half of its benefit to this splitting attack in our simulation.
* **Oracle-free:** it uses only the pool's own price and liquidity, so there is no price feed to manipulate or delay.

## 3. How it was tested
* **Data:** Binance public 1-minute prices and perpetual funding, Jan 2022 – Nov 2026. The 16 pairs are BTC, ETH, SOL, XRP, BNB, DOGE, ADA, TRX, LINK and AVAX against USD, plus BTC/ETH, SOL/ETH, LINK/ETH, BNB/ETH, BTC/BNB and XRP/BTC.
  Real Uniswap v3 pool volumes and fees come from The Graph: 76 pools on Ethereum, Arbitrum and Base.
* **Simulator:** a $10M pool. Bots trade whenever it is profitable after 2bp exchange cost and $0.05 gas.
  * Normal traders = 50% of the real Uniswap 0.30%-pool volume for each pair.
  * Their volume falls with the square of any fee increase, a strong reaction (aggregators route away).
* **Safety check:** a design is rejected if the pool's price drifts more than 1% from the market for over 2% of the time,
  because real traders would avoid such a pool. Several "winning" designs failed this check.
* **Everything is reproducible:** each design is one file in `lab/methods/`. GitHub Actions re-runs all 16 pairs on every
  change and rebuilds `results/SUMMARY.md`, `results/HOLDING.md` and `results/LP_results.xlsx`.

## 4. Results against existing and new designs
| Design (5-year result, with normal traders) | Avg of 16 pairs | Beats Uniswap |
|---|---|---|
| Uniswap 0.30% | +13.6% | – |
| Volatility-based fee (as in current vol-fee hooks) | +9.6% | 0/16 |
| Variance-feedback "optimal" fee (arXiv 2606.21769, Jun 2026) | +9.0% | 0/16 |
| CoW-style batch auction (80% of bot profit returned) | +14.9% | 9/16 |
| Partially Active AMM (arXiv 2602.09887, Feb 2026) | +15.3% | 16/16 |
| **Earn hook** | **+19.1%** | **15/16** |

Fees that rise with volatility charge **everyone** more in busy markets. Normal traders leave, so these designs end
below Uniswap. Earn charges only one-directional flow, so normal traders keep paying 0.30%.

## 5. Robustness
* **Holding period:** deposits starting every month since 2022, held 1, 3, 12 and 24 months. Earn beat Uniswap in **70%, 78%,
  89% and 97%** of them; the median 2-year result was +14.2% vs +12.6%.
* **Trader reaction:** with a mild reaction, Earn's lead grows (+56.9% vs +47.7% at a 10%/day volume assumption). With fewer
  normal traders (30% of volume), Earn is still ahead (+8.6% vs +2.8%).
* **Price-feed delay:** not applicable. Earn uses no feed. (Oracle-based gap fees were also tested on 1-second data.)
* **Hook tests (Foundry, 11 tests incl. 256-run fuzzing):**
  * small trade ≈ 0.30%;
  * a 1%-of-pool trade pays 1.30%;
  * 10 split swaps pay the same total fee as one big swap (within 2%) and get no better price;
  * the fee resets every block;
  * trades against the flow pay only 0.30%;
  * the cap is respected.

## 6. What did not work (so others need not repeat it)
* **AI timing** did not beat simple rules: an ML storm predictor, a mode switcher, a reinforcement-learning bandit, RSI and Stochastic RSI.
* **Options and variance-swap insurance** costs about what it pays out at fair prices, and is worse with market markups.
* **Oracle "gap" fees** with strong capture left the pool more than 1% off market 75% of the time (unusable).
* **Trade-size fees at γ ≥ 2** froze the pool.
* **Volatility- and variance-scaled fees** lost to Uniswap once normal traders react to fees.

## 7. Limitations
* This is a simulation, not live trading. The bot/normal-trader split of real volume and the fee reaction are modelled.
* The pools are full range. With concentrated liquidity the hook measures local depth, which needs its own testing.
* The hook is unaudited and testnet only.

## 8. Next milestones
1. **Testnet:** deploy to Unichain Sepolia (`deploy-testnet` workflow) with a hooked pool and a plain 0.30% pool side by side,
   plus a public comparison dashboard.
2. **Security:** an independent review and audit, and more tests for concentrated liquidity and multi-hop routes.
3. **Mainnet pilot:** one small pool on Unichain, with live tracking against a standard pool.
4. **Optional LP vault** (Balanced / Shield settings): adds a slow, trend-only hedge for volatile pairs. In simulation this
   reached +29.6% with no pair ending negative (Balanced) and a worst 1-year result of -0.5% at the 5th percentile (Shield).
