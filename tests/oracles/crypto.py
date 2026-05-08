# Moire — crypto helpers for the Python reference oracles.
#
# `cn_fast_hash` in monero is Keccak-256 (pre-SHA3-standardization padding).
# pycryptodome's Crypto.Hash.keccak is the matching primitive.
#
# This module is consumed by the reference oracles in the same package.
# It is NOT a substitute for src/crypto/* — it is the test side of the bridge:
# Hermes's C++ unit tests must produce the same digests on the same input bytes.

from __future__ import annotations

import struct
from typing import Iterable

from Crypto.Hash import keccak


def cn_fast_hash(data: bytes) -> bytes:
    """Monero's cn_fast_hash: Keccak-256 (32 bytes). Pre-standard padding."""
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def hash_hex(data: bytes) -> str:
    return cn_fast_hash(data).hex()


def le_u64(x: int) -> bytes:
    return struct.pack("<Q", x & 0xFFFFFFFFFFFFFFFF)


def le_u32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def le_f64(x: float) -> bytes:
    return struct.pack("<d", float(x))


def merkle_root_pairwise(leaves: Iterable[bytes]) -> bytes:
    """Pairwise binary Merkle. Empty -> 32 zero bytes. Odd leaf duplicated.

    Used for `cumulative_reduction_root` over an ordered list of accepted
    reduce(ΔC) tx hashes. C++ side must mirror exactly.
    """
    nodes = [bytes(l) for l in leaves]
    if not nodes:
        return b"\x00" * 32
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        nodes = [cn_fast_hash(nodes[i] + nodes[i + 1]) for i in range(0, len(nodes), 2)]
    return nodes[0]
