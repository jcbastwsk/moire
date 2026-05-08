"""Re-derive every value in genesis/golden_vectors.json from the oracle
reference implementations and assert match. This file becomes a living
regression test: edit golden_vectors.json without re-running the generator
and this test fails."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tests.oracles.crypto import cn_fast_hash, merkle_root_pairwise
from tests.oracles.emission import (
    EmissionParams, K_ATOMIC_PER_BLOCK, LAMBDA_PER_BLOCK,
    envelope, reward_atomic,
)
from tests.oracles.poa import (
    ActivityWindow, PoAParams, activity_score, activity_ledger_hash,
)
from tests.oracles.por import (
    CodebaseSnapshot, PoRWeights, codebase_entropy, extend_cumulative_root,
    reduction_rate, transition_predicate,
)
from tests.oracles.reduce import (
    K_CANARY_BLOCKS, MIN_CANARY_PEER_ASNS, CanaryStatus,
    ReduceTxState, TxinReduce, reduce_tx_promotable,
)


VECTORS = Path(__file__).resolve().parent.parent.parent / "genesis" / "golden_vectors.json"


@pytest.fixture(scope="module")
def vectors():
    if not VECTORS.exists():
        pytest.skip("golden_vectors.json not yet generated")
    return json.loads(VECTORS.read_text())


def test_constants_pinned(vectors):
    c = vectors["constants"]
    assert c["k_atomic_per_block"] == K_ATOMIC_PER_BLOCK
    assert c["lambda_per_block"] == LAMBDA_PER_BLOCK
    assert c["k_canary_blocks"] == K_CANARY_BLOCKS
    assert c["min_canary_peer_asns"] == MIN_CANARY_PEER_ASNS


def test_block_reward_vectors(vectors):
    p = EmissionParams()
    for v in vectors["block_reward"]:
        assert reward_atomic(v["n"], v["pivot"], p) == v["reward_atomic"], (
            f"reward mismatch at n={v['n']}, pivot={v['pivot']}"
        )


def test_poa_vectors(vectors):
    p = PoAParams()
    for v in vectors["poa"]:
        w = ActivityWindow(**v["window"])
        score = activity_score(w, p)
        assert score == pytest.approx(v["activity_score"]), v["label"]
        assert activity_ledger_hash(w).hex() == v["activity_ledger_hash_hex"], v["label"]


def test_por_vectors(vectors):
    block = vectors["por"]
    w = PoRWeights(**block["weights"])
    snaps = []
    for s in block["snapshots"]:
        snap = CodebaseSnapshot(
            root=bytes.fromhex(s["root_hex"]),
            brotli_size_bytes=s["brotli_size_bytes"],
            ast_node_count=s["ast_node_count"],
            proof_size_bytes=s["proof_size_bytes"],
        )
        snaps.append(snap)
        assert codebase_entropy(snap, w) == pytest.approx(s["codebase_entropy"]), s["label"]

    for tc in block["transition_cases"]:
        got = transition_predicate(tc["avg_grad"], tc["avg_activity"], tc["theta"])
        assert got == tc["fires"]


def test_reduce_tx_vectors(vectors):
    for v in vectors["reduce_tx"]:
        blob = bytes.fromhex(v["wire_blob_hex"])
        # Round-trip
        tx = TxinReduce.deserialize(blob)
        assert tx.serialize() == blob, v["label"]
        # Admissibility input hash
        assert tx.admissibility_input_hash().hex() == v["admissibility_input_hash_hex"], v["label"]


def test_canary_vectors(vectors):
    base_state = ReduceTxState(
        patch_blob_hash=cn_fast_hash(b"moire-golden|canary|patch"),
        canary_window_start=1_000_000,
        observed_peer_asns=MIN_CANARY_PEER_ASNS,
        consensus_divergence=False,
        invariants_passed_continuously=True,
        status=CanaryStatus.PENDING,
    )
    for v in vectors["canary"]:
        got = reduce_tx_promotable(base_state, v["current_height"])
        assert got == v["promotable"], v["label"]


def test_merkle_vectors(vectors):
    leaves = [cn_fast_hash(f"leaf-{i}".encode()) for i in range(7)]
    for v in vectors["merkle"]:
        got = merkle_root_pairwise(leaves[: v["size"]]).hex()
        assert got == v["root_hex"], f"merkle size {v['size']}"


def test_self_sha256_protocol(vectors):
    """The self_sha256 is sha256 of the json without the self_sha256 key.
    Pinning the protocol so Hermes-side verifiers stay in sync."""
    import hashlib
    payload = {k: v for k, v in vectors.items() if k != "self_sha256"}
    expected = hashlib.sha256(
        json.dumps(payload, indent=2, sort_keys=True).encode()
    ).hexdigest()
    assert vectors["self_sha256"] == expected
