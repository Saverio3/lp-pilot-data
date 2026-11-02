"""Gap fee + crash-shield hedge (spot-first): fee recaptures bot profit, hedge removes price-direction loss."""
def designs(c):
    out = []
    for r, nm in [(1.0, 'full'), (0.5, 'half'), (0.25, 'quarter')]:
        out.append((f'Gap fee 0.9 fast + {nm} hedge', dict(base=0.003, alpha=0.9, hedge=1, ratio=r)))
    out.append(('Gap fee 0.9 stale + full hedge', dict(base=0.003, alpha=0.9, O=c['stale'], hedge=1, ratio=1.0)))
    out.append(('Gap fee 0.9 stale + half hedge', dict(base=0.003, alpha=0.9, O=c['stale'], hedge=1, ratio=0.5)))
    return out
