"""Invariant 5 — cumulative_reduction_root Merkle correctness.

Constitution Article V + patch 05 (block_header += cumulative_reduction_root).
The root is updated by por_oracle::extend_cumulative_root for each accepted
reduce(ΔC) tx, AND independently as the pairwise Merkle root over all accepted
patch_blob_hashes (the audit trail).

Properties asserted here:
  (a) extend_cumulative_root deterministic.
  (b) Order matters (parent hash chain is sequence-dependent).
  (c) Different children produce different roots.
  (d) Pairwise Merkle root: empty corpus -> 32 zero bytes; single -> hashed-with-self
      stable; paired with reorder -> different root unless symmetric.
  (e) Round-trip across snapshot equality (same snapshot -> same extension).
"""

from __future__ import annotations

import os

from hypothesis import given, settings, strategies as st

from tests.oracles.crypto import merkle_root_pairwise, cn_fast_hash
from tests.oracles.por import CodebaseSnapshot, extend_cumulative_root


def _snapshot(seed: int = 0) -> CodebaseSnapshot:
    rng = os.urandom(32) if seed == 0 else cn_fast_hash(seed.to_bytes(8, "little"))
    return CodebaseSnapshot(
        root=rng,
        brotli_size_bytes=100_000 + seed,
        ast_node_count=50_000 + seed,
        proof_size_bytes=8_000 + seed,
    )


def test_extend_cumulative_root_deterministic():
    parent = b"\xaa" * 32
    patch = b"\xbb" * 32
    snap = _snapshot(1)
    a = extend_cumulative_root(parent, patch, snap)
    b = extend_cumulative_root(parent, patch, snap)
    assert a == b
    assert len(a) == 32


def test_extend_order_dependent():
    """Chain (root0 -> root1 -> root2) ≠ (root0 -> root2 -> root1) in general."""
    p0 = b"\x00" * 32
    s1 = _snapshot(1)
    s2 = _snapshot(2)
    pa = extend_cumulative_root(p0, b"\x01" * 32, s1)
    pa_then = extend_cumulative_root(pa, b"\x02" * 32, s2)
    pb = extend_cumulative_root(p0, b"\x02" * 32, s2)
    pb_then = extend_cumulative_root(pb, b"\x01" * 32, s1)
    assert pa_then != pb_then


@given(
    parent=st.binary(min_size=32, max_size=32),
    patch=st.binary(min_size=32, max_size=32),
)
@settings(max_examples=100, deadline=None)
def test_extend_changes_when_snapshot_changes(parent, patch):
    s1 = _snapshot(7)
    s2 = CodebaseSnapshot(
        root=s1.root,
        brotli_size_bytes=s1.brotli_size_bytes + 1,
        ast_node_count=s1.ast_node_count,
        proof_size_bytes=s1.proof_size_bytes,
    )
    a = extend_cumulative_root(parent, patch, s1)
    b = extend_cumulative_root(parent, patch, s2)
    assert a != b


def test_merkle_empty_is_zero():
    assert merkle_root_pairwise([]) == b"\x00" * 32


def test_merkle_single_leaf_is_self_hashed_via_pairing_rule_or_pass_through():
    """With our rule (return single leaf as-is when len==1 after the loop
    starts), single leaf returns itself. Pinning this here so any change
    is intentional."""
    leaf = cn_fast_hash(b"alpha")
    assert merkle_root_pairwise([leaf]) == leaf


def test_merkle_two_leaves():
    a = cn_fast_hash(b"alpha")
    b = cn_fast_hash(b"beta")
    expected = cn_fast_hash(a + b)
    assert merkle_root_pairwise([a, b]) == expected


def test_merkle_three_leaves_duplicates_last():
    a = cn_fast_hash(b"a")
    b = cn_fast_hash(b"b")
    c = cn_fast_hash(b"c")
    # Odd: last duplicates -> [a,b], [c,c] -> root = H(H(a||b) || H(c||c))
    layer1 = [cn_fast_hash(a + b), cn_fast_hash(c + c)]
    expected = cn_fast_hash(layer1[0] + layer1[1])
    assert merkle_root_pairwise([a, b, c]) == expected


@given(seq=st.lists(st.binary(min_size=32, max_size=32), min_size=0, max_size=20))
def test_merkle_root_deterministic_property(seq):
    assert merkle_root_pairwise(seq) == merkle_root_pairwise(list(seq))


def test_merkle_reorder_changes_root_for_distinct_leaves():
    a = cn_fast_hash(b"a")
    b = cn_fast_hash(b"b")
    assert merkle_root_pairwise([a, b]) != merkle_root_pairwise([b, a])
