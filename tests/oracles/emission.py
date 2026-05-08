# Moire — Python reference for the block-reward formula.
#
# Constitution Article II:
#   For n < N_trans:  R(n) = k · A(B_n) · exp(-λ·n)
#   For n ≥ N_trans:  R(n) = k · grad_H(ΔC_n) · exp(-λ·n)
#
# Genesis pin: k = 7.48e12 attomoire/block, λ ≈ 3.5622e-7 per block.
# Asymptotic cap: 21 M MOI = 2.1e19 attomoire.
#
# Used by tests/invariants/test_block_reward.py and test_hard_cap.py.

from __future__ import annotations

import math
from dataclasses import dataclass


# Genesis constants — pinned by genesis/params.toml.
K_ATOMIC_PER_BLOCK = 7_480_000_000_000          # k
LAMBDA_PER_BLOCK = 3.5622e-7                    # λ
ASYMPTOTIC_CAP_ATOMIC = 21_000_000_000_000_000_000  # S(∞) in attomoire


@dataclass(frozen=True)
class EmissionParams:
    k: int = K_ATOMIC_PER_BLOCK
    lam: float = LAMBDA_PER_BLOCK
    cap: int = ASYMPTOTIC_CAP_ATOMIC


def envelope(n: int, p: EmissionParams = EmissionParams()) -> float:
    """exp(-λ·n). Strictly decreasing in n for λ > 0."""
    return math.exp(-p.lam * n)


def reward_atomic(n: int,
                  pivot: float,
                  p: EmissionParams = EmissionParams()) -> int:
    """R(n) in attomoire. `pivot` is A(B_n) before transition, grad_H after.

    Both pivots are constitutionally bounded in [0, 1] for the issuance bound
    to hold (Article III caps A; Article VII bounds grad_H by θ·A pre-transition,
    and Article IV caps the post-transition grad_H by 1.0 via the entropy floor).
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    pivot_clamped = max(0.0, min(1.0, float(pivot)))
    r = float(p.k) * pivot_clamped * envelope(n, p)
    # Truncate (floor) to integer attomoire — block reward must be integral.
    return int(r)


def cumulative_supply_closed_form(n: int,
                                  avg_pivot: float = 1.0,
                                  p: EmissionParams = EmissionParams()) -> float:
    """Closed-form S(N) = k·avg_pivot · (1 - exp(-λ·N)) / λ.

    Real chain S(N) = sum_{i=0..N-1} reward_atomic(i, A(B_i)). The closed form is
    the upper envelope at avg_pivot=1 and is what the asymptotic-cap proof
    relies on.
    """
    if n <= 0:
        return 0.0
    return float(p.k) * avg_pivot * (1.0 - math.exp(-p.lam * n)) / p.lam


def cumulative_supply_summed(n: int,
                             pivots: list[float] | None = None,
                             p: EmissionParams = EmissionParams()) -> int:
    """Discrete sum of integer rewards. If pivots is None, defaults to all-1.0
    (worst-case upper envelope)."""
    if pivots is None:
        return sum(reward_atomic(i, 1.0, p) for i in range(n))
    if len(pivots) != n:
        raise ValueError(f"pivots length {len(pivots)} != n {n}")
    return sum(reward_atomic(i, pivots[i], p) for i in range(n))
