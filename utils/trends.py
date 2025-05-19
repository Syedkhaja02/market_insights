from __future__ import annotations
from typing import Tuple
import math

def pct_delta(new: float, old: float) -> Tuple[str, float]:
    """Return Unicode arrow ↑/↓/→ and delta %% (rounded)."""
    if old == 0 or math.isnan(old):
        return "→", 0.0
    delta = (new - old) / old * 100
    arrow = "↑" if delta > 0.5 else "↓" if delta < -0.5 else "→"
    return arrow, round(delta, 1)