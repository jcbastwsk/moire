#!/usr/bin/env python3
"""Emit genesis/golden_vectors.json.

These are deterministic (input, expected) tuples that the C++ unit tests on
Hermes M4 must reproduce against the canonical implementations in:
  src/cryptonote_core/poa_oracle.{h,cpp}
  src/cryptonote_core/por_oracle.{h,cpp}
  src/cryptonote_core/reduce_tx.{h,cpp}
  block-reward formula in cryptonote_core::core::get_block_reward (post-patch)

The vector file is constitution-pinned — any change must come through a
reduce(ΔC) tx (patch + ledger entry) like everything else.

Usage:
    python3 tests/gen_golden_vectors.py > genesis/golden_vectors.json
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

# Allow running from project root without an install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.oracles.crypto import cn_fast_hash, merkle_root_pairwise
from tests.oracles.emission import (
    EmissionParams,
    K_ATOMIC_PER_BLOCK,
    LAMBDA_PER_BLOCK,
    envelope,
    reward_atomic,
)
from tests.oracles.poa import (
    ActivityWindow,
    PoAParams,
    activity_score,
    activity_ledger_hash,
)
from tests.oracles.por import (
    CodebaseSnapshot,
    PoRWeights,
    codebase_entropy,
    extend_cumulative_root,
    reduction_rate,
    transition_predicate,
)
from tests.oracles.reduce import (
    K_CANARY_BLOCKS,
    MIN_CANARY_PEER_ASNS,
    CanaryStatus,
    ReduceTxState,
    TxinReduce,
    reduce_tx_promotable,
)


def hex32(seed: bytes, label: bytes) -> bytes:
    """Deterministic 32-byte material derived from a seed + label."""
    return cn_fast_hash(b"moire-golden|" + seed + b"|" + label)


def make_reward_vectors() -> list[dict]:
    p = EmissionParams()
    points = [
        # (n, pivot)
        (0, 1.0),
        (0, 0.5),
        (0, 1e-6),
        (1, 1.0),
        (525_960, 1.0),       # year 1
        (2_103_840, 1.0),     # year 4
        (8_409_600, 1.0),     # year 16 — must be ~5% of k
        (8_409_600, 0.5),
        (50_000_000, 1.0),    # deep tail
    ]
    return [
        {
            "n": n,
            "pivot": pivot,
            "envelope_f64_hex": envelope(n, p).hex() if False else f"{envelope(n, p):.17e}",
            "reward_atomic": reward_atomic(n, pivot, p),
        }
        for (n, pivot) in points
    ]


def make_poa_vectors() -> list[dict]:
    p = PoAParams()
    cases = [
        ("empty", ActivityWindow(0, 719, 0, 720_000_000_000_000, 0, 4, 0.0, 0.0)),
        ("full_fees_only", ActivityWindow(0, 719, 720_000_000_000_000, 720_000_000_000_000, 0, 4, 0.0, 0.0)),
        ("full_reduce_only", ActivityWindow(0, 719, 0, 720_000_000_000_000, 4, 4, 0.0, 0.0)),
        ("full_stake_only", ActivityWindow(0, 719, 0, 720_000_000_000_000, 0, 4, 1.0, 1.0)),
        ("all_full", ActivityWindow(0, 719, 720_000_000_000_000, 720_000_000_000_000, 4, 4, 1.0, 1.0)),
        ("over_target", ActivityWindow(720, 1439, 10**21, 720_000_000_000_000, 999, 4, 5.0, 1.0)),
    ]
    return [
        {
            "label": label,
            "window": {
                "height_lo": w.height_lo, "height_hi": w.height_hi,
                "fee_burnt_atomic": w.fee_burnt_atomic, "fee_target_atomic": w.fee_target_atomic,
                "reduce_tx_count": w.reduce_tx_count, "reduce_tx_target": w.reduce_tx_target,
                "stake_weight": w.stake_weight, "stake_weight_max": w.stake_weight_max,
            },
            "activity_score": activity_score(w, p),
            "activity_ledger_hash_hex": activity_ledger_hash(w).hex(),
        }
        for label, w in cases
    ]


def make_por_vectors() -> list[dict]:
    w = PoRWeights()
    snaps = [
        CodebaseSnapshot(root=hex32(b"snap", b"0"), brotli_size_bytes=100_000, ast_node_count=50_000, proof_size_bytes=8_000),
        CodebaseSnapshot(root=hex32(b"snap", b"1"), brotli_size_bytes=99_000,  ast_node_count=49_500, proof_size_bytes=8_000),
        CodebaseSnapshot(root=hex32(b"snap", b"2"), brotli_size_bytes=95_000,  ast_node_count=48_000, proof_size_bytes=7_000),
    ]
    parent_root = b"\x00" * 32
    chain = [parent_root]
    for i, s in enumerate(snaps):
        patch_blob = hex32(b"patch", str(i).encode())
        new_root = extend_cumulative_root(chain[-1], patch_blob, s)
        chain.append(new_root)

    return {
        "weights": {"w_brotli": w.w_brotli, "w_ast": w.w_ast, "w_proof": w.w_proof},
        "snapshots": [
            {
                "label": f"snap_{i}",
                "root_hex": s.root.hex(),
                "brotli_size_bytes": s.brotli_size_bytes,
                "ast_node_count": s.ast_node_count,
                "proof_size_bytes": s.proof_size_bytes,
                "codebase_entropy": codebase_entropy(s, w),
            }
            for i, s in enumerate(snaps)
        ],
        "reduction_rates": [
            {
                "parent": "snap_0",
                "child": f"snap_{i+1}",
                "patch_size_bytes": ps,
                "rate": reduction_rate(snaps[0], snaps[i + 1], ps, w),
            }
            for i, ps in enumerate([200, 800])
        ],
        "transition_cases": [
            {"avg_grad": 1.5, "avg_activity": 1.0, "theta": 2.0, "fires": transition_predicate(1.5, 1.0, 2.0)},
            {"avg_grad": 2.0, "avg_activity": 1.0, "theta": 2.0, "fires": transition_predicate(2.0, 1.0, 2.0)},
            {"avg_grad": 2.5, "avg_activity": 1.0, "theta": 2.0, "fires": transition_predicate(2.5, 1.0, 2.0)},
        ],
        "cumulative_root_chain": [r.hex() for r in chain],
    }


def make_reduce_tx_vectors() -> list[dict]:
    cases = []
    base = TxinReduce(
        parent_codebase_hash=hex32(b"reduce", b"parent"),
        child_codebase_hash=hex32(b"reduce", b"child"),
        patch_blob_hash=hex32(b"reduce", b"patch"),
        entropy_delta_signed=42,
        issuer_pubkey=hex32(b"reduce", b"pubkey"),
        issuer_signature=cn_fast_hash(b"sig|0") + cn_fast_hash(b"sig|1"),
        staked_credit_atomic=100_000_000_000_000,
        canary_window_start=1_234_567,
    )
    blob = base.serialize()
    cases.append({
        "label": "canonical_42",
        "fields": {
            "parent_codebase_hash_hex": base.parent_codebase_hash.hex(),
            "child_codebase_hash_hex": base.child_codebase_hash.hex(),
            "patch_blob_hash_hex": base.patch_blob_hash.hex(),
            "entropy_delta_signed": base.entropy_delta_signed,
            "issuer_pubkey_hex": base.issuer_pubkey.hex(),
            "issuer_signature_hex": base.issuer_signature.hex(),
            "staked_credit_atomic": base.staked_credit_atomic,
            "canary_window_start": base.canary_window_start,
        },
        "wire_blob_hex": blob.hex(),
        "wire_blob_len": len(blob),
        "admissibility_input_hash_hex": base.admissibility_input_hash().hex(),
    })

    # Negative entropy (will be rejected by admissibility, but must roundtrip).
    neg = TxinReduce(
        parent_codebase_hash=base.parent_codebase_hash,
        child_codebase_hash=base.child_codebase_hash,
        patch_blob_hash=base.patch_blob_hash,
        entropy_delta_signed=-1,
        issuer_pubkey=base.issuer_pubkey,
        issuer_signature=base.issuer_signature,
        staked_credit_atomic=base.staked_credit_atomic,
        canary_window_start=base.canary_window_start,
    )
    cases.append({
        "label": "negative_entropy",
        "wire_blob_hex": neg.serialize().hex(),
        "wire_blob_len": len(neg.serialize()),
        "admissibility_input_hash_hex": neg.admissibility_input_hash().hex(),
    })

    return cases


def make_canary_vectors() -> list[dict]:
    base_state = ReduceTxState(
        patch_blob_hash=hex32(b"canary", b"patch"),
        canary_window_start=1_000_000,
        observed_peer_asns=MIN_CANARY_PEER_ASNS,
        consensus_divergence=False,
        invariants_passed_continuously=True,
        status=CanaryStatus.PENDING,
    )
    return [
        {"label": "happy_at_window_end", "current_height": 1_000_000 + K_CANARY_BLOCKS,
         "promotable": reduce_tx_promotable(base_state, 1_000_000 + K_CANARY_BLOCKS)},
        {"label": "early_one_block", "current_height": 1_000_000 + K_CANARY_BLOCKS - 1,
         "promotable": reduce_tx_promotable(base_state, 1_000_000 + K_CANARY_BLOCKS - 1)},
    ]


def make_merkle_vectors() -> list[dict]:
    leaves = [cn_fast_hash(f"leaf-{i}".encode()) for i in range(7)]
    layers = [{"size": k, "root_hex": merkle_root_pairwise(leaves[:k]).hex()} for k in range(8)]
    return layers


def main() -> int:
    p = EmissionParams()
    out = {
        "schema_version": 1,
        "comment": (
            "Moire golden vectors. Constitution-pinned. Hermes M4 unit tests "
            "must reproduce these values from the C++ implementation. "
            "Hash function: Keccak-256 (Monero cn_fast_hash). All 32-byte fields "
            "are hex strings, lowercase, no 0x prefix."
        ),
        "constants": {
            "k_atomic_per_block": K_ATOMIC_PER_BLOCK,
            "lambda_per_block": LAMBDA_PER_BLOCK,
            "asymptotic_cap_atomic": int(K_ATOMIC_PER_BLOCK / LAMBDA_PER_BLOCK),
            "discrete_cap_atomic": int(K_ATOMIC_PER_BLOCK / (1.0 - math.exp(-LAMBDA_PER_BLOCK))),
            "k_canary_blocks": K_CANARY_BLOCKS,
            "min_canary_peer_asns": MIN_CANARY_PEER_ASNS,
        },
        "block_reward": make_reward_vectors(),
        "poa": make_poa_vectors(),
        "por": make_por_vectors(),
        "reduce_tx": make_reduce_tx_vectors(),
        "canary": make_canary_vectors(),
        "merkle": make_merkle_vectors(),
    }
    payload = json.dumps(out, indent=2, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    out["self_sha256"] = digest
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
