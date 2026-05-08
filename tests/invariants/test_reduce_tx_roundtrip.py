"""Invariant 4 — txin_reduce serialization round-trip.

Constitution Article V + patch 06: serialize(deserialize(x)) == x and
deserialize(serialize(x)) == x for all valid txin_reduce values.

Properties:
  (a) Round-trip on hand-rolled vectors.
  (b) Round-trip via hypothesis over the field domain.
  (c) Trailing-byte rejection.
  (d) Negative entropy_delta survives encoding (zig-zag preserves sign).
  (e) admissibility_input_hash is deterministic and depends on every signed field.
"""

from __future__ import annotations

import os

from hypothesis import given, settings, strategies as st

from tests.oracles.reduce import (
    TxinReduce,
    varint_encode,
    varint_decode,
    zigzag_encode,
    zigzag_decode,
)


def _make(parent=b"\x01" * 32, child=b"\x02" * 32, patch=b"\x03" * 32,
          delta=42, pub=b"\x04" * 32, sig=b"\x05" * 64,
          stake=100_000_000_000_000, canary=1234) -> TxinReduce:
    return TxinReduce(parent, child, patch, delta, pub, sig, stake, canary)


def test_handrolled_roundtrip():
    a = _make()
    blob = a.serialize()
    b = TxinReduce.deserialize(blob)
    assert a == b
    assert blob == b.serialize()


def test_negative_entropy_delta_roundtrips():
    a = _make(delta=-99)
    b = TxinReduce.deserialize(a.serialize())
    assert b.entropy_delta_signed == -99


@given(
    delta=st.integers(min_value=-(2**62), max_value=2**62 - 1),
    stake=st.integers(min_value=0, max_value=2**63 - 1),
    canary=st.integers(min_value=0, max_value=2**63 - 1),
)
@settings(max_examples=200, deadline=None)
def test_property_roundtrip(delta, stake, canary):
    a = TxinReduce(
        parent_codebase_hash=os.urandom(32),
        child_codebase_hash=os.urandom(32),
        patch_blob_hash=os.urandom(32),
        entropy_delta_signed=delta,
        issuer_pubkey=os.urandom(32),
        issuer_signature=os.urandom(64),
        staked_credit_atomic=stake,
        canary_window_start=canary,
    )
    b = TxinReduce.deserialize(a.serialize())
    assert a == b


def test_trailing_bytes_rejected():
    a = _make()
    blob = a.serialize() + b"\x00"
    try:
        TxinReduce.deserialize(blob)
    except ValueError:
        return
    raise AssertionError("trailing bytes accepted")


def test_truncated_payload_rejected():
    blob = _make().serialize()[:-1]
    try:
        TxinReduce.deserialize(blob)
    except (ValueError, IndexError):
        return
    raise AssertionError("truncated payload accepted")


@given(n=st.integers(min_value=0, max_value=2**63 - 1))
def test_varint_roundtrip(n):
    enc = varint_encode(n)
    dec, consumed = varint_decode(enc)
    assert dec == n
    assert consumed == len(enc)


@given(n=st.integers(min_value=-(2**62), max_value=2**62 - 1))
def test_zigzag_roundtrip(n):
    assert zigzag_decode(zigzag_encode(n)) == n


def test_admissibility_hash_is_deterministic():
    a = _make()
    h1 = a.admissibility_input_hash()
    h2 = a.admissibility_input_hash()
    assert h1 == h2
    assert len(h1) == 32


def test_admissibility_hash_depends_on_each_signed_field():
    """Flip one byte in each signed field; hash must change."""
    base = _make()
    base_h = base.admissibility_input_hash()

    perturb = [
        ("parent_codebase_hash", bytes([base.parent_codebase_hash[0] ^ 1]) + base.parent_codebase_hash[1:]),
        ("child_codebase_hash", bytes([base.child_codebase_hash[0] ^ 1]) + base.child_codebase_hash[1:]),
        ("patch_blob_hash", bytes([base.patch_blob_hash[0] ^ 1]) + base.patch_blob_hash[1:]),
        ("entropy_delta_signed", base.entropy_delta_signed + 1),
        ("issuer_pubkey", bytes([base.issuer_pubkey[0] ^ 1]) + base.issuer_pubkey[1:]),
        ("staked_credit_atomic", base.staked_credit_atomic + 1),
        ("canary_window_start", base.canary_window_start + 1),
    ]
    for fname, new_val in perturb:
        kwargs = dict(
            parent_codebase_hash=base.parent_codebase_hash,
            child_codebase_hash=base.child_codebase_hash,
            patch_blob_hash=base.patch_blob_hash,
            entropy_delta_signed=base.entropy_delta_signed,
            issuer_pubkey=base.issuer_pubkey,
            issuer_signature=base.issuer_signature,
            staked_credit_atomic=base.staked_credit_atomic,
            canary_window_start=base.canary_window_start,
        )
        kwargs[fname] = new_val
        twin = TxinReduce(**kwargs)
        assert twin.admissibility_input_hash() != base_h, f"hash invariant under {fname} perturb"
