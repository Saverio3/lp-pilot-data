# Earn hook: an oracle-free bot fee for Uniswap v4 liquidity providers

[![hook-tests](https://github.com/Saverio3/lp-pilot-data/actions/workflows/hook-tests.yml/badge.svg)](https://github.com/Saverio3/lp-pilot-data/actions/workflows/hook-tests.yml)

Normal traders pay 0.30%. Trades that push the pool's price hard in one direction within a block (what arbitrage bots do)
pay extra. There is **no price feed**, and splitting a trade does not avoid the fee.

**Results** (16 pairs, Jan 2022 – Nov 2026, with normal traders at real Uniswap volumes):

| | Uniswap 0.30% | Earn hook |
|---|---|---|
| LP result vs holding, 5 years | +13.6% | **+19.1%** |
| Pairs beating Uniswap | – | **15 / 16** |
| 2-year deposits beating Uniswap | – | **97%** |

📄 **[Results report](results/REPORT.md)** · 📊 **[Excel workbook](results/LP_results.xlsx)** · 🔧 **[Hook code & tests](hook/)**

## Repository
| Folder | What |
|---|---|
| `hook/` | Uniswap v4 hook (`BlockImpactFeeHook.sol`), Foundry tests, Unichain Sepolia deploy script |
| `lab/` | Pool simulator (`engine.py`) and one file per tested design (`methods/`, about 150 designs) |
| `results/` | `REPORT.md`, `LP_results.xlsx`, `SUMMARY.md` (all designs), `HOLDING.md` (1–24 month deposits), `LATENCY.md` |
| `data/` | Binance 1-minute prices and funding (public data), real Uniswap pool data (The Graph) |
| `scripts/` | Data download robots |

## Automation (GitHub Actions)
| Workflow | Runs when | Does |
|---|---|---|
| `hook-tests` | hook code changes | compiles the hook and runs all tests |
| `lab` | a design file changes | tests new or changed designs on 16 pairs in parallel, updates results and the Excel file |
| `holding` | holding test changes | monthly deposits held 1/3/12/24 months |
| `latency` | latency test changes | price-feed delay test on 1-second data |
| `fetch-binance-data`, `fetch-uniswap` | manual / script changes | refresh the data |
| `deploy-testnet` | manual | deploys the hook and demo pools to Unichain Sepolia (needs secret `TESTNET_PRIVATE_KEY`, a testnet-only wallet) |

Add a design: create `lab/methods/my_idea.py` with `designs(ctx)` and push. Only new or changed designs are re-run.

Simulation results, not financial advice. The hook is unaudited; testnet only.
