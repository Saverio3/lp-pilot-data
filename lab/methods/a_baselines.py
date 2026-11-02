"""What exists today: Uniswap fixed fee, CoW-style auction, hedged-LP vault."""
def designs(c):
    return [('Uniswap 0.30%', dict(base=0.003)),
            ('CoW-style auction 80%', dict(auction=True, capture=0.8)),
            ('Hedged vault (0.30% + perp)', dict(base=0.003, hedge=2))]
