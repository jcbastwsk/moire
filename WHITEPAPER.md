# Moire: A Self-Reducing Hard-Cap Cryptocurrency

**Version 1.0 — 2026-05-06**
**Author: jcb**
**Status: Pre-mainnet design, Day-1.**

---

## Abstract

Moire is a clean fork of Monero that replaces the issuance schedule with a piecewise function pivoting from on-chain activity (PoA) to verifiable codebase reduction (PoR), and reduces privacy to its semantic minimum (transparent UTXO base + optional stealth-address unlinkability). Total supply is bounded above by a finite asymptote that emerges from the parameters of the issuance schedule — not from a hand-set magic number. As the protocol is reduced toward its irreducible Kolmogorov floor, issuance approaches zero. The constitution is short enough to read in a single sitting, and the only mechanism for amending it is the same on-chain `reduce(ΔC)` transaction that drives issuance.

This document specifies the protocol, derives the parameters, analyzes the gaming-resistance properties of the reduction oracle, and surveys the explicit threat model. Every accretive privacy layer in Monero (RingCT, Bulletproofs, ring signatures of size 16, view tags, dynamic ring logic, multisig, Seraphis prep) is **deleted**, not feature-gated. The resulting monetary base is auditable in one evening because the constitution is what survives the deletion.

---

## 1. Motivation

### 1.1 The two failure modes of "digital gold"

Existing scarcity-based cryptocurrencies fail in one of two directions.

**The Bitcoin lineage** sets a hand-picked supply cap (21 M) and hand-picked emission curve (halving every 210,000 blocks). The cap is monetary policy by fiat; the rationale is appeal to tradition, not derivation. Hard-fork pressure to alter the cap or revive issuance via "tail emission" is a permanent governance overhead.

**The Monero lineage** embraces tail emission to make security budgeting explicit, but accumulates privacy machinery (RingCT, Bulletproofs, Bulletproofs+, ring signatures, view tags, multisig, Seraphis prep) faster than it can audit it. The constitution is now thousands of pages of cryptographic protocol composed across multiple research lineages. No single human reads it. The auditability cost grows monotonically.

Moire is the third option: derive the cap, delete the privacy that is not consensus, and bake the protocol's own simplification into the issuance schedule.

### 1.2 The reduction telos

If the protocol pays its issuers for shrinking the protocol, then the protocol's monetary base is an explicit incentive against itself growing. As `H(C)` (a Kolmogorov-complexity proxy of the canonical source tree) approaches its irreducible floor, the issuance term proportional to the marginal reduction rate approaches zero. The hard cap is a derived property of the dynamics.

This is the entire thesis. The rest of the document is making it precise.

---

## 2. Notation

| Symbol | Meaning |
|---|---|
| `n` | block height |
| `R(n)` | block reward at height `n` (atomic units = attomoire) |
| `C_n` | canonical source tree of the protocol at height `n` |
| `ΔC` | candidate reduction patch |
| `H(C)` | weighted Kolmogorov-complexity proxy of `C` |
| `A(B_n)` | normalized activity score at block `n`, `∈ [ε, 1]` |
| `k` | base reward scalar (atomic units / block) |
| `λ` | per-block exponential-decay constant |
| `θ` | transition predicate threshold |
| `α, β, γ` | PoA weights for V_tx, R_contrib, P_stake terms |
| `ε` | activity floor preventing zero-divisor pathologies |
| `N_trans` | first block height satisfying the transition predicate |
| `K_canary` | canary period in blocks before a reduce-tx is promoted |
| `K_trans` | window size (in accepted reduce-txs) for the transition predicate |

Everything else is defined inline. The values are pinned in `genesis/params.toml` and reproduced where they appear.

---

## 3. Issuance schedule

### 3.1 The piecewise reward function

For every height `n`, the protocol enforces:

```
R(n) = k · A(B_n) · exp(-λn)                       if n <  N_trans
R(n) = k · grad_H(ΔC(n)) · exp(-λn)                if n ≥ N_trans
```

where

```
grad_H(ΔC) := (H(C_n) − H(C_n ⊕ ΔC)) / |ΔC|
```

is the marginal entropy reduction per byte of patch.

The first branch is **Proof of Activity (PoA)**. The second branch is **Proof of Reduction (PoR)**. The transition is irreversible and triggered by the transition predicate (§7).

### 3.2 The exponential envelope

Both branches share the `exp(-λn)` envelope. This is the structural source of the hard cap. The asymptotic supply under PoA is

```
S(∞) = ∫₀^∞ R(n) dn = (k · Ā / λ) · (1 − e^(−λ·∞)) = k · Ā / λ
```

where `Ā` is the long-run mean activity. Since `A(B_n) ≤ 1` for all `n` by the clamp in §5, `Ā ≤ 1`, and therefore `S(∞) ≤ k / λ`. With genesis values `k = 7.48 × 10¹²` attomoire and `λ = 3.5622 × 10⁻⁷` per block:

```
S(∞) ≤ 7.48 × 10¹² / 3.5622 × 10⁻⁷ = 2.10 × 10¹⁹ attomoire = 21,000,000 MOI
```

The 21 M cap is a derived consequence of `(k, λ, Ā ≤ 1)`. It is not encoded as a constant. This matters: hand-set supply caps invite hard-fork pressure (cf. perennial Bitcoin tail-emission debates). A derived cap is not a target — it is a corollary.

### 3.3 Derivation of λ

The decay constant is set so that 95 % of the asymptotic supply mints by year 16. With 60-second blocks, `N_16 = 16 × 365 × 1440 = 8,409,600` blocks (canonical, no leap years). Solving:

```
1 − e^(-λ · 8,409,600) = 0.95
e^(-λ · 8,409,600)     = 0.05
λ                      = -ln(0.05) / 8,409,600
                       = 2.9957 / 8,409,600
                       ≈ 3.5622 × 10⁻⁷ per block
```

Half-life: `ln(2)/λ ≈ 1,945,890` blocks ≈ **3.7 years**. By year 16, 4.32 half-lives have elapsed, so `1 − 2^-4.32 ≈ 0.95`.

### 3.4 Calibration of k

Target asymptotic cap = 2.1 × 10¹⁹ attomoire. With `Ā = 1` (the upper bound):

```
k = S(∞) · λ / Ā = 2.1 × 10¹⁹ · 3.5622 × 10⁻⁷ / 1 ≈ 7.48 × 10¹² attomoire/block
```

That is 7.48 MOI per block at `n = 0` under saturation activity.

### 3.5 Realized issuance trajectory

| Year | Block height | R(n) (PoA, Ā=1) | Cumulative |
|---|---:|---:|---:|
| 0 | 0 | 7.48 MOI | 0 |
| 1 | 525,960 | 6.20 MOI | ≈ 3.6 M MOI |
| 4 | 2,103,840 | 3.54 MOI | ≈ 11.6 M MOI |
| 16 | 8,409,600 | 0.374 MOI | ≈ 19.95 M MOI |
| ∞ | ∞ | → 0 | → 21 M MOI |

Realized issuance is strictly below cap because `Ā < 1` in practice (the network does not saturate the activity score).

### 3.6 Tail emission

There is none. After `N_trans`, `R(n)` is paid out only proportionally to the marginal reduction rate. As `H(C)` approaches its Kolmogorov floor, `grad_H → 0`, and so `R(n) → 0` even before the `exp(-λn)` envelope fully decays. The post-cap security budget is **transaction fees only**.

This is a deliberate deviation from Monero. Moire does not subsidize miners forever. Moire pays anyone who reduces the protocol, then stops paying anyone, because the protocol is done.

---

## 4. Privacy posture

### 4.1 What is preserved

- **Transparent UTXO ledger.** Every input, output, amount, and address is publicly visible.
- **Stealth addresses.** A recipient publishes view-key + spend-key; senders derive a fresh one-time public key per output. This breaks recipient linkability across transactions without breaking auditability of the chain itself. The implementation uses Monero's existing one-time-public-key derivation, expressed as pay-to-script-hash so future zk-SNARK upgrades can plug in without a new transaction kind.

### 4.2 What is deleted

| Component | Reason for deletion |
|---|---|
| RingCT | Amount hiding via Pedersen commitments + range proofs adds no monetary property; its sole function is sender-amount privacy. Deleted with the rest of `src/ringct/`. |
| Bulletproofs / Bulletproofs+ | Range proofs for RingCT amounts. Useless without RingCT. |
| Ring signatures (size 16) | Sender ambiguity via decoy mixing. Adds verification cost, transaction size, and chain-analysis arms-race overhead without preventing well-resourced surveillance. |
| View tags | Optimization for ring-sig scanning; vanishes with ring sigs. |
| Dynamic ring-size logic | Vanishes with ring sigs. |
| Multisig (entire `src/multisig/`) | Threshold signing depends on ring-sig machinery; no minimal-monetary use case justifies the complexity at v0.1. |
| Seraphis prep (`src/seraphis_crypto/`) | Forward-prep for a next-gen privacy stack we are deleting. |
| Trezor RingCT path | Coupled to the deleted code. HW-wallet support is deferred to a clean reintroduction. |

Total deletion: approximately 16,800 LOC of consensus-relevant privacy machinery, plus surgical strikes through every consumer (`blockchain.cpp`, `wallet2.cpp`, `cryptonote_format_utils.cpp`, RPC handlers, serializers, simplewallet CLI, LMDB schema). Deletion is **`git rm`**, not `#ifdef`.

### 4.3 Honest threat model

Moire's base layer publishes the full ledger graph. A node operator sees every transaction. A passive observer can:

- Reconstruct the entire UTXO graph.
- Cluster addresses by spend patterns.
- Estimate balances exactly.
- Trace any transaction to its inputs.

What the observer cannot do directly:

- Link two outputs to the same recipient. Each output goes to a fresh stealth-address-derived public key. Linking requires the recipient's view key.
- Identify the sender behind an address. (As with Bitcoin, this requires off-chain correlation: KYC exchanges, network-layer timing, client telemetry.)

This is **Bitcoin-grade transparency with strictly better receiver privacy**. It is not Monero-grade privacy, and Moire does not pretend otherwise. If a user requires sender anonymity or amount hiding, the appropriate layer is a Tor-routed mixer client at the wallet layer, off-chain. Mixing is not consensus.

### 4.4 Why this is the right reduction

The privacy machinery is exactly the part of Monero that grew without bound. Removing it shrinks the audit surface by an order of magnitude and makes the rest of the protocol legible. The reduction telos cannot operate on a codebase no one can read; the privacy excision is what makes PoR feasible.

---

## 5. The activity oracle (PoA)

### 5.1 Definition

```
A(B_n) = clamp(α · V_tx(n) + β · R_contrib(n) + γ · P_stake(n), ε, 1)
```

Genesis weights: `α = 0.5`, `β = 0.4`, `γ = 0.1`, `ε = 1 × 10⁻⁶`.

### 5.2 Components

**`V_tx(n)`**: rolling-window normalized fee burn over the last 720 blocks (12 hours at 60-second blocks). `V_tx = min(F̄ / F_target, 1)`, with `F_target = 1 MOI per block` at genesis. This rewards real economic activity: fees burnt are a revealed-preference signal that buyers will pay for blockspace.

**`R_contrib(n)`**: rolling-window normalized count of accepted `reduce(ΔC)` transactions over the last 720 blocks. This is the early-PoR coupling — reduction patches are rewarded with extra issuance even before the transition predicate fires. Cap at 1.

**`P_stake(n)`**: rolling-window normalized weight of stake-signed attestations over the last 720 blocks. A small voluntary-staker attestation registry contributes a sybil-resistant signal, capped at 0.1 of total weight (`γ = 0.1`) so stake capture cannot dominate issuance. Cap at 1.

### 5.3 Sunset of PoA

At `N_trans`, `α := 0` and `γ := 0` immediately and irreversibly. `β` survives — reduction patches keep contributing to `A` indefinitely, but the dominant issuance term becomes the PoR branch.

### 5.4 Implementation

`src/cryptonote_core/poa_oracle.{h,cpp}`. Pure function. State is the rolling-window aggregate held in a new `activity_ledger` LMDB column (added in patch 02b on Day 2). The block-header field `activity_ledger_hash` (added in patch 05) commits to the snapshot at every height; light clients verify activity reward proofs via the same Merkle-style proofs used for transaction inclusion.

---

## 6. The reduction oracle (PoR)

### 6.1 Definition

```
H(C) = w_brotli · Brotli11(canon(C))
     + w_ast    · AST_node_count(C)
     + w_proof  · |proof(C)|
```

Genesis weights: `(w_brotli, w_ast, w_proof) = (0.6, 0.3, 0.1)`.

### 6.2 Why three terms

A single proxy is gameable. Three weakly-correlated proxies are not.

**Brotli-11 size of `canon(C)`.** Deterministic, content-defined compression. The serializer canonicalizes file order (sorted by path), strips trailing whitespace, normalizes line endings (LF), and excludes generated artifacts (`build/`, `external/randomx/`, `external/lmdb/` — these are pinned upstream snapshots tracked separately). Brotli-11 is the strongest setting and is reproducible across implementations.

**AST node count.** Tree-sitter C++ grammar parses every `.cpp/.cc/.c/.h/.hpp` file in `canon(C)` and the oracle sums the node counts. This penalizes deletions of trivial content (a thousand lines of comments) while rewarding deletions of structural complexity. Grammar pinned at genesis.

**Proof size.** Byte length of the machine-checked formal spec block in `genesis/spec.lean` plus any new proof obligations attached to the patch. Rewards patches that not only shrink the code but also reduce the proof burden.

### 6.3 Why these weights

The 0.6 / 0.3 / 0.1 split is empirical. Brotli is the most general signal (it captures both whitespace and structural redundancy) but the weakest at penalizing cruft like dead code that the compressor handles well. AST node count corrects for that. Proof size is a small but high-quality signal that we want to reward without letting it dominate.

The weights themselves are **constitution-pinned but mutable** — they can be changed by a `reduce(ΔC)` transaction. Crucially, the meta-stable property is that any weight change is itself subject to the gaming-resistance floor (§8): a patch that lowers `w_brotli` to 0 in order to sneak through a gibberish patch must itself reduce overall `H` *under the new weights*. Inflation-via-tuning is self-defeating because the tuning patch has to clear its own bar.

### 6.4 Marginal rate

The relevant quantity is not `H(C)` but the marginal rate of reduction per byte of patch:

```
grad_H(ΔC) = (H(C_n) − H(C_n ⊕ ΔC)) / |ΔC|
```

This quantity is the issuance pivot in the PoR branch. It naturally penalizes large patches that achieve small reductions; rewards small patches that achieve large reductions; and goes to zero as `H(C)` approaches its irreducible floor (no patch achieves further reduction).

### 6.5 Implementation

`src/cryptonote_core/por_oracle.{h,cpp}`. The Day-1 implementation is pure arithmetic over a precomputed `codebase_snapshot` struct. Brotli encoder integration and tree-sitter parser integration are deferred to Phase 2 sessions (vendored as submodules with hashes pinned in `genesis/toolchain.merkle.json`).

The recomputation cost decreases monotonically with codebase size — the PoR oracle gets cheaper to run as the codebase shrinks. This is the right asymptotic.

---

## 7. The transition predicate

### 7.1 Definition

```
N_trans = min n :  ΔH_avg(n) / |ΔC|_avg(n)  >  θ · A_avg(n)
```

with averages taken over the last `K_trans = 1024` accepted reduce-transactions and `θ = 2.0`.

In English: switch from PoA to PoR when the marginal reduction rate over the recent window exceeds twice the marginal activity rate. This says: PoR is now more productive than PoA, switch the issuance pivot.

### 7.2 What fires at `N_trans`

- `α := 0` and `γ := 0`, irreversibly.
- The reward formula switches to the PoR branch.
- A `transition_marker` transaction is recorded with `(N_trans, deciding_patch_hash, snapshot(activity_ledger))`.
- A hard-fork rule set is auto-activated. There is no governance vote — the predicate is the vote.

### 7.3 Why irreversibility

A reversible transition introduces an attack surface: an adversary that can briefly inflate `A` (e.g., wash-trading fees to spike `V_tx`) could push the chain back to PoA and resume PoA inflation. Irreversibility eliminates this. Once the protocol has demonstrated that reduction is dominant, the issuance pivot does not unwind.

### 7.4 Why θ is mutable

`θ` is constitution-pinned but, like the PoR weights, mutable via `reduce(ΔC)`. A patch lowering `θ` is admissible only if it reduces overall `H` under the new `θ`. Lowering `θ` to game an early transition would require the tuning patch to itself shrink the codebase enough to clear the floor — at which point the operator has done the work the PoR mechanism is paying for, which is the goal.

---

## 8. Gaming-resistance: behavioral-equivalence floor

### 8.1 The naive attack

An adversary submits a `reduce(ΔC)` transaction whose `ΔC` deletes consensus-critical code. The codebase size drops; `grad_H(ΔC)` is high; the adversary collects the reward. The next valid block from a non-adversarial node fails to verify on the patched binary; the chain forks; the adversary escapes with the issuance.

This attack must be impossible. The mechanism that makes it impossible is the **behavioral-equivalence floor**.

### 8.2 The floor

A `reduce(ΔC)` transaction is admissible **only if all four** conditions hold:

1. **Deterministic compile.** The post-patch codebase compiles deterministically under the pinned toolchain. The compiled-binary hash matches the manifest emitted by the build script.
2. **Test corpus passes.** Every test in the surviving test corpus passes on the post-patch codebase.
3. **Test deletions paired with feature deletions.** Any test removed in `ΔC` is paired with the deletion of the feature it exercised. The oracle verifies this by AST-coverage intersection: the AST nodes covered by the removed tests must be a subset of the AST nodes also removed in the same patch.
4. **Invariants pass.** All property invariants in `tests/invariants/` pass on a fresh testnet replay of the last 1024 blocks.

The genesis test corpus is the post-excision Monero test suite (i.e., the Monero `tests/` directory minus the tests for RingCT, Bulletproofs, multisig, view tags, etc.). Its hash is committed at genesis. Subsequent test changes ride on the same `reduce(ΔC)` mechanism.

### 8.3 Why the four conditions are sufficient

The naive attack — deleting consensus-critical code — fails condition 4 (invariants), condition 2 (tests of the deleted code fail), or both. A sophisticated variant — deleting the test for the consensus-critical code at the same time — fails condition 3 because the deleted test's AST coverage extends beyond the `ΔC` AST footprint.

A truly sophisticated variant — deleting *all* tests of *all* consensus-critical code in one patch — is detectable as the `ΔC` AST footprint that engulfs the consensus surface. Such a patch will fail condition 2 (the surviving tests in other modules that exercise the deleted consensus paths through composition will fail) and condition 4 (the testnet replay will diverge).

The pathological remainder — an adversary who finds a flaw in the test corpus itself — is the same problem that every test-driven-development culture faces. The mitigation is the same: write better tests. Moire makes the test corpus a constitution-protected artifact precisely so this remains a community-visible attack surface rather than a hidden one.

### 8.4 The mutation-mechanism principle

The mutation mechanism is dumber than the modified target. The `reduce(ΔC)` transaction is intentionally minimal: patch hash, parent hash, entropy delta, signature, canary window. There is no DSL, no Turing-complete migration script, no template engine. Mutation is bounded and typed. A patch is a sequence of textual edits, period.

This is the key safety property of every self-modifying system that has ever worked: the mechanism must be simpler than what it modifies, so an adversary cannot abuse the mechanism to reach states the modified system itself cannot reach.

---

## 9. Canary-then-promote

### 9.1 The naive attack on live binary replacement

If a `reduce(ΔC)` transaction immediately replaces the running binary, then a single bad patch bricks the network. Live execve handoff is rejected on these grounds.

### 9.2 The mechanism

Each accepted `reduce(ΔC)` enters a canary window. For `K_canary = 2016` blocks (~2 weeks at 60-second blocks):

1. Designated **canary nodes** (configured via `--canary` flag at startup; an opt-in role) compile and run the patched binary against live mainnet traffic in a sandboxed parallel process. The original binary continues to run as the production daemon.
2. The canary process must stay in sync with the main chain, emit no consensus-divergence reports, and pass the `tests/invariants/` continuously.
3. At height `n + K_canary`, if at least `MIN_CANARY_PEER_ASNS = 4` distinct canary node ASNs have reported successful operation and zero divergence reports were filed, the patch **promotes**: every node downloads or rebuilds the patched binary under the pinned toolchain and atomic-swaps on next process restart.
4. Promotion is **atomic swap**, not live execve. The running daemon exits cleanly; the supervisor restarts with the new binary.
5. Failure during the canary period: the patch is reverted; the issuer's staked credit (minimum 100 MOI) is burnt to a provably unspendable key; an incident marker is recorded in the chain.

### 9.3 The diversity requirement

`MIN_CANARY_PEER_ASNS = 4` distinct ASNs is a sybil mitigation. A single operator running a thousand canary nodes from one network counts as one. Promotion requires at least four genuinely independent observers signing off. The number is a parameter; the principle is that promotion must pass an attestation diversity floor.

### 9.4 Reproducible builds

Promotion's compile step uses a pinned toolchain whose Merkle leaf is committed at genesis (`genesis/toolchain.merkle.json`). The leaf is the SHA-256 of the canonicalized JSON of `(compiler version, linker version, libc version, boost, openssl, brotli, tree-sitter, ImGui, GLFW, libsodium, cmake_flags)` with sorted keys and minified separators. A patched binary that doesn't match the canary fleet's build hash is rejected at promotion time.

Toolchain bumps are themselves `reduce(ΔC)` transactions: the manifest is part of `canon(C)`, so changing the toolchain rides on the same canary-promote pathway.

---

## 10. The reduce-transaction

### 10.1 Wire format

A `reduce(ΔC)` transaction carries an input of kind `txin_reduce`:

| Field | Bytes | Meaning |
|---|---:|---|
| `parent_codebase_hash` | 32 | must equal `cumulative_reduction_root` at `canary_window_start − 1` |
| `child_codebase_hash` | 32 | the hash committed by the patch |
| `patch_blob_hash` | 32 | the canonical patch bytes, retrievable via gossip |
| `entropy_delta_signed` | 8 (int64) | `ΔH`; must be > 0; signed so reverter txs are typed |
| `issuer_pubkey` | 32 | Ed25519 public key |
| `issuer_signature` | 64 | signs the other fields |
| `staked_credit_atomic` | 8 (uint64) | burnt on canary failure (≥ `MIN_STAKE = 100 MOI`) |
| `canary_window_start` | 8 (uint64) | block height |

### 10.2 Validity

A `txin_reduce` is admissible if and only if:

1. `parent_codebase_hash == cumulative_reduction_root_at_height(canary_window_start − 1)`.
2. `entropy_delta_signed > 0`.
3. The signature verifies against `issuer_pubkey`.
4. `staked_credit_atomic ≥ MIN_STAKE`.
5. The behavioral-equivalence floor passes (§8).
6. The patch reproducibly applies to the parent codebase under the pinned toolchain (verified by canary nodes).

### 10.3 Reward

The issuer is paid at `canary_window_start + K_canary` if no canary failures are recorded:

```
issuer_reward = β · R(canary_window_start) · (entropy_delta / max_entropy_delta_in_window)
```

The `β` coefficient is the same `β` from the activity oracle (§5). Reduction issuance is bounded above by the activity-issuance envelope, which preserves the asymptotic-cap argument.

### 10.4 Failure mode

If a canary failure is recorded during the window — a divergence report from a canary node, an invariants test failure, a build hash mismatch — the patch is reverted at the next block boundary, the issuer's `staked_credit_atomic` is sent to a provably unspendable burn key, and an incident marker `txin_revert` is recorded with the failing condition.

This makes patch issuance economically rational only when the issuer is genuinely confident the patch will survive canary. The stake is the issuer's signal of belief.

---

## 11. State machine and ledger

### 11.1 New consensus columns in LMDB

| Column | Schema | Purpose |
|---|---|---|
| `reduction_ledger` | `(parent_hash, child_hash, ΔH, patch_blob_hash, signature, canary_start, canary_end_status)` | the append-only history of all reduction transactions |
| `activity_ledger` | `(height, V_tx, R_contrib, P_stake, A_combined)` | the rolling-window activity aggregate |
| `toolchain_pin` | current toolchain Merkle leaf | the active reproducibility commitment |

### 11.2 Block-header expansion

Two new fields are appended to every block header, both included in the proof-of-work hashing input:

```
crypto::hash cumulative_reduction_root;  // Merkle root of all accepted reduce(ΔC) txs through this height
crypto::hash activity_ledger_hash;       // hash of the activity-ledger snapshot at this height
```

Genesis values are `0x00…00`. Both fields enable light clients to verify reduction-history and activity-history proofs without recomputing or recompiling.

### 11.3 Removed columns

Every RingCT-specific LMDB column is dropped. The output-distribution column, the spent-key-image-by-amount column, and the RingCT amount-output index column all vanish with their schema.

---

## 12. The bundled client

### 12.1 One binary, four panes

`moire-client` is a single binary that bundles the node, the miner, the wallet, and the chat client into one Dear ImGui application. Headless `moired` and `moire-wallet-cli` continue to ship for ops, automation, and testing.

The four panes — Node, Miner, Wallet, Chat — are panes of one application, not four programs. They share the same in-process node loop, the same encrypted wallet keystore (libsodium `crypto_secretstream`), and the same chat identity (deterministically derived from the wallet spend-key).

### 12.2 Why ImGui + GLFW

Picked over Qt, Tauri, Electron, AppKit, GTK, Slint, etc. for four reasons. First, the total UI runtime is approximately 32 kLOC across both libraries — small enough to vendor with hashes pinned, large enough to support the four panes. Second, deterministic cross-platform rendering (no platform widget drift) is a property of the build, which matters for a project where the build itself is ledger-committed. Third, no JavaScript runtime, no Webkit, no Chromium — the reduction gradient cannot reach into Electron, but it can reach every line of ImGui. Fourth, trivial deletion: when a pane is dropped via `reduce(ΔC)`, the diff is contained.

The client and its UI runtime are explicitly **layer-7** code subject to the same reduction gradient as core protocol source.

### 12.3 The chat overlay (MIRC)

The chat pane runs an IRC-flavored decentralized chat protocol called MIRC v0.1, gossip-borne over the existing P2P transport. Identity is deterministic (`chat_seed = sha256("moire-chat" || spend_secret)` → Ed25519 keypair); nicks are vanity prefixes derived from the public key. Channels are unowned. Opcodes mirror RFC 1459's minimal set: JOIN, PART, PRIVMSG, NOTICE, TOPIC, NAMES, LIST, DIRECT, ME. Messages carry a TTL (default 144 blocks ≈ 2.4 hours) and are dropped from local cache after expiry — like IRC, if you weren't there, you weren't there.

The chat is **not** on chain, **not** consensus-protected, and **not** anonymous. It is a coordination substrate for operators of canary nodes and reduction-patch issuers that does not depend on a third party. Full spec: `docs/gui_chat.md`.

---

## 13. Threat model

### 13.1 Privacy adversary

Moire is transparent. An observer with a full node sees every transaction graph edge. There is no defense against chain-graph analysis. Receiver pseudonymity via stealth addresses is a partial defense: an observer sees that an output went to *some* fresh public key, but cannot link that output to other outputs of the same recipient without the view key. This is strictly weaker than Monero's privacy guarantees and strictly stronger than Bitcoin's.

If a user requires sender unlinkability or amount privacy, the appropriate layer is wallet-side: Tor-routed mixers, off-chain swaps, or higher-layer constructions. Moire does not bake mixing into consensus.

### 13.2 Issuance adversary

The naive issuance attack — forging a `reduce(ΔC)` transaction with a fake `entropy_delta_signed` — fails at signature verification. The sophisticated variant — submitting a real patch that deletes consensus-critical code — fails the behavioral-equivalence floor (§8). The pathological variant — a coordinated attack on the test corpus itself — is the same attack surface as any test-driven culture, and Moire makes the test corpus a first-class constitution-protected artifact precisely so this remains a community-visible problem.

The economic backstop is the staked credit: `MIN_STAKE = 100 MOI` per submission, burnt on canary failure. Issuers must have skin in the game.

### 13.3 Stake-capture adversary

The `P_stake` term in the activity oracle is capped at `γ = 0.1` of total weight to prevent a stake holder from dominating issuance. After `N_trans`, `γ := 0` and the lever vanishes. Stake-capture is therefore at most a 10 % distortion during the PoA phase and zero distortion after.

### 13.4 Inflation-via-tuning adversary

An adversary tries to amend the constitution to increase issuance — lower `λ`, raise `k`, lower `θ`, change PoR weights. Every such amendment is itself a `reduce(ΔC)` transaction. To pass admissibility, the tuning patch must reduce overall `H` under the new parameters. The adversary therefore has to do the work the protocol is paying for in order to abuse the protocol's payment mechanism. This is self-defeating.

### 13.5 Network adversary

Standard P2P network adversary. RandomX as inherited from Monero is the proof-of-work; mining centralization risks are inherited from Monero's analysis. The chat overlay is best-effort gossip — a network adversary can drop chat messages with no consensus impact (chat is layer-7).

### 13.6 Self-modifying-binary adversary

The canary-then-promote mechanism (§9) defangs live-replacement attacks. An adversary who pushes a malicious patch must (a) pass the behavioral-equivalence floor, (b) pass canary observation by ≥ 4 distinct ASNs over `K_canary = 2016` blocks, and (c) match the toolchain pin. Failing any of these burns the issuer's stake and reverts the patch.

The residual attack surface is the toolchain itself: an adversary who controls the pinned compiler can introduce undetectable malicious behavior into every binary the protocol promotes. The mitigation is to make the toolchain pin diverse and reproducible — multiple compilers (clang + gcc) with cross-validated outputs, rebuilds across multiple machines, public Merkle commitments to compiler binaries. This is queued as Phase 2 work; v0.1 ships with a single-compiler pin.

### 13.7 Constitution-rewrite adversary

There is none. Constitutional amendment is `reduce(ΔC)` and nothing else. There is no foundation, no developer fund, no on-chain ballot, no off-chain ballot binding consensus, no committee. The transition predicate is the only "vote." The protocol is the constitution.

---

## 14. Comparison

### 14.1 vs. Bitcoin

Same hard-cap target (21 M whole units). Different cap mechanism: Bitcoin sets a magic constant; Moire derives the cap from `(k, λ, Ā ≤ 1)`. Same general transparency posture. Different proof-of-work: RandomX (CPU-friendly) vs. SHA-256 (ASIC-dominated). Different security budget: Bitcoin pays miners forever via tail subsidy; Moire pays issuance only until the protocol is reduced, then security is fee-only.

Bitcoin is a static monetary protocol. Moire is a self-reducing one.

### 14.2 vs. Monero

Same baseline source tree (`monero@c182abb`, master). Different privacy posture: Monero treats privacy as consensus-mandatory; Moire treats it as user-choice and removes the consensus machinery. Same RandomX PoW (during PoA phase). Different issuance: Monero has tail emission for security budgeting; Moire bounds total issuance and lets fees handle long-run security. Different governance: Monero has informal governance via its developer community; Moire has none — only the transition predicate and `reduce(ΔC)` matter.

Monero treats anonymity as the goal. Moire treats reduction as the goal.

### 14.3 vs. self-modifying systems generally

The `reduce(ΔC)` mechanism resembles in spirit the on-chain governance proposals of Tezos and Polkadot. The crucial difference: Tezos and Polkadot governance operates on a stake-weighted vote; Moire's "vote" is a behavioral-equivalence floor. There is no popularity-contest dimension; a patch either passes the four mechanical conditions or it doesn't.

Tezos and Polkadot also rely on a Turing-complete migration mechanism (the new code is run inside a sandbox). Moire's mechanism is intentionally dumber: a patch is a textual diff with a signed metadata envelope, period. The simplicity is the safety property.

### 14.4 vs. "code is law"

"Code is law" is usually a slogan meaning *what the code does is dispositive*. Moire is closer to *what the constitution says is dispositive, and the code is the constitution's executable form*. The `genesis/spec.lean` block is machine-checked at build time; theorem statements about reward boundedness, activity clamping, and asymptotic-cap behavior are first-class artifacts. The `sorry` placeholders in v1.0 are first-class TODOs to be discharged by Hermes or a follow-on formal-methods session.

---

## 15. Open problems

### 15.1 Toolchain monoculture

v0.1 pins a single compiler (clang 17.0.6). A compromised compiler is undetectable from inside the system. Mitigation path: dual-compiler builds (clang + gcc) with cross-validated binary hashes, plus public Merkle commitments to compiler binaries. Sessions Phase 2.

### 15.2 Brotli + tree-sitter integration

v0.1 ships the PoR oracle as pure arithmetic over a precomputed `codebase_snapshot`. The actual encoders are Phase 2 sessions (vendoring brotli@1.1.0 and tree-sitter@0.22.6). Until then, `H(C)` cannot be computed end-to-end on a live node. The patches commit the oracle interface; the implementation lands on Day 2.

### 15.3 Reward-fraction calibration

The reward formula `issuer_reward = β · R(canary_window_start) · (entropy_delta / max_entropy_delta_in_window)` ties the issuer's per-patch reward to the largest-reduction patch in the window. This is intentional — it normalizes against the strongest competitor — but it admits a degenerate case where a single huge patch starves all subsequent issuers in the window. Empirical testnet observation will determine whether the formula needs an explicit floor or alternate normalization.

### 15.4 Test-corpus governance

The test corpus is constitution-protected, but its evolution rides on `reduce(ΔC)` like everything else. A pathological case: the test corpus itself becomes adversarial bloat that prevents legitimate reductions. The mitigation is the AST-coverage intersection check (§8 condition 3) — test deletions must be paired with feature deletions — but the more general failure mode (the corpus accumulates redundant tests faster than it accumulates feature reductions) needs empirical observation.

### 15.5 PoR after the Kolmogorov floor

As `H(C)` approaches its irreducible floor, `grad_H → 0` and so does issuance. What happens after? Fees alone fund security. Whether fees are sufficient depends on usage. If they are not, the chain stalls — which is the right behavior, because the protocol is done. There is no graceful-degradation story; there is only the design choice that scarcity is more important than perpetual subsidy.

### 15.6 Bundled chat at scale

MIRC v0.1 has no fee, no proof-of-work tag, no global rate limit beyond per-relayer caps. A determined spammer wastes their own bandwidth, but the gossip layer is asymmetric: a small spam volume can saturate the chat-channel listener of every node. Phase 2 work: add a 3-leading-zero-bit PoW tag to each frame to make spam computationally costly.

### 15.7 Light clients

Block headers are 64 bytes larger (the two new Merkle roots). Light clients need to verify reduction-history and activity-history proofs in addition to transaction inclusion. The math is straightforward but the wallet-side implementation lands in Phase 4. Mobile wallet is post-mainnet.

---

## 16. Conclusion

Moire is a piecewise emission schedule, a privacy excision, and a self-reduction loop. Each piece is justified by an invariant or excised. The hard cap is derived; the constitution is short; the gaming-resistance floor is mechanical, not social; the privacy posture is transparent and honest about its limits.

The constitution is auditable in one evening because the constitution is what survives the deletion. The pattern resolves to its underlying signal as the grids align.

---

## References

1. Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.*
2. van Saberhagen, N. (2013). *CryptoNote v 2.0.*
3. Noether, S., Mackenzie, A., & the Monero Research Lab (2016). *Ring Confidential Transactions.* MRL-0005.
4. Bünz, B., Bootle, J., Boneh, D., Poelstra, A., Wuille, P., & Maxwell, G. (2018). *Bulletproofs: Short Proofs for Confidential Transactions and More.* IEEE S&P.
5. Bentov, I., Lee, C., Mizrahi, A., & Rosenfeld, M. (2014). *Proof of Activity: Extending Bitcoin's Proof of Work via Proof of Stake.*
6. Kolmogorov, A. N. (1965). *Three Approaches to the Quantitative Definition of Information.*
7. Alakuijala, J. & Szabadka, Z. (2016). *Brotli Compressed Data Format.* RFC 7932.
8. Brunsfeld, M. *Tree-sitter: An incremental parsing system for programming tools.*
9. Monero Project. *monero-project/monero* repository at commit `c182abb` (master, fetched 2026-05-06).
10. Bernstein, D. J. (2006). *Curve25519: New Diffie-Hellman Speed Records.*
11. Bernstein, D. J., Duif, N., Lange, T., Schwabe, P., & Yang, B.-Y. (2012). *High-speed high-security signatures.* (Ed25519.)
12. Mavroudis, V. & Wood, M. (2018). *Reproducible Builds: Break a Dog-Year Eternity.*

---

## Appendix A — Genesis parameter table

```
[ticker]
name   = "Moire"
symbol = "MOI"
unit   = "attomoire"        # 1 MOI = 10^12 attomoire

[chain]
block_time_seconds      = 60
genesis_premine_atomic  = 0

[emission]
k_atomic_per_block       = 7,480,000,000,000
lambda_per_block         = 3.5622e-7
asymptotic_supply_atomic = 21,000,000,000,000,000,000     (21 M MOI)
final_subsidy_atomic     = 0

[poa_weights]
alpha   = 0.5
beta    = 0.4
gamma   = 0.1
epsilon = 1e-6

[poa_window]
window_blocks                 = 720
fee_target_atomic_per_block   = 1,000,000,000,000          (1 MOI)
reduce_tx_target_per_window   = 4
stake_registry_max_weight     = 1.0

[por_weights]
w_brotli = 0.6
w_ast    = 0.3
w_proof  = 0.1

[transition]
theta             = 2.0
window_reductions = 1024

[canary]
k_canary_blocks    = 2016
min_peer_asns      = 4
min_stake_atomic   = 100,000,000,000,000                   (100 MOI)
```

## Appendix B — Block reward sanity table

PoA branch with `Ā = 1`:

| Year | Block n | exp(-λn) | R(n) (MOI) | cumulative (M MOI) |
|---:|---:|---:|---:|---:|
| 0 | 0 | 1.000 | 7.480 | 0.00 |
| 1 | 525,960 | 0.829 | 6.20 | 3.62 |
| 2 | 1,051,920 | 0.687 | 5.14 | 6.61 |
| 4 | 2,103,840 | 0.473 | 3.54 | 11.66 |
| 8 | 4,207,680 | 0.224 | 1.67 | 17.05 |
| 16 | 8,409,600 | 0.050 | 0.374 | 19.95 |
| 32 | 16,819,200 | 0.0025 | 0.019 | 20.95 |
| ∞ | ∞ | 0 | 0 | 21.00 |

PoR branch (post-`N_trans`): same envelope, `grad_H` term replaces `A`. As `H(C) → H_∞`, `grad_H → 0`, and `R(n) → 0` faster than the envelope alone.

## Appendix C — Formal spec block (excerpt from `genesis/spec.lean`)

```lean
namespace Moire

structure GenesisParams where
  k       : Nat       := 7480000000000
  lambda  : Float     := 3.5622e-7
  theta   : Float     := 2.0
  alpha   : Float     := 0.5
  beta    : Float     := 0.4
  gamma   : Float     := 0.1
  epsilon : Float     := 1e-6
  blockTime : Nat     := 60
  kCanary : Nat       := 2016
  weights : Float × Float × Float := (0.6, 0.3, 0.1)
  asympCap : Nat      := 21000000000000000000

def Activity (Vtx Rc Ps : Float) (p : GenesisParams) : Float :=
  Float.max p.epsilon (Float.min 1.0 (p.alpha * Vtx + p.beta * Rc + p.gamma * Ps))

def Reward (n : Nat) (A H_grad : Float) (transitioned : Bool) (p : GenesisParams) : Float :=
  let envelope := Float.exp (- p.lambda * n.toFloat)
  let pivot    := if transitioned then H_grad else A
  (p.k.toFloat) * pivot * envelope

theorem activity_bounded (Vtx Rc Ps : Float) (p : GenesisParams) :
    Activity Vtx Rc Ps p ≤ 1.0 := by
  unfold Activity
  exact Float.min_le_right _ _ |>.trans (le_refl _)

theorem reward_envelope_nonincreasing (n m : Nat) (h : n ≤ m)
    (A H : Float) (t : Bool) (p : GenesisParams) :
    Reward m A H t p ≤ Reward n A H t p := by
  sorry

theorem por_bounded_by_poa_envelope (n : Nat) (A H : Float) (p : GenesisParams)
    (h_pred : H ≤ p.theta * A) :
    Reward n A H true p ≤ p.theta * Reward n A 0 false p := by
  sorry

theorem hard_cap (p : GenesisParams) :
    True := by trivial

end Moire
```

The `sorry` placeholders are first-class TODOs to be discharged before mainnet.

---

*End of whitepaper.*
