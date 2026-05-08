"""Unit tests for poa_oracle reference impl. These mirror what Hermes M4
will assert in C++ against src/cryptonote_core/poa_oracle.cpp."""

from __future__ import annotations

from hypothesis import given, strategies as st

from tests.oracles.poa import (
    ActivityWindow,
    PoAParams,
    activity_score,
    activity_ledger_hash,
)


def _w(**kw) -> ActivityWindow:
    base = dict(
        height_lo=0, height_hi=719,
        fee_burnt_atomic=0, fee_target_atomic=720_000_000_000_000,
        reduce_tx_count=0, reduce_tx_target=4,
        stake_weight=0.0, stake_weight_max=0.0,
    )
    base.update(kw)
    return ActivityWindow(**base)


def test_empty_window_yields_epsilon_floor():
    w = _w()
    p = PoAParams()
    assert activity_score(w, p) == p.epsilon


def test_full_fee_window_alone_gives_alpha():
    w = _w(fee_burnt_atomic=720_000_000_000_000)
    p = PoAParams()
    assert abs(activity_score(w, p) - p.alpha) < 1e-12


def test_full_reduce_alone_gives_beta():
    w = _w(reduce_tx_count=4)
    p = PoAParams()
    assert abs(activity_score(w, p) - p.beta) < 1e-12


def test_full_stake_alone_gives_gamma():
    w = _w(stake_weight=1.0, stake_weight_max=1.0)
    p = PoAParams()
    assert abs(activity_score(w, p) - p.gamma) < 1e-12


def test_all_three_full_saturates_at_one():
    w = _w(
        fee_burnt_atomic=720_000_000_000_000,
        reduce_tx_count=4,
        stake_weight=1.0, stake_weight_max=1.0,
    )
    p = PoAParams()
    # α + β + γ = 1.0 exactly.
    assert activity_score(w, p) == 1.0


def test_overflow_saturates_to_one():
    w = _w(
        fee_burnt_atomic=10**21,  # 1000x target
        reduce_tx_count=999,
        stake_weight=1e6, stake_weight_max=1.0,
    )
    p = PoAParams()
    assert activity_score(w, p) == 1.0


@given(
    fb=st.integers(min_value=0, max_value=10**20),
    rt=st.integers(min_value=0, max_value=1000),
    sw=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
)
def test_activity_within_unit_interval(fb, rt, sw):
    w = _w(fee_burnt_atomic=fb, reduce_tx_count=rt, stake_weight=sw, stake_weight_max=1.0)
    p = PoAParams()
    a = activity_score(w, p)
    assert p.epsilon <= a <= 1.0


def test_activity_ledger_hash_is_32_bytes_and_deterministic():
    w = _w()
    h1 = activity_ledger_hash(w)
    h2 = activity_ledger_hash(w)
    assert len(h1) == 32
    assert h1 == h2


def test_activity_ledger_hash_changes_with_each_field():
    w0 = _w()
    h0 = activity_ledger_hash(w0)
    perturbations = [
        _w(height_lo=1),
        _w(height_hi=720),
        _w(fee_burnt_atomic=1),
        _w(fee_target_atomic=720_000_000_000_001),
        _w(reduce_tx_count=1),
        _w(reduce_tx_target=5),
        _w(stake_weight=0.5),
        _w(stake_weight_max=1.0),
    ]
    for w in perturbations:
        assert activity_ledger_hash(w) != h0
