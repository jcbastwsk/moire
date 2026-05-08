"""Invariant 2 — transition_predicate monotonicity.

Constitution Article VII: N_trans fires when avg(grad_H) > θ · avg(A).
θ = 2.0 at genesis.

Properties:
  (a) Threshold semantics: predicate is False at equality, True strictly above.
  (b) Monotone in grad_H (raising it cannot un-fire the predicate).
  (c) Anti-monotone in A (raising avg-A cannot fire the predicate sooner).
  (d) θ-tuning is one-way: higher θ makes firing harder. (Article VII gaming-resistance.)
  (e) Post-transition PoA params: α=γ=0; β survives.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from tests.oracles.por import transition_predicate
from tests.oracles.poa import PoAParams, poa_params_post_transition


def test_predicate_false_at_equality():
    assert transition_predicate(2.0, 1.0, theta=2.0) is False


def test_predicate_true_strictly_above():
    assert transition_predicate(2.0001, 1.0, theta=2.0) is True


def test_predicate_false_strictly_below():
    assert transition_predicate(1.9999, 1.0, theta=2.0) is False


@given(
    grad=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    activity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    theta=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
    bump=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
)
def test_monotone_in_grad(grad, activity, theta, bump):
    """If predicate fires at grad, it still fires at grad + bump."""
    if transition_predicate(grad, activity, theta):
        assert transition_predicate(grad + bump, activity, theta)


@given(
    grad=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    activity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    theta=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
    bump=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
)
def test_anti_monotone_in_activity(grad, activity, theta, bump):
    """Raising activity cannot un-fire what was already not firing.
    Equivalently: if predicate is False at activity, it stays False at activity+bump."""
    if not transition_predicate(grad, activity, theta):
        assert not transition_predicate(grad, activity + bump, theta)


@given(
    grad=st.floats(min_value=0.0, max_value=10.0),
    activity=st.floats(min_value=0.0, max_value=1.0),
    theta=st.floats(min_value=0.5, max_value=5.0),
    theta_bump=st.floats(min_value=0.0, max_value=5.0),
)
def test_higher_theta_makes_firing_harder(grad, activity, theta, theta_bump):
    if not transition_predicate(grad, activity, theta):
        assert not transition_predicate(grad, activity, theta + theta_bump)


def test_post_transition_zeroes_alpha_and_gamma():
    p = PoAParams()
    q = poa_params_post_transition(p)
    assert q.alpha == 0.0
    assert q.gamma == 0.0
    assert q.beta == p.beta  # β survives the transition (Article VII)
    assert q.epsilon == p.epsilon
