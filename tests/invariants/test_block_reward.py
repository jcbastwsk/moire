"""Invariant 1 — block reward formula.

Constitution Article II:
  R(n) = k · pivot · exp(-λ·n),
  pivot = A(B_n) for n < N_trans, grad_H(ΔC_n) for n >= N_trans.

We assert:
  (a) R is monotonically non-increasing in n at fixed pivot ≥ 0.
  (b) R(0) at pivot=1 is exactly k (truncated to int).
  (c) Numeric agreement with the closed-form within 1 attomoire on a corpus.
  (d) Pivot clamping: out-of-range pivots are saturated, not rejected
      (defense-in-depth against oracle bugs).
"""

from __future__ import annotations

import math

from hypothesis import given, settings, strategies as st

from tests.oracles.emission import (
    EmissionParams,
    K_ATOMIC_PER_BLOCK,
    LAMBDA_PER_BLOCK,
    envelope,
    reward_atomic,
)


def test_reward_at_zero_with_unit_pivot_equals_k():
    p = EmissionParams()
    assert reward_atomic(0, 1.0, p) == K_ATOMIC_PER_BLOCK


def test_envelope_strict_monotone_decreasing():
    p = EmissionParams()
    prev = envelope(0, p)
    for n in [1, 10, 1_000, 100_000, 1_000_000, 8_409_600]:
        cur = envelope(n, p)
        assert cur < prev, f"envelope not strictly decreasing at n={n}"
        prev = cur


@given(
    n=st.integers(min_value=0, max_value=10_000_000),
    pivot=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300, deadline=None)
def test_reward_matches_closed_form_within_one_attomoire(n: int, pivot: float):
    p = EmissionParams()
    expected = float(p.k) * pivot * math.exp(-p.lam * n)
    got = reward_atomic(n, pivot, p)
    assert abs(got - expected) <= 1.0


@given(pivot=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=50, deadline=None)
def test_reward_monotone_in_n_at_fixed_pivot(pivot: float):
    p = EmissionParams()
    a = reward_atomic(0, pivot, p)
    b = reward_atomic(1, pivot, p)
    c = reward_atomic(100, pivot, p)
    d = reward_atomic(8_409_600, pivot, p)  # year 16
    assert a >= b >= c >= d


def test_reward_clamps_pivot_above_one():
    p = EmissionParams()
    a = reward_atomic(0, 1.0, p)
    b = reward_atomic(0, 1.5, p)  # above 1.0 — must saturate
    assert a == b == K_ATOMIC_PER_BLOCK


def test_reward_clamps_pivot_below_zero():
    p = EmissionParams()
    assert reward_atomic(0, -0.1, p) == 0


def test_year16_milestone_within_5pct_of_05_factor():
    """Article II commitment: λ tuned so 95% of cap is minted by year 16.
    Equivalently, envelope at year-16 should be ~0.05 (so 1-0.05 = 95% if
    avg pivot is 1)."""
    p = EmissionParams()
    e = envelope(8_409_600, p)
    assert 0.04 < e < 0.06, f"year-16 envelope = {e:.4f}"
