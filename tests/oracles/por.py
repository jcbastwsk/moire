# Moire — Python reference for src/cryptonote_core/por_oracle.{h,cpp}.
#
# Mirrors patch 04-por-oracle.patch.
# Constitution: Articles IV (PoR), VII (transition predicate).

from __future__ import annotations

from dataclasses import dataclass

from .crypto import cn_fast_hash, le_u64


@dataclass(frozen=True)
class PoRWeights:
    w_brotli: float = 0.6
    w_ast: float = 0.3
    w_proof: float = 0.1


@dataclass(frozen=True)
class CodebaseSnapshot:
    root: bytes  # 32 bytes — Merkle root of canon(C)
    brotli_size_bytes: int
    ast_node_count: int
    proof_size_bytes: int

    def __post_init__(self):
        if len(self.root) != 32:
            raise ValueError(f"snapshot.root must be 32 bytes, got {len(self.root)}")


def codebase_entropy(c: CodebaseSnapshot, w: PoRWeights = PoRWeights()) -> float:
    """H(C) = w_brotli·Brotli + w_ast·AST_nodes + w_proof·proof_bytes."""
    return (
        w.w_brotli * float(c.brotli_size_bytes)
        + w.w_ast * float(c.ast_node_count)
        + w.w_proof * float(c.proof_size_bytes)
    )


def reduction_rate(parent: CodebaseSnapshot,
                   child: CodebaseSnapshot,
                   patch_size_bytes: int,
                   w: PoRWeights = PoRWeights()) -> float:
    """grad_H = (H(parent) - H(child)) / |patch|."""
    if patch_size_bytes == 0:
        return 0.0
    return (codebase_entropy(parent, w) - codebase_entropy(child, w)) / float(patch_size_bytes)


def transition_predicate(avg_reduction_rate: float,
                         avg_activity_score: float,
                         theta: float = 2.0) -> bool:
    """N_trans fires when avg(grad_H) > θ · avg(A)."""
    return avg_reduction_rate > theta * avg_activity_score


def extend_cumulative_root(parent_root: bytes,
                           patch_blob_hash: bytes,
                           child: CodebaseSnapshot) -> bytes:
    """Mirror por_oracle.cpp::extend_cumulative_root byte layout.

    Layout: parent_root(32) || patch_blob_hash(32) || child.root(32) ||
            u64 brotli || u64 ast || u64 proof
    """
    if len(parent_root) != 32 or len(patch_blob_hash) != 32:
        raise ValueError("hashes must be 32 bytes")
    buf = (
        parent_root
        + patch_blob_hash
        + child.root
        + le_u64(child.brotli_size_bytes)
        + le_u64(child.ast_node_count)
        + le_u64(child.proof_size_bytes)
    )
    return cn_fast_hash(buf)
