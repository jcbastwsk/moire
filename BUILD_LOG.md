# Moire — Build Log

Append-only ledger. Each entry: timestamp UTC + agent + outcome.

---

## 2026-05-06T00:39Z — Day-1 sandbox session — Architecture + 7-patch scaffold

**Agent:** Day-1 sandbox (operator: jcb).
**Baseline:** `monero-project/monero@c182abb` (master).
**Outcome:** All 7 patches generated, replay-verified clean, deliverables on disk.

### Source tree LOC

| Slice | LOC |
|---|---|
| `monero@c182abb` `src/`               | 209,564 |
| Moire `src/` after patches 01–07    | 192,733 |
| **Net source delete** | **−16,831** |
| Whole tree (excl. `external/`)        | 275,362 |

### Patch ledger

| File | Lines | sha256 (first 16 hex) |
|---|---:|---|
| `diff/01-rename.patch`               | 898 | `13f30784c068ef7b…` |
| `diff/02-privacy-excision.patch`     | 19,915 | `7f0b2ff0787cb8db…` |
| `diff/03-poa-oracle.patch`           | 126 | `3e9491e3e44d2e27…` |
| `diff/04-por-oracle.patch`           | 151 | `fbc18ce46c2fe6e7…` |
| `diff/05-block-header.patch`         | 31 | `269c809ccc4e9876…` |
| `diff/06-reduce-tx-type.patch`       | 123 | `f97dd82fa7d0b2c3…` |
| `diff/07-genesis-constitution.patch` | 195 | `588672aee28e754d…` |

Replay against fresh `monero@c182abb` clone: all 7 apply cleanly.

### Whole-directory deletions in patch 02

| Path | LOC deleted |
|---|---:|
| `src/ringct/`           | 7,213 |
| `src/multisig/`         | 3,729 |
| `src/seraphis_crypto/`  | 448 |
| `src/device_trezor/`    | ~5,400 |
| **Total directory delete** | **~16,790** |

Plus surgical strikes in `cryptonote_basic.h` (txout_to_tagged_key removed,
key_offsets stripped from txin_to_key, rct_signatures stripped from
transaction, txout_target_v variant pruned), `cryptonote_config.h`
(HF_VERSION_BULLETPROOF*, HF_VERSION_VIEW_TAGS, MONEY_SUPPLY,
EMISSION_SPEED_FACTOR_PER_MINUTE, FINAL_SUBSIDY_PER_MINUTE replaced),
plus CMakeLists pruning.

### New code in patches 03–07

| Path | New LOC |
|---|---:|
| `src/cryptonote_core/poa_oracle.{h,cpp}`      | 110 |
| `src/cryptonote_core/por_oracle.{h,cpp}`      | 130 |
| `src/cryptonote_core/reduce_tx.{h,cpp}`       |  72 |
| `genesis/params.toml`                         |  41 |
| `genesis/spec.lean`                           |  43 |
| `genesis/toolchain.merkle.json`               |  39 |
| Moire constants block in `cryptonote_config.h` |  17 |

### Gaming-resistance posture (constitution-pinned)

- Behavioral-equivalence floor: enforced (constitution Article VI).
- Canary-then-promote: `K_canary = 2016` blocks (~2 weeks @ 60 s).
- θ-tuning self-defeating: any θ change must reduce overall H.
- Stake γ-cap: 0.1; deprecated to 0 at `N_trans`.
- No live execve hand-off (manifesto §II self-modification safety).

### Genesis math

λ ≈ `3.5622 × 10⁻⁷` per block (95 % minted by year 16).
k = `7.48 × 10¹²` attomoire/block.
S(∞) = 21,000,000 MOI. Half-life ≈ 3.7 years.
Audit trail: `genesis/derivation.md`.

### What didn't ship today

- Patch-02b cross-file RingCT call-site sweep (Hermes M4).
- Compile pass (Hermes M4).
- Tree-sitter + brotli vendor drops (Sessions 11–12).
- `genesis/toolchain.merkle.json` placeholder hashes (Hermes M4).
- LMDB `reduction_ledger` + `activity_ledger` columns (Session 15).
- `tests/invariants/` first 5 properties (Session 3).

---

---

## 2026-05-06T00:55Z — Day-1 sandbox session — Scope addition: GUI client + chat

**Agent:** Day-1 sandbox.
**Operator directive:** "we also need a working gui node/miner/wallet/chat
system to also reduce over time" + "I want there to be an irc like chat
network going" + "within the client".

### Decision

Single binary `moire-client` bundling four panes (Node / Miner / Wallet /
Chat) on Dear ImGui + GLFW. Headless `moired` and `moire-wallet-cli`
continue to ship for ops/automation.

Chat is a fourth pane in the same client, **not a separate process and not
on chain**. IRC-flavored, decentralized, gossip-borne overlay over the
existing P2P layer (new opcode `0x7DA`). Identity derived from wallet
spend-key. Channels unowned. Opcodes mirror RFC 1459 minimal set. Messages
TTL-bounded; no persistent backlog.

Both surfaces are layer-7 — no consensus impact, no constitution change.
They evolve under the same `reduce(ΔC)` gradient as core source.

### Rationale for ImGui + GLFW (over Qt, Tauri, Electron)

- ~32 kLOC total UI runtime, both vendor cleanly with hashes pinned.
- Deterministic cross-platform rendering (no platform widget drift).
- No JavaScript runtime, no Webkit, no theme system.
- Trivial deletion path under the reduction gradient.

### Deliverables added

- `docs/gui_chat.md` — full GUI + MIRC chat protocol spec.
- DESIGN.md §16 — bundled-client overview.
- roadmap.md — Phase 1.5 (sessions C1–C5) added.
- HERMES_HANDOFF.md — Phase 1.5 brief added.

### Three-risk re-assessment (operator query)

All three previously-flagged risks remain manageable:
1. Patch-02b sweep is mechanical; bounded by 1–2 extra Phase-0 sessions.
2. block_header +64 bytes is safe under genesis-clean-start; LMDB blob
   storage has no fixed-size assumption.
3. `txin_reduce` was deliberately appended to the END of `txin_v` —
   discriminant indices 0..3 preserved; only `VARIANT_TAG` and explicit
   `which()==N` sites need audit (≤ 20 hits expected).

None forces a re-cut of patches 01–07.

### Cleanup note

A residual `monero-ref/.git/` skeleton exists in the project root from an
early aborted clone attempt. The sandbox's FUSE mount cannot delete it
(EPERM). Hermes can `rm -rf monero-ref/` on the M4 with normal
permissions.

---

---

## 2026-05-06T02:55Z — Day-1 sandbox session — Project rename: Distill → Moire

**Agent:** Day-1 sandbox.
**Operator directive:** "rename it to the Moire".

### Decision

Project is now **Moire**. Naming reasoning: a moiré pattern is the
interference figure that emerges when two grids overlap. The protocol and
its constitution overlay; reduction is the alignment that emerges. The
pattern resolves to its underlying signal as the grids align — same
reduction telos as before, sharper metaphor.

### Renamed

| Was | Now |
|---|---|
| Distill | Moire |
| DST (ticker) | MOI |
| attodist (atomic unit) | attomoire |
| `distilld` | `moired` |
| `distill-wallet-cli` | `moire-wallet-cli` |
| `distill-client` | `moire-client` |
| `namespace distill` | `namespace moire` |
| `DISTILL_*` macros | `MOIRE_*` macros |
| DSTC chat protocol | MIRC v0.1 |
| `chat_seed = sha256("distill-chat" \|\| ...)` | `sha256("moire-chat" \|\| ...)` |
| `CRYPTONOTE_NAME "distill"` | `CRYPTONOTE_NAME "moire"` |
| `MOIRE_TODO_HERMES` (from `DISTILL_TODO_HERMES`) | (already current) |

Project directory remains `~/.hermes/Projects/distill/` per the operator's
original lock. Hermes can `mv` later if desired.

### Patches re-cut

All 7 patches regenerated from a clean Monero baseline with the new
naming. Replay verified clean against fresh `monero@c182abb`.

| File | Lines | sha256 (first 16 hex) |
|---|---:|---|
| `diff/01-rename.patch`               |    901 | `a25ce11ff8849884…` |
| `diff/02-privacy-excision.patch`     | 19,915 | `114481ca43a46db4…` |
| `diff/03-poa-oracle.patch`           |    118 | `9ef8cf4cc80d4bdf…` |
| `diff/04-por-oracle.patch`           |    137 | `0a2d075ecec29a83…` |
| `diff/05-block-header.patch`         |     31 | `fc5ecf016b2f1849…` |
| `diff/06-reduce-tx-type.patch`       |    120 | `d44f82b552f6bdc8…` |
| `diff/07-genesis-constitution.patch` |    205 | `6642706b2c270646…` |

Net source delete unchanged at **−16,831 LOC** in `src/`.

### Invariants unchanged

The constitution math, the formal spec, the gaming-resistance posture, the
canary semantics, and the GUI/chat architecture are identical to the
pre-rename state. Only nominal identifiers moved.

### Doc files updated

DESIGN.md, constitution.md, HERMES_HANDOFF.md, roadmap.md, build.sh,
docs/gui_chat.md, notes/excision_map.md, genesis/{params.toml, spec.lean,
derivation.md, toolchain.merkle.json}. Final stale-reference scan: clean
(only the `~/.hermes/Projects/distill/` directory paths remain, and those
are intentionally preserved per the original location lock).

---

## 2026-05-06T21:49Z — Day-2 sandbox session — Oracle ref impl + invariant suite + golden vectors

**Agent:** Day-2 sandbox (operator: jcb).
**Canonical path:** `~/Projects/moire/` (operator promoted in mid-session;
see Day-2 path-promotion entry below). Day-2 work was authored against the
deprecated `~/.hermes/Projects/distill/` mirror, then auto-synced and
committed here.
**Project name:** Operator's task brief used "Distill"; on-disk artifacts
are "Moire" per the Day-1 rename. Honoring the rename. Vocabulary in this
entry follows the locked invariants (Distill ≡ Moire ≡ this codebase).
**Outcome:** Oracle Python references + invariant suite + golden-vector file
shipped. **74/74 tests pass.** Patches 01-07 unmodified (sha256 verified).

### Shipped

| Path | LOC | Purpose |
|---|---:|---|
| `tests/oracles/crypto.py`             |  53 | Keccak-256 + Merkle-pairwise, mirrors `crypto::cn_fast_hash`. |
| `tests/oracles/poa.py`                |  76 | Python ref of `src/cryptonote_core/poa_oracle.{h,cpp}`. |
| `tests/oracles/por.py`                |  77 | Python ref of `src/cryptonote_core/por_oracle.{h,cpp}`. |
| `tests/oracles/emission.py`           |  63 | R(n) = k·pivot·exp(-λn) + closed-form/discrete supply. |
| `tests/oracles/reduce.py`             | 175 | `txin_reduce` codec + canary state machine. |
| `tests/invariants/test_block_reward.py`         |  72 | Property-1: reward formula. |
| `tests/invariants/test_transition_predicate.py` |  82 | Property-2: monotonicity. |
| `tests/invariants/test_hard_cap.py`             | 105 | Property-3: cap bound (with discrete-overshoot doc). |
| `tests/invariants/test_reduce_tx_roundtrip.py`  | 144 | Property-4: txin_reduce roundtrip + sig-hash sensitivity. |
| `tests/invariants/test_cumulative_root.py`      | 113 | Property-5: Merkle root correctness + reorder sensitivity. |
| `tests/oracle_unit/test_poa.py`                 | 100 | PoA oracle units. |
| `tests/oracle_unit/test_por.py`                 |  72 | PoR oracle units. |
| `tests/oracle_unit/test_reduce.py`              |  62 | Canary state-machine units. |
| `tests/oracle_unit/test_golden_vectors.py`      |  98 | Re-derives every golden vector from refs. |
| `tests/gen_golden_vectors.py`                   | 187 | Vector generator (idempotent). |
| `tests/conftest.py`                             |  10 | Path setup. |
| `genesis/golden_vectors.json`                   | n/a | self-sha256 sealed; Hermes M4 unit-test target. |

### Test results

```
74 passed in 0.62s
```

### Patch ledger sanity

All 7 patch sha256 prefixes match Day-1 rename ledger above (lines 192-198).
Re-verified line counts: 901 / 19,915 / 118 / 137 / 31 / 120 / 205. Clean.

### Findings — surfaced by the test suite

1. **Discrete-vs-continuous cap discrepancy.** λ at genesis was solved against
   the integral form `S(∞) = k/λ`. Per-block emission is discrete, so the
   true asymptotic ceiling is `k/(1-exp(-λ))`. Relative overshoot ≈ λ/2
   ≈ 1.78×10⁻⁷ — about **3.74 MOI on the 21 M MOI cap**. Two clean fixes:
   (a) re-solve λ to satisfy the discrete cap exactly, OR
   (b) explicitly redefine `S(∞) := k/(1-exp(-λ))` in constitution.md
       Article II and re-run the year-16 sanity check.
   Pinned in `tests/invariants/test_hard_cap.py::test_discrete_asymptotic_cap_overshoot_documented`
   so any future λ change keeps overshoot < 1e-5 relative.
2. **txin_reduce signature scope.** `admissibility_input_hash` covers all 7
   non-signature fields (parent, child, patch, Δ, pubkey, stake, canary).
   Hermes M4 must wire `crypto::generate_signature` over this exact byte
   sequence. The Python reference encodes the canonical layout; golden
   vector `reduce_tx[0]` pins both the wire blob and the sig-input hash.
3. **Merkle rule.** `merkle_root_pairwise([])` returns 32 zero bytes;
   single-leaf returns the leaf as-is; odd layers duplicate the last
   leaf. C++ side must match exactly for `cumulative_reduction_root`
   verification to be portable. Pinned in golden vectors §merkle.

### Hermes M4 hand-off

The C++ unit tests on M4 should:
1. Read `genesis/golden_vectors.json` at compile time.
2. For each `block_reward[i]`: assert `core::get_block_reward(n, pivot)` matches.
3. For each `poa[i]`: assert `moire::activity_score()` and `activity_ledger_hash()` match (binary-identical).
4. For each `por[i]`: assert `codebase_entropy()`, `transition_predicate()`, and the chain extension match.
5. For each `reduce_tx[i]`: deserialize `wire_blob_hex`, re-serialize, assert byte equality. Compute `admissibility_input_hash` and assert match.
6. For each `canary[i]`: build `reduce_tx_state` per the fixture and assert `reduce_tx_promotable()` matches.
7. For each `merkle[i]`: build leaves `cn_fast_hash("leaf-{i}")` and assert root match.
8. Verify `self_sha256` of the file using sha256 of `json.dumps(payload-without-self_sha256, indent=2, sort_keys=True)`.

### What didn't ship today (still queued)

- C++ ports of the 5 invariants (Hermes M4: cmocka or gtest).
- `diff/02b-sweep.patch` cross-file RingCT call-site sweep.
- Compile pass.
- `tests/01-excise-privacy.patch` — the test-corpus excision (we wrote
  invariants TOP-DOWN instead; bottom-up Monero test deletion still pending).
- LMDB column wiring.

### Blockers

1. **~~Path-layout divergence~~** — RESOLVED in the Day-2 path-promotion
   entry below. `~/Projects/moire/` is canonical.
2. **Genesis λ recompute.** See finding (1) above. Two-line fix in
   `genesis/derivation.md` + new pinned λ in `genesis/params.toml`. Either
   pick (a) re-solve λ to satisfy the discrete cap, or (b) redefine
   `S(∞) := k/(1-exp(-λ))` in the constitution. Next session executes.

---

## 2026-05-07T02:08Z — Day-2 sandbox session — Path promotion: ~/Projects/moire/ canonical

**Agent:** Day-2 sandbox.
**Operator directive:** "Yes make the projects folder one the new canonical path."

### Decision

`~/Projects/moire/` is now the **canonical** project root. The previous
location `~/.hermes/Projects/distill/` is a deprecated mirror and should
not receive new writes. The autosync pipeline that mirrored sandbox edits
into `~/Projects/moire/` did the heavy lifting; this entry pins the
decision in the ledger.

### Reconciled

- Synced the two stragglers `tests/.gitignore` and `tests/README.md` from
  the deprecated mirror into the canonical tree.
- Stripped the `Path lock: ~/.hermes/Projects/distill/` line from the
  Day-2 BUILD_LOG header above; replaced with a canonical-path note.
- Updated `tests/README.md` cd-path to `~/Projects/moire`.
- Verified `pytest tests/ -q` from the canonical tree: **74 passed in 0.71s**.
- Verified all 7 patch sha256 prefixes still match the Day-1 ledger.
- Verified `genesis/golden_vectors.json` `self_sha256` re-derivation matches.

### Future-session note

The scheduled task file (`SKILL.md`) still contains the line
`PATH NOTE — canonical project root is ~/.hermes/Projects/distill/. Do
NOT write to ~/Projects/.` That language is now stale. Operator should
edit the scheduled task to read `canonical project root is ~/Projects/moire/`
before the next automated run, or future autoruns will land in the
deprecated mirror again. (The sandbox cannot edit the task file directly —
it lives in the user's macOS Application Support uploads folder.)

### Tombstone

`~/.hermes/Projects/distill/MOVED.md` was already the breadcrumb. It's
preserved. The orphaned `monero-ref/.git/` skeleton inside the deprecated
tree still cannot be removed from the sandbox (FUSE EPERM); operator can
`rm -rf ~/.hermes/Projects/distill/` from the host shell at any time.

---

## (Hermes appends from here)

---

## 2026-05-08T17:34Z — Hermes host session — Build bring-up started

**Agent:** Hermes on host.
**Objective:** Start Session 2 / patch-02b bring-up: run `build.sh`, make the patch stack reproducible, and reach the first real compile failures.

### Pre-existing Day-2 work landed

Found a staged Day-2 sandbox handoff in the index plus `notes/day2_pending_commit.md`. Verified with:

```bash
uvx --with hypothesis --with pycryptodome --from pytest pytest tests/ -q
```

Result: **74 passed**. Also verified `genesis/golden_vectors.json` `self_sha256`.

Committed and pushed:

```text
d070520 Day-2: oracle ref impl + 5 invariants + golden vectors; promote canonical
```

### Host dependencies installed

Installed missing build dependencies via Homebrew:

```text
cmake boost libsodium pkg-config zeromq miniupnpc expat libpgm hidapi protobuf ccache
```

### Build harness fixes

`build.sh` had three host bring-up blockers before reaching the intended C++ sweep:

1. `SRC` was read by the Python source-hash step before it was exported.
2. Re-running the script failed because `git reset --hard` left untracked files created by prior patch attempts; added `git clean -fd` inside `monero-src` before patch replay.
3. Fresh clone lacked submodules; added `git submodule update --init --force`.
4. Trezor/device support was still probed even though Moire excises Trezor privacy paths; configure now passes `-DUSE_DEVICE_TREZOR=OFF`.

### Patch stack fix

`diff/01-rename.patch` renamed `project(monero)` to `project(moire)`, which made CMake variable `monero_SOURCE_DIR` empty in `cmake/CheckLinkerFlag.cmake`. Added the corresponding rename to `moire_SOURCE_DIR`.

### Verified progress

After those fixes, `build.sh` now:

- clones/checks out `monero@c182abb`,
- initializes submodules,
- applies patches `01..07` cleanly,
- computes the toolchain leaf,
- computes `canon(C)` source hash,
- configures CMake successfully,
- starts compiling.

Current source hash after patch replay:

```text
19dfc8bfe8e9ce6718dcf627c92c101ac2df04846f325894040867b266d9e612
```

### Current true blocker

The build now fails in the expected patch-02b zone: remaining consumers of deleted RingCT/device code.

First compile layer:

```text
src/cryptonote_basic/cryptonote_basic.h: fatal error: 'ringct/rctTypes.h' file not found
src/device/device.hpp: fatal error: 'ringct/rctTypes.h' file not found
```

A focused local sweep identified the next clusters:

- `cryptonote_basic.h`: missing `txin_reduce` `VARIANT_TAG`s; stale `txout_to_tagged_key`, `rct_signatures`, and `key_offsets` references.
- `account.h` / `account.cpp`: device API still assumes full `hw::device` and `hw::get_device` from `device/device.hpp`.
- `device/*`: public device API still exposes RingCT/MLSAG/CLSAG methods.
- `blockchain_db/*`: output DB still stores `rct::key commitment` and `add_output(..., const rct::key*)`.
- `rpc/*`: RPC structs still expose RingCT `mask` fields and include `ringct/rctSigs.h`.
- `cryptonote_tx_utils.*`: transaction construction still includes `ringct/rctOps.h`, `rct::ctkey`, `RCTConfig`, ring offsets, view tags.
- `wallet2.*`: large remaining RingCT/multisig/ringdb surface.

### Status

Patch replay/configure is now reproducible. Full `moired` / `moire-wallet-cli` compile is **not yet green**; the next commit must be the actual `diff/02b-sweep.patch` transparent-UTXO consumer sweep.
