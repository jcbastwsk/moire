# Moire — Python reference for src/cryptonote_core/reduce_tx.{h,cpp} +
# the txin_reduce serialization shape from cryptonote_basic.h.
#
# Mirrors patch 06-reduce-tx-type.patch. Used by:
#   tests/invariants/test_reduce_tx_roundtrip.py
#   tests/invariants/test_cumulative_root.py
#   tests/oracle_unit/test_reduce.py

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .crypto import cn_fast_hash, le_u64


# Constitution-pinned canary constants (must match reduce_tx.h).
K_CANARY_BLOCKS = 2016
MIN_CANARY_PEER_ASNS = 4
MIN_STAKE_ATOMIC = 100_000_000_000_000  # 100 MOI in attomoire


class CanaryStatus(IntEnum):
    PENDING = 0
    PROMOTED = 1
    REVERTED = 2


# ---------------------------------------------------------------------------
# txin_reduce wire format (from patch 06).
#
# Field order in serialization:
#   parent_codebase_hash   : 32B
#   child_codebase_hash    : 32B
#   patch_blob_hash        : 32B
#   entropy_delta_signed   : varint (zig-zag) — must be > 0 for admissibility
#   issuer_pubkey          : 32B
#   issuer_signature       : 64B
#   staked_credit_atomic   : varint
#   canary_window_start    : varint
#
# Monero's VARINT_FIELD: unsigned LEB128. zig-zag is for the SIGNED int64.
# ---------------------------------------------------------------------------

def varint_encode(n: int) -> bytes:
    """Unsigned LEB128 (matches Monero's tools::write_varint)."""
    if n < 0:
        raise ValueError("unsigned varint")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def varint_decode(buf: bytes, off: int = 0) -> tuple[int, int]:
    """Returns (value, bytes_read)."""
    n = 0
    shift = 0
    i = 0
    while True:
        if off + i >= len(buf):
            raise ValueError("varint truncated")
        b = buf[off + i]
        n |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            return n, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def zigzag_encode(n: int) -> int:
    """Map signed int64 -> unsigned for varint."""
    if n < 0:
        return ((-n) << 1) - 1
    return n << 1


def zigzag_decode(u: int) -> int:
    return (u >> 1) ^ -(u & 1)


@dataclass
class TxinReduce:
    parent_codebase_hash: bytes
    child_codebase_hash: bytes
    patch_blob_hash: bytes
    entropy_delta_signed: int
    issuer_pubkey: bytes        # 32B
    issuer_signature: bytes     # 64B
    staked_credit_atomic: int
    canary_window_start: int

    def __post_init__(self):
        for name, exp in [("parent_codebase_hash", 32),
                           ("child_codebase_hash", 32),
                           ("patch_blob_hash", 32),
                           ("issuer_pubkey", 32),
                           ("issuer_signature", 64)]:
            v = getattr(self, name)
            if len(v) != exp:
                raise ValueError(f"{name} must be {exp} bytes, got {len(v)}")
        if self.staked_credit_atomic < 0 or self.canary_window_start < 0:
            raise ValueError("negative varint field")

    # -- (de)serialization ---------------------------------------------------

    def serialize(self) -> bytes:
        return (
            self.parent_codebase_hash
            + self.child_codebase_hash
            + self.patch_blob_hash
            + varint_encode(zigzag_encode(self.entropy_delta_signed))
            + self.issuer_pubkey
            + self.issuer_signature
            + varint_encode(self.staked_credit_atomic)
            + varint_encode(self.canary_window_start)
        )

    @classmethod
    def deserialize(cls, buf: bytes) -> "TxinReduce":
        off = 0
        parent = buf[off:off + 32]; off += 32
        child = buf[off:off + 32]; off += 32
        patch = buf[off:off + 32]; off += 32
        zz, n = varint_decode(buf, off); off += n
        delta = zigzag_decode(zz)
        pub = buf[off:off + 32]; off += 32
        sig = buf[off:off + 64]; off += 64
        stake, n = varint_decode(buf, off); off += n
        canary, n = varint_decode(buf, off); off += n
        if off != len(buf):
            raise ValueError(f"trailing bytes: consumed {off}, total {len(buf)}")
        return cls(parent, child, patch, delta, pub, sig, stake, canary)

    # -- semantics -----------------------------------------------------------

    def admissibility_input_hash(self) -> bytes:
        """Hash of fields covered by issuer_signature (everything except the sig)."""
        m = (
            self.parent_codebase_hash
            + self.child_codebase_hash
            + self.patch_blob_hash
            + varint_encode(zigzag_encode(self.entropy_delta_signed))
            + self.issuer_pubkey
            + le_u64(self.staked_credit_atomic)
            + le_u64(self.canary_window_start)
        )
        return cn_fast_hash(m)


# ---------------------------------------------------------------------------
# Canary state machine (mirrors reduce_tx_state + reduce_tx_promotable).
# ---------------------------------------------------------------------------

@dataclass
class ReduceTxState:
    patch_blob_hash: bytes
    canary_window_start: int
    observed_peer_asns: int
    consensus_divergence: bool
    invariants_passed_continuously: bool
    status: CanaryStatus = CanaryStatus.PENDING


def reduce_tx_promotable(st: ReduceTxState, current_height: int) -> bool:
    """Mirrors reduce_tx.cpp::reduce_tx_promotable."""
    if st.status != CanaryStatus.PENDING:
        return False
    if current_height < st.canary_window_start + K_CANARY_BLOCKS:
        return False
    if st.consensus_divergence:
        return False
    if not st.invariants_passed_continuously:
        return False
    if st.observed_peer_asns < MIN_CANARY_PEER_ASNS:
        return False
    return True


def reduce_tx_admissible(st: ReduceTxState, current_cumulative_root: bytes) -> bool:
    """Day-1 stub. The full predicate runs in cryptonote_core::check_tx_inputs.
    Reference here is intentionally permissive — Hermes promotes this in M4."""
    if len(current_cumulative_root) != 32:
        return False
    return True
