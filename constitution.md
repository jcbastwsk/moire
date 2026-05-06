# Moire Monetary Constitution

Version: 1.0.0  Genesis-pinned. Mutable only via `reduce(ΔC)` transactions.

This document is the on-chain monetary constitution. Read top to bottom in one sitting.

---

## Article I — Names and units

| Field | Value |
|---|---|
| Project name | Moire |
| Ticker | MOI |
| Smallest unit | 1 attomoire = 10⁻¹² MOI |
| Block time | 60 seconds |
| Genesis date | TBD (set at mainnet launch) |
| Pre-mine | 0 attomoire |

---

## Article II — Issuance schedule

```
R(n) = k · A(n) · exp(-λ · n)                         for n <  N_trans
R(n) = k · grad_H(ΔC(n)) · exp(-λ · n)                for n >= N_trans
```

| Constant | Value | Source |
|---|---|---|
| `k` | 7,480,000,000,000 attomoire | `genesis/params.toml` |
| `λ` | 3.5622 × 10⁻⁷ per block | derived (Article IX) |
| `θ` | 2.0 | `genesis/params.toml` |
| `N_trans` | runtime; first n with `grad_H/avg_A > θ` | computed |

---

## Article III — Activity score `A(n)`

```
A(n) = clamp(α · V_tx(n) + β · R_contrib(n) + γ · P_stake(n), ε, 1)
```

| Weight | Value | Decommission |
|---|---|---|
| `α` | 0.5 | set to 0 at `N_trans` |
| `β` | 0.4 | survives PoR phase |
| `γ` | 0.1 | set to 0 at `N_trans` |
| `ε` | 1 × 10⁻⁶ | survives PoR phase |

Inputs:
- `V_tx(n)`: rolling 720-block normalized fee burn. `V_tx = min(F̄ / F_target, 1)`. `F_target = 1 MOI per block`.
- `R_contrib(n)`: rolling 720-block normalized count of accepted `reduce(ΔC)` txs. Cap at 1.
- `P_stake(n)`: rolling 720-block normalized stake-signed attestation weight. Cap at 1.

---

## Article IV — Reduction proxy `H(C)`

```
H(C) = w_brotli · Brotli11(canon(C))
     + w_ast    · AST_node_count(C)
     + w_proof  · |proof(C)|
```

| Weight | Genesis value |
|---|---|
| `w_brotli` | 0.6 |
| `w_ast`    | 0.3 |
| `w_proof`  | 0.1 |

`canon(C)` excludes `external/randomx/`, `external/lmdb/`, and `build/`. Tree-sitter C++ grammar pinned by hash in `genesis/toolchain.merkle.json`. Brotli pinned by hash in same.

Weights are mutable only via PoR txs that demonstrably reduce overall `H` under the new weights.

---

## Article V — `reduce(ΔC)` transaction

A reduce-tx carries:

| Field | Bytes |
|---|---|
| `parent_codebase_hash` | 32 |
| `child_codebase_hash` | 32 |
| `entropy_delta_signed` | 8 (int64) |
| `patch_blob_hash` | 32 |
| `issuer_pubkey` | 32 |
| `issuer_signature` | 64 |
| `staked_credit` | 8 (uint64 attomoire) |
| `canary_window_start` | 8 (uint64 height) |

Validity (consensus rules):

1. `parent_codebase_hash == cumulative_reduction_root_at_height(canary_window_start - 1)`.
2. `entropy_delta_signed > 0`.
3. Signature verifies against `issuer_pubkey`.
4. `staked_credit >= MIN_STAKE` (genesis: `100,000,000,000,000` attomoire = 100 MOI).
5. Behavioral-equivalence floor passes (Article VI).
6. Patch reproducibly applies to parent codebase under pinned toolchain (canary-node check).

Reward (paid at `canary_window_start + K_canary` if no canary failures):

```
issuer_reward = β · R(canary_window_start) · (entropy_delta / max_entropy_delta_in_window)
```

Failure: `staked_credit` is burnt (sent to provably unspendable key); incident marker recorded.

---

## Article VI — Behavioral-equivalence floor

A reduce-tx is valid only if:

1. The post-patch codebase compiles deterministically under the pinned toolchain.
2. Every test in the surviving test corpus passes on the post-patch codebase.
3. Tests deleted in `ΔC` are paired with deletion of the feature they exercised. Verified by AST-coverage intersection.
4. All `tests/invariants/` properties pass on a fresh testnet replay of the last 1024 blocks.

The test corpus hash at genesis is the `tests/` directory of the post-excision Monero source. Subsequent test changes ride on `reduce(ΔC)` txs.

---

## Article VII — Transition predicate

```
N_trans = min n :  ΔH_avg(n) / |ΔC|_avg(n)  >  θ · A_avg(n)
```

Window: last `K_trans = 1024` accepted reduce-txs.

At `n = N_trans`:
- `α := 0`, `γ := 0`, irreversibly.
- Reward formula switches to PoR branch.
- A `transition_marker` tx is recorded with `(N_trans, deciding_patch_hash, snapshot(activity_ledger))`.

θ is mutable only via reduce-tx that reduces overall H under the new θ. Inflation-via-θ-tuning is self-defeating.

---

## Article VIII — Canary-then-promote

| Constant | Value |
|---|---|
| `K_canary` | 2,016 blocks (~2 weeks) |
| `MIN_CANARY_PEER_ASNS` | 4 |

Canary nodes opt in via `--canary` flag. A reduce-tx is **promoted** at height `canary_window_start + K_canary` only if:

- ≥ `MIN_CANARY_PEER_ASNS` distinct canary-node ASNs reported successful operation.
- Zero consensus-divergence reports filed during the window.
- All `tests/invariants/` continued to pass on canary process.

Promotion = every node downloads or rebuilds the patched binary under the pinned toolchain at next process restart. Atomic swap, not live execve.

---

## Article IX — λ derivation (audit trail)

Target: 95 % of asymptotic supply minted by year 16 = 8,409,600 blocks.

```
1 − e^(-λ · 8,409,600) = 0.95
λ = -ln(0.05) / 8,409,600
λ = 2.9957 / 8,409,600
λ ≈ 3.5622 × 10⁻⁷ per block
```

Half-life ≈ 1,945,890 blocks ≈ 3.7 years.

Asymptotic supply with `Ā = 1`, `k = 7.48 × 10¹²` attomoire:

```
S(∞) = k · Ā / λ = 7.48 × 10¹² / 3.5622 × 10⁻⁷
     ≈ 2.10 × 10¹⁹ attomoire
     = 21,000,000 MOI
```

The 21 M cap is a **derived property** of (k, λ, Ā), not a hand-set constant.

---

## Article X — Privacy

The base layer publishes:

- All transaction amounts.
- All inputs and outputs.
- Block-by-block ledger.

Receiver pseudonymity is provided by stealth addresses (one-time pubkey per output). No mixing. No ring signatures. No range proofs. No view tags.

If you want anonymity, run a Tor mixer client at the wallet layer. Mixing is not consensus.

---

## Article XI — Governance

There is none.

The transition predicate is the only "vote." Patches advance the protocol via `reduce(ΔC)`. There is no foundation, no developer fund, no on-chain ballot, no off-chain ballot binding consensus, no committee. The protocol is the constitution.

---

## Article XII — Hard-cap guarantee

Total issuance is bounded above by:

```
S(∞) ≤ k · Ā / λ
```

`Ā ≤ 1` by the clamp in Article III. `k` and `λ` are constitution-pinned. Therefore `S(∞)` is finite and known at genesis.

After `N_trans`, the bound tightens:

```
R(n) = k · grad_H(ΔC(n)) · exp(-λn)
```

`grad_H` decreases monotonically as the codebase approaches its irreducible Kolmogorov floor. At the floor, `R(n) → 0`, which is the asymptotic hard cap.

---

## Article XIII — Amendment

This constitution is amended only by `reduce(ΔC)` transactions that pass Articles V and VI and the canary period of Article VIII. The text of this file at any height is `genesis/constitution.md` patched by every accepted reduce-tx in `cumulative_reduction_root` up to that height.

---

End of constitution. 13 articles. Read it again tomorrow.
