"""Optimal-control idea (Baggiani et al. 2025: fees linear in inventory): trades pushing the pool further from
its starting price pay extra. Tested alone and on top of the gap fee."""
def designs(c):
    return [('Inventory fee b=0.05', dict(base=0.003, beta=0.05)),
            ('Inventory fee b=0.15', dict(base=0.003, beta=0.15)),
            ('Gap fee 0.9 fast + inventory b=0.05', dict(base=0.003, alpha=0.9, beta=0.05))]
