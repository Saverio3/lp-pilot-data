"""Early-warning gap fee: arbitrage-direction trades pay alpha x the gap between the Binance price and the pool price.
fast = oracle sees this minute's price; stale = 1 minute old."""
def designs(c):
    out = []
    for a in [0.5, 0.75, 0.9]:
        out.append((f'Gap fee a={a} fast', dict(base=0.003, alpha=a)))
        out.append((f'Gap fee a={a} stale', dict(base=0.003, alpha=a, O=c['stale'])))
    return out
