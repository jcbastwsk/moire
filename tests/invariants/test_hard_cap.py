"""Invariant 3 — hard cap bound.

Constitution Article II: cumulative supply S(N) is bounded above by S(∞) = k/λ
when avg pivot ≤ 1.

Properties:
  (a) Closed-form S(∞) = k/λ ≤ asymptotic_cap (within rounding).
  (b) S(N) is monotone non-decreasing in N.
  (c) For all finite N, S(N) ≤ S(∞).
  (d) Discrete summed supply (integer attomoire) ≤ closed-form upper envelope.
  (e) 95%-by-year-16 commitment: |S(N16)/S(∞) - 0.95| ≤ 0.01.

This is the digital-gold scarcity contract.
"""

from __future__ import annotations

import math

from hypothesis import given, settings, strategies as st

from tests.oracles.emission import (
    ASYMPTOTIC_CAP_ATOMIC,
    EmissionParams,
    K_ATOMIC_PER_BLOCK,
    LAMBDA_PER_BLOCK,
    cumulative_supply_closed_form,
    cumulative_supply_summed,
    envelope,
)


YEAR_16_BLOCKS = 8_409_600  # canonical: 16 * 365 * 1440 (no leap days)


def test_asymptotic_cap_is_exactly_21M_MOI():
    s_inf = K_ATOMIC_PER_BLOCK / LAMBDA_PER_BLOCK
    # Genesis derivation pins S(∞) ≈ 2.1e19 attomoire = 21 M MOI.
    rel_err = abs(s_inf - ASYMPTOTIC_CAP_ATOMIC) / ASYMPTOTIC_CAP_ATOMIC
    assert rel_err < 1e-3, f"S(∞)={s_inf:.6e}, cap={ASYMPTOTIC_CAP_ATOMIC:.6e}, rel_err={rel_err:.3e}"


def test_supply_monotone_non_decreasing():
    p = EmissionParams()
    prev = 0.0
    for n in [0, 1, 100, 10_000, 1_000_000, YEAR_16_BLOCKS, 50_000_000]:
        cur = cumulative_supply_closed_form(n, 1.0, p)
        assert cur >= prev, f"S({n}) < S(prev)"
        prev = cur


@given(n=st.integers(min_value=0, max_value=10**9),
       avg_pivot=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=200, deadline=None)
def test_supply_below_cap_for_all_finite_n(n: int, avg_pivot: float):
    p = EmissionParams()
    s = cumulative_supply_closed_form(n, avg_pivot, p)
    cap = K_ATOMIC_PER_BLOCK * avg_pivot / LAMBDA_PER_BLOCK
    # S(n) is strictly less than k·avg/λ for any finite n (because (1-e^-λn) < 1).
    assert s <= cap + 1e-3


def test_year16_within_one_percent_of_95pct_cap():
    p = EmissionParams()
    s = cumulative_supply_closed_form(YEAR_16_BLOCKS, 1.0, p)
    s_inf = K_ATOMIC_PER_BLOCK / LAMBDA_PER_BLOCK
    frac = s / s_inf
    assert 0.94 <= frac <= 0.96, f"S(N16)/S(∞) = {frac:.4f}"


def test_discrete_sum_bounded_by_geometric_partial_sum():
    """Discrete reward emission is a left-Riemann sum that exceeds the
    continuous integral. The correct upper envelope is the geometric partial
    sum k·(1-exp(-λN))/(1-exp(-λ)). We assert the integer-truncated
    cumulative supply is at or below that envelope.

    NOTE — this surfaces a small constitution-math discrepancy:
    S(∞) discrete = k/(1-exp(-λ)) > k/λ by factor 1/(1-λ/2). At λ=3.5622e-7
    the relative overshoot is ~1.78e-7 (≈3.74 MOI on a 21 M cap).
    Recommended action: re-solve λ to satisfy the DISCRETE cap, or
    explicitly redefine S(∞) := k/(1-exp(-λ)) in the constitution.
    Logged in BUILD_LOG Day-2 entry.
    """
    p = EmissionParams()
    N = 10_000
    summed = cumulative_supply_summed(N, None, p)
    geometric = float(p.k) * (1.0 - math.exp(-p.lam * N)) / (1.0 - math.exp(-p.lam))
    # Truncation lops at most 1 attomoire per block.
    assert summed <= geometric + 1.0
    # Also: discrete > continuous integral form, by ~1/(1-λ/2).
    closed = cumulative_supply_closed_form(N, 1.0, p)
    assert summed > closed


def test_envelope_integral_matches_closed_form_within_1pct():
    """∫₀^N k·exp(-λn) dn = (k/λ)(1 - exp(-λN)). Integral form is within
    factor (1-exp(-λ))/λ ≈ 1 - λ/2 of the discrete sum over N=10k blocks.
    The relative gap is bounded by λ ≈ 3.6e-7, so well below 1%."""
    p = EmissionParams()
    N = 10_000
    integral = (p.k / p.lam) * (1.0 - math.exp(-p.lam * N))
    summed = cumulative_supply_summed(N, None, p)
    rel = abs(integral - summed) / integral
    assert rel < 0.01, f"rel diff {rel:.4f} between integral and sum"


def test_discrete_asymptotic_cap_overshoot_documented():
    """Discrete S(∞) = k/(1-exp(-λ)) overshoots the integral S(∞)=k/λ
    by relative factor 1/(1-λ/2). At genesis λ this is ~1.78e-7 (~3.74 MOI).
    Pinning the magnitude here so any λ change keeps overshoot < 1e-5
    relative — safety margin for mainnet."""
    p = EmissionParams()
    cap_integral = float(p.k) / p.lam
    cap_discrete = float(p.k) / (1.0 - math.exp(-p.lam))
    rel_overshoot = (cap_discrete - cap_integral) / cap_integral
    assert 0 < rel_overshoot < 1e-5


def test_cap_immune_to_pivot_above_one():
    """Pivot saturation in reward_atomic guarantees no inflation via oracle bug."""
    p = EmissionParams()
    # cumulative_supply_summed defaults pivots=None -> 1.0 -> cap saturates.
    s_unit = cumulative_supply_summed(100_000, None, p)
    # If we manually inject pivots above 1, the saturated reward path means
    # supply does not exceed unit-pivot supply.
    pivots_hot = [1.5] * 100_000  # supplied pivots saturated to 1.0 inside
    s_hot = cumulative_supply_summed(100_000, pivots_hot, p)
    assert s_hot == s_unit
