"""Unit tests for the canary state machine and admissibility helpers."""

from __future__ import annotations

from tests.oracles.reduce import (
    K_CANARY_BLOCKS,
    MIN_CANARY_PEER_ASNS,
    CanaryStatus,
    ReduceTxState,
    reduce_tx_promotable,
    reduce_tx_admissible,
)


def _state(**kw) -> ReduceTxState:
    base = dict(
        patch_blob_hash=b"\x00" * 32,
        canary_window_start=1_000_000,
        observed_peer_asns=MIN_CANARY_PEER_ASNS,
        consensus_divergence=False,
        invariants_passed_continuously=True,
        status=CanaryStatus.PENDING,
    )
    base.update(kw)
    return ReduceTxState(**base)


def test_promotable_at_exactly_canary_end():
    st = _state()
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is True


def test_not_promotable_one_block_early():
    st = _state()
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS - 1) is False


def test_not_promotable_if_consensus_diverged():
    st = _state(consensus_divergence=True)
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is False


def test_not_promotable_if_invariants_failed():
    st = _state(invariants_passed_continuously=False)
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is False


def test_not_promotable_if_peer_asns_too_few():
    st = _state(observed_peer_asns=MIN_CANARY_PEER_ASNS - 1)
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is False


def test_not_promotable_if_already_promoted():
    st = _state(status=CanaryStatus.PROMOTED)
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is False


def test_not_promotable_if_already_reverted():
    st = _state(status=CanaryStatus.REVERTED)
    assert reduce_tx_promotable(st, 1_000_000 + K_CANARY_BLOCKS) is False


def test_admissible_requires_32_byte_root():
    st = _state()
    assert reduce_tx_admissible(st, b"\x00" * 32) is True
    assert reduce_tx_admissible(st, b"\x00" * 31) is False


def test_canary_constants_are_constitution_pinned():
    """Defense-in-depth: a stray PR cannot quietly alter these."""
    assert K_CANARY_BLOCKS == 2016
    assert MIN_CANARY_PEER_ASNS == 4
