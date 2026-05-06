# Moire — Architecture & Invariants

**Operator:** jcb. **Phase:** Day-1 design + scaffolding pass (sandbox).
**Reference baseline:** `monero-project/monero@c182abb` (master, 2026-05-06).
**Successor stack on M4:** Hermes.

---

## 1. One-paragraph thesis

Moire is a clean fork of Monero whose monetary base is governed by a piecewise emission schedule that begins as proof-of-on-chain-activity (PoA) and ends as proof-of-reduction (PoR). Issuance is paid out in proportion to verifiable codebase entropy reduction. As the protocol approaches its Kolmogorov floor, issuance approaches zero, enforcing a finite hard cap without a hand-set magic number. Privacy is reduced to its semantic minimum: transparent UTXO base + optional stealth-address unlinkability. Every accretive anonymity layer (RingCT, Bulletproofs, ring signatures, view tags, multisig, dynamic ring logic, Seraphis prep) is **deleted**, not feature-gated.

The constitution is auditable in one evening because the constitution is what survives the deletion.

---

## 2. Core formal invariants

For every height `n`, the protocol enforces:

```
R_n = k · A(B_n) · e^(-λn)                           if n <  N_trans
R_n = k · (H(C_n) - H(C_n ⊕ ΔC)) / |ΔC| · e^(-λn)    if n >= N_trans
```

Symbols:

| Symbol | Meaning | Genesis value |
|---|---|---|
| `R_n` | block reward at height `n` (atomic units) | derived |
| `k` | base reward scalar | calibrated to target cap (see §3) |
| `λ` | decay constant per block | `3.5622e-7` (95 % minted by year 16) |
| `A(B_n)` | normalized activity score for block `B_n`, ∈ [ε, 1] | per §4 |
| `α, β, γ` | PoA weights: tx-volume, early-reduction, stake-signed | `0.5, 0.4, 0.1` |
| `ε` | activity floor, prevents zero-divisor pathologies | `1e-6` |
| `H(·)` | Kolmogorov proxy: weighted Brotli + AST + proof | per §5 |
| `C_n` | canonical source tree state at height `n` | tracked on chain |
| `ΔC` | candidate reduction patch | per `reduce(ΔC)` tx |
| `θ` | transition predicate threshold | `2.0` |
| `N_trans` | first height satisfying transition predicate | runtime-determined |
| `K_canary` | canary period in blocks | `2016` (~2 weeks @ 60 s) |
| `block_time` | target block interval | `60 s` |

`α` and `γ` are deprecated to zero on-chain at `N_trans`. `β` survives as the PoR coupling term.

---

## 3. λ derivation

Pure-exponential PoA phase, treating `A` as expectation `Ā`:

```
S(N) = k·Ā · ∫₀^N e^(-λn) dn = (k·Ā / λ)·(1 − e^(-λN))
S(∞) = k·Ā / λ
```

Target: 95 % of `S(∞)` minted by year 16 = `8,409,600` blocks (60 s blocks × 365.25 × 86400 / 60).

```
1 − e^(-λ · 8,409,600) = 0.95
λ = -ln(0.05) / 8,409,600 = 2.9957 / 8,409,600
λ ≈ 3.5622 × 10⁻⁷ per block
```

Half-life = `ln(2)/λ ≈ 1,945,890` blocks ≈ **3.7 years**. By year 16 ≈ 4.32 half-lives elapsed.

### k calibration (target asymptotic cap = 21,000,000 whole coins, 12 decimals)

Atomic unit = `1 / 10¹²` whole coin.

```
S(∞) = k · Ā / λ          (atomic units)
k    = S(∞) · λ / Ā
     = 21·10¹⁸ · 3.5622e-7 / 1
     ≈ 7.48 × 10¹² atomic units per block
     ≈ 7.48 moire-coins per block at n=0 with Ā = 1
```

Calibration locked in `genesis/params.toml`. **The cap is a derived property of (λ, Ā, k), not a hand-set constant.** This is the entire point.

The PoR phase preserves the same `e^(-λn)` envelope; entropy-gradient terms scale `R_n` down further as the codebase approaches its floor. Total issuance under PoR is bounded by the same `k·Ā/λ` because the entropy gradient is itself bounded above by `Ā` (transition predicate).

---

## 4. Activity oracle `A(B_n)`

```
A(B_n) = clamp(α · V_tx + β · R_contrib + γ · P_stake, ε, 1)
```

| Term | Definition |
|---|---|
| `V_tx` | normalized transaction-fee burn over the last 720 blocks (12 h), `min(F̄ / F_target, 1)` |
| `R_contrib` | normalized count of accepted `reduce(ΔC)` txs in the last 720 blocks |
| `P_stake` | normalized weight of stake-signed attestations over the last 720 blocks |

`F_target` and the stake registry table are genesis constants (`genesis/params.toml`).

`V_tx` rewards real economic activity (fees burnt = buyers willing to pay). `R_contrib` is the early-PoR coupling — reduction patches get rewarded even before `N_trans`. `P_stake` is a small sybil-resistant signal from voluntary stakers; capped at 0.1 of total weight to prevent stake capture.

Implementation: `src/cryptonote_core/poa_oracle.{h,cpp}`. Pure function. State is the rolling-window aggregate held in `blockchain_db` columns.

---

## 5. Reduction oracle `H(·)`

```
H(C) = 0.6 · Brotli11(serialize_canonical(C))
     + 0.3 · AST_node_count(C)
     + 0.1 · proof_size(C)
```

- **Brotli11**: deterministic, content-defined; serializer canonicalizes file order, strips trailing whitespace, normalizes line endings, drops generated artifacts (`build/`, `external/randomx/`, `external/lmdb/` excluded — these are pinned upstream snapshots tracked separately).
- **AST node count**: tree-sitter C++ grammar; node count over the union of `.cpp/.cc/.c/.h/.hpp` files in the canonical scope. Tree-sitter pinned as a git submodule with hash committed at genesis.
- **proof size**: byte length of the machine-checked formal spec block (`genesis/spec.lean`) plus any new proof obligations attached to the patch.

Weights `(0.6, 0.3, 0.1)` themselves become a future PoR reduction target — **they are in the constitution and can be modified by accepted PoR patches**, but only as part of a patch that demonstrably reduces overall H. This is the meta-stable property: the weights cannot be drifted to inflate the issuer's own reduction.

Entropy delta: `ΔH = H(C_n) − H(C_n ⊕ ΔC)`. Positive ΔH means the patch reduces entropy. Marginal rate per patch byte: `ΔH / |ΔC|`. The transition predicate compares this rate to the activity score; once reduction beats activity by factor `θ`, PoR takes over.

Implementation: `src/cryptonote_core/por_oracle.{h,cpp}`. Pure function. Recomputation cost decreases monotonically with codebase size.

---

## 6. Behavioral-equivalence floor (gaming resistance)

A patch `ΔC` is admissible **only if**:

1. The post-patch codebase compiles deterministically under the pinned toolchain (build-hash matches advertised manifest).
2. The post-patch codebase passes every test in the surviving test corpus.
3. Any test deletion in `ΔC` is paired with a deletion of the feature the test exercised. The oracle verifies this by checking that the test-AST-coverage of removed tests intersects only with code AST nodes also removed in the same patch.
4. Property invariants in `tests/invariants/` pass on a fresh testnet replay of the last 1024 blocks.

This is the gaming-resistance floor. Without it, an adversary trivially "reduces" the codebase by deleting consensus-critical logic.

The test corpus is itself a constitution-protected artifact: its hash is committed at genesis (the post-excision Monero test suite minus all RingCT/Bulletproof/multisig tests) and evolves only through the same `reduce(ΔC)` mechanism.

---

## 7. Transition predicate

```
N_trans = first n such that  ΔH_observed(n) / |ΔC_observed(n)|  >  θ · A_avg(n)
```

`ΔH_observed(n)` and `|ΔC_observed(n)|` are the moving-average reduction rate and patch sizes over the last `K_trans = 1024` accepted reduce-txs. `A_avg(n)` is the moving average of `A(B_n)` over the same window.

Once satisfied:
- The PoA terms (`α`, `γ`) deprecate to zero immediately and irreversibly.
- The reward formula switches to the PoR branch.
- A hard-fork rule set is auto-activated. There is no governance vote — the predicate is the vote.
- An on-chain marker tx records `N_trans`, the deciding patch hash, and a snapshot of the activity ledger.

Reversibility: none. The predicate must be tunable only via the same reduction mechanism — i.e., a patch that lowers `θ` is itself admissible only if it reduces codebase entropy. Inflation-via-θ-tuning is therefore self-defeating.

---

## 8. Self-modifying binary safety: canary-then-promote

We do **not** live-replace the running binary. Live execve hand-off as written in the original spec is rejected: too brittle, too easy to brick the network. Instead:

1. `reduce(ΔC)` tx is accepted and recorded in the cumulative reduction Merkle root at height `n`.
2. Designated canary nodes (configured via `--canary` flag at startup; an opt-in role) compile and run the patched binary against live mainnet traffic in a sandboxed parallel process.
3. For `K_canary = 2016` blocks, the canary process must:
   - Stay in sync with the main chain.
   - Emit no consensus-divergence reports.
   - Pass `tests/invariants/` continuously.
4. At `n + K_canary`, if no canary failures recorded, the patch promotes — every node downloads the verified binary blob (or rebuilds from source under the pinned toolchain) and atomic-swaps on next process restart.
5. Failure during canary period: the patch is reverted; the issuer's staked credit is slashed; an incident marker is recorded.

Reproducible builds: the toolchain Merkle leaf (compiler version + flags + libc + linker hashes) is committed at genesis (`genesis/toolchain.merkle.json`). Patches that change the toolchain are themselves valid `reduce(ΔC)` txs subject to canary review.

**Insight (operator's manifesto §II):** the modification mechanism is dumber than the modified target. The `reduce(ΔC)` tx kind is intentionally minimal — patch hash, parent hash, entropy delta, signature, canary window. No DSL, no Turing-complete migration scripts. Mutation is bounded and typed.

---

## 9. Block-header expansion

Two new fields appended to `block_header`:

```
crypto::hash cumulative_reduction_root;  // Merkle root of all accepted reduce-txs to height n
crypto::hash activity_ledger_hash;       // hash of A-ledger snapshot at height n
```

Both included in the proof-of-work hash input. Genesis values are `0x00…00`. Light clients verify the entire reduction proof chain via Merkle proofs alone — they do not need to recompile.

---

## 10. Privacy reduction — what survives

Surviving privacy primitives:

- **Stealth addresses** (one-time public keys derived from the recipient's view+spend pubkeys). Optional, expressed as pay-to-script-hash so future zk-SNARK upgrades plug in without new tx kinds.
- Nothing else.

Excised:

- RingCT / Bulletproofs / Bulletproofs+ — entire `src/ringct/`.
- Ring signatures (mixin/decoy selection) — `txin_to_key.key_offsets` field deleted; ring construction code in `cryptonote_tx_utils` and `wallet2` deleted.
- View tags — `txout_to_tagged_key` struct deleted.
- Multisig — entire `src/multisig/`.
- Seraphis prep — entire `src/seraphis_crypto/`.
- Trezor RingCT path — `src/device_trezor/` mostly deleted (HW-wallet hooks deferred).
- All tests exercising the above.

Threat-model honesty: Moire amounts and chain graph are **transparent**. Sender/recipient linkability is broken only by stealth addresses (each tx output goes to a fresh key). Anyone running a node sees the full ledger. This is not Monero-grade privacy. It is **Bitcoin-grade transparency + better receiver privacy**, deliberately — because monetary auditability is the point of digital gold. If you want anonymity, run a Tor mixer client; do not bake mixing into the consensus rules.

---

## 11. State machine and on-chain ledger

| Column | Purpose |
|---|---|
| `blocks` | (existing) full block storage |
| `txs` | (existing) full tx storage |
| `key_images` | (existing) double-spend prevention |
| `reduction_ledger` | new: `(parent_hash, child_hash, ΔH, patch_blob_hash, signature, canary_start, canary_end_status)` |
| `activity_ledger` | new: `(height, V_tx, R_contrib, P_stake, A_combined)` rolling window |
| `toolchain_pin` | new: current toolchain Merkle leaf |

LMDB schema additions in `src/blockchain_db/lmdb/db_lmdb.{h,cpp}`. RingCT-specific columns deleted.

---

## 12. Bootstrap

- Genesis block = dual-oracle definition + zero pre-mine + initial constitution + initial toolchain pin.
- PoA phase begins at height 1.
- RandomX retained as PoW for PoA phase only. Deleted automatically (via reduction pressure) after `N_trans + K_PoW_drain`.
- Post-cap security budget = transaction fees + optional external PoR bounties (off-chain). The protocol does not pay miners after R_n → 0.

---

## 13. Failure model & mitigations

| Failure | Mitigation |
|---|---|
| Adversarial "reduction" by deleting consensus logic | Behavioral-equivalence floor (§6) |
| Brittle live-replace bricks the network | Canary-then-promote (§8) |
| Inflation via θ-tuning | θ change is a `reduce(ΔC)` tx; subject to entropy reduction floor |
| Stake capture of `P_stake` term | `γ = 0.1` cap; deprecated at `N_trans` |
| Non-deterministic builds across machines | Pinned toolchain Merkle leaf in genesis; canary verifies build hash |
| Brotli/AST oracle drift | Tree-sitter and brotli versions pinned at genesis; their hashes are toolchain leaves |
| Reduction-ledger corruption | Append-only LMDB column with per-segment checksums |
| Rich-get-richer in canary-node selection | Canary role is opt-in; minimum 4 distinct canary peer ASNs required for promotion |

---

## 14. Formal spec block (excerpt — full file in `genesis/spec.lean`)

```lean
namespace Moire

structure GenesisParams where
  k       : Nat       := 7480000000000  -- atomic units / block, base scalar
  lambda  : Float     := 3.5622e-7      -- per-block decay
  theta   : Float     := 2.0            -- transition threshold
  alpha   : Float     := 0.5            -- PoA weight: V_tx
  beta    : Float     := 0.4            -- PoA weight: R_contrib
  gamma   : Float     := 0.1            -- PoA weight: P_stake
  epsilon : Float     := 1e-6           -- activity floor
  blockTime : Nat     := 60             -- seconds
  kCanary : Nat       := 2016           -- blocks
  weights : Float × Float × Float := (0.6, 0.3, 0.1)  -- Brotli, AST, proof

def Activity (Vtx Rc Ps : Float) (p : GenesisParams) : Float :=
  Float.max p.epsilon (Float.min 1.0 (p.alpha * Vtx + p.beta * Rc + p.gamma * Ps))

def Reward (n : Nat) (A H_grad : Float) (transitioned : Bool) (p : GenesisParams) : Float :=
  let envelope := Float.exp (- p.lambda * n.toFloat)
  let pivot    := if transitioned then H_grad else A
  (p.k.toFloat) * pivot * envelope

theorem Reward_nonincreasing_in_n (n m : Nat) (h : n ≤ m) (A H : Float) (t : Bool) (p : GenesisParams) :
    Reward m A H t p ≤ Reward n A H t p := by
  -- expanded in genesis/spec.lean
  sorry

theorem Reward_bounded_by_PoA_envelope (n : Nat) (A H : Float) (p : GenesisParams)
    (h_predicate : H ≤ p.theta * A) :
    Reward n A H true p ≤ p.theta * Reward n A 0 false p := by
  -- expanded in genesis/spec.lean
  sorry

end Moire
```

The `sorry`s are deliberate placeholders. Hermes (or a follow-on formal-methods session) discharges them. The constants, definitions, and theorem statements are part of the constitution.

---

## 15. What this design *does not* do

- No GPU mining tuning. RandomX as-is.
- No L2 / lightning analogue. Base layer is the product.
- No on-chain governance. The transition predicate **is** the governance.
- No staking yield. `P_stake` is a sybil-attestation signal, not a yield mechanism.
- No DEX, no smart-contract VM. Moire is money. Money does one thing.

---

## 16. Bundled client (node + miner + wallet + chat)

A single binary, `moire-client`, surfaces all four operator-facing
functions as panes of one ImGui application. The headless `moired` and
`moire-wallet-cli` binaries continue to ship for ops/automation.

Stack: Dear ImGui + GLFW. Reasons: single source tree, deterministic
cross-platform rendering, ~32 kLOC total for the UI runtime (both vendor
as submodules with hashes pinned in the toolchain manifest), and trivial
deletion path under the reduction gradient.

Chat is a fourth pane in this client, **not a separate process and not on
chain**. It's an IRC-flavored, decentralized, gossip-borne overlay on the
existing P2P layer. Identity is derived from the wallet spend-key
(`chat_seed = sha256("moire-chat" || spend_secret)`); nicks are
deterministic vanity prefixes. Channels are unowned. Opcodes mirror RFC
1459's minimal set: JOIN/PART/PRIVMSG/NOTICE/TOPIC/NAMES/LIST/DIRECT/ME.
Messages carry a TTL (default 144 blocks ≈ 2.4 h) and are dropped after
expiry — no persistent backlog, like IRC.

Both the GUI and the chat protocol are **layer-7**: they don't enter
consensus, they don't affect issuance, they don't appear in the
constitution. They evolve under the same `reduce(ΔC)` gradient as every
other line of source under `canon(C)`.

Full spec: `docs/gui_chat.md`.

## 17. Mapping to the operator's manifesto (CB v0.4)

- **Self-replicating firmware (§II):** PoR + canary = bounded-mutation kernel. `reduce(ΔC)` tx is the proposal envelope; auditor quorum = test corpus + canary nodes; mutator is the PoR oracle.
- **Deterministic art ledger (§III):** every `reduce(ΔC)` tx is an artifact with manifest, lineage (`parent_codebase_hash`), proof (test pass + canary), signature.
- **Build-farm cinema (§IV):** the canary-node fleet IS a build farm; each promotion is a deterministic build job with on-ledger proof.
- **Compute economy as narrative (§V):** PoA `R_contrib` term + PoR rewards = credit decay + freshness baked into protocol.
- **Studio sim (§VI):** roadmap.md week 6 — wire the studio simulator to the Moire testnet so in-game "release" maps to real testnet `reduce(ΔC)` txs.
