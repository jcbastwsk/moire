# Moire — Python reference for src/cryptonote_core/poa_oracle.{h,cpp}.
#
# Mirrors patch 03-poa-oracle.patch byte-for-byte at the math level.
# Hermes M4 unit tests must produce identical numeric output for identical inputs.
#
# Constitution: Article III (Activity-Weighted Issuance).
# Genesis params: genesis/params.toml.

from __future__ import annotations

from dataclasses import dataclass

from .crypto import cn_fast_hash, le_u64, le_u32, le_f64


@dataclass(frozen=True)
class PoAParams:
    alpha: float = 0.5
    beta: float = 0.4
    gamma: float = 0.1
    epsilon: float = 1e-6


@dataclass(frozen=True)
class ActivityWindow:
    height_lo: int
    height_hi: int
    fee_burnt_atomic: int
    fee_target_atomic: int
    reduce_tx_count: int
    reduce_tx_target: int
    stake_weight: float
    stake_weight_max: float


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def activity_score(w: ActivityWindow, p: PoAParams) -> float:
    """A(B_n) per constitution Art III. Floor at p.epsilon."""
    v_tx = 0.0 if w.fee_target_atomic == 0 else _clamp01(w.fee_burnt_atomic / w.fee_target_atomic)
    r_contrib = 0.0 if w.reduce_tx_target == 0 else _clamp01(w.reduce_tx_count / w.reduce_tx_target)
    p_stake = 0.0 if w.stake_weight_max == 0.0 else _clamp01(w.stake_weight / w.stake_weight_max)
    a = p.alpha * v_tx + p.beta * r_contrib + p.gamma * p_stake
    return max(p.epsilon, min(1.0, a))


def poa_params_post_transition(p: PoAParams) -> PoAParams:
    """Article III: at N_trans, α and γ collapse to 0. β survives."""
    return PoAParams(alpha=0.0, beta=p.beta, gamma=0.0, epsilon=p.epsilon)


def activity_ledger_hash(w: ActivityWindow) -> bytes:
    """Mirrors poa_oracle.cpp::activity_ledger_hash byte layout EXACTLY.

    Layout: u64 lo, u64 hi, u64 fee_burnt, u64 fee_target,
            u32 reduce_count, u32 reduce_target,
            f64 stake_weight, f64 stake_max.
    """
    buf = (
        le_u64(w.height_lo)
        + le_u64(w.height_hi)
        + le_u64(w.fee_burnt_atomic)
        + le_u64(w.fee_target_atomic)
        + le_u32(w.reduce_tx_count)
        + le_u32(w.reduce_tx_target)
        + le_f64(w.stake_weight)
        + le_f64(w.stake_weight_max)
    )
    return cn_fast_hash(buf)
