Each file here is one method. It must define `designs(ctx)` returning a list of `(design name, settings)`.
`ctx` has: P (prices), n, fund (funding), score (AI storm score), rv60 (1h realised variance, past only),
stale (price 1 minute old), pair, year. Settings are passed to `lab/engine.py: sim()`.
Add a new file + push -> GitHub runs it on all 16 pairs and updates results/SUMMARY.md.
