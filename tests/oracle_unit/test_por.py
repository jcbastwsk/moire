"""Unit tests for por_oracle reference impl."""

from __future__ import annotations

from tests.oracles.por import (
    CodebaseSnapshot,
    PoRWeights,
    codebase_entropy,
    reduction_rate,
    extend_cumulative_root,
    transition_predicate,
)


def _snap(brotli=100_000, ast=50_000, proof=8_000, root=b"\x00" * 32) -> CodebaseSnapshot:
    return CodebaseSnapshot(root=root, brotli_size_bytes=brotli,
                            ast_node_count=ast, proof_size_bytes=proof)


def test_codebase_entropy_default_weights():
    c = _snap()
    H = codebase_entropy(c)
    # 0.6 * 100_000 + 0.3 * 50_000 + 0.1 * 8_000 = 60_000 + 15_000 + 800 = 75_800
    assert H == 75_800.0


def test_reduction_rate_zero_patch_size_is_zero():
    parent = _snap()
    child = _snap(brotli=99_000)
    assert reduction_rate(parent, child, patch_size_bytes=0) == 0.0


def test_reduction_rate_positive_when_child_smaller():
    parent = _snap(brotli=100_000)
    child = _snap(brotli=99_000)
    rate = reduction_rate(parent, child, patch_size_bytes=200)
    # ΔH = 0.6 * 1_000 = 600. rate = 600 / 200 = 3.0.
    assert rate == 3.0


def test_reduction_rate_negative_when_child_larger():
    """A 'reduction' that grows the codebase has negative grad_H. The
    admissibility predicate must reject these (entropy_delta_signed > 0
    invariant). Here we just verify the math is signed."""
    parent = _snap(brotli=100_000)
    child = _snap(brotli=101_000)
    rate = reduction_rate(parent, child, patch_size_bytes=100)
    assert rate < 0.0


def test_weights_sum_invariant():
    """Genesis policy: w_brotli + w_ast + w_proof = 1.0."""
    w = PoRWeights()
    s = w.w_brotli + w.w_ast + w.w_proof
    assert abs(s - 1.0) < 1e-12


def test_transition_predicate_basic():
    assert transition_predicate(2.5, 1.0, 2.0) is True
    assert transition_predicate(1.5, 1.0, 2.0) is False


def test_extend_cumulative_root_distinct_for_distinct_patches():
    p0 = b"\x00" * 32
    s = _snap()
    h1 = extend_cumulative_root(p0, b"\x01" * 32, s)
    h2 = extend_cumulative_root(p0, b"\x02" * 32, s)
    assert h1 != h2


def test_codebase_entropy_sensitive_to_each_axis():
    base = _snap()
    H0 = codebase_entropy(base)
    assert codebase_entropy(_snap(brotli=base.brotli_size_bytes + 1)) != H0
    assert codebase_entropy(_snap(ast=base.ast_node_count + 1)) != H0
    assert codebase_entropy(_snap(proof=base.proof_size_bytes + 1)) != H0
