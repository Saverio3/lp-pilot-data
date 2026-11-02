# LP pilot data
Free Binance public data (data.binance.vision): 1-minute spot closes + volume and futures funding rates for 10 large coins, 2022 to today. Fetched by GitHub Actions (`.github/workflows/fetch.yml`).

## Lab (pool design tests)
- `lab/methods/` — one file per method. Add a file and push: GitHub runs it on 16 pairs in parallel (workflow `lab`) and writes `results/SUMMARY.md`.
- `lab/latency.py` — price-feed delay test on 1-second data (workflow `latency`) → `results/LATENCY.md`.
- `lab/engine.py` — the shared pool simulator.
