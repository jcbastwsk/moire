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

---

## 2026-05-06T03:00Z — Day-1 sandbox session — Project relocation: ~/.hermes/Projects/distill/ → ~/Projects/moire/

**Agent:** Day-1 sandbox.
**Operator directive:** "I do want all hermes projects in the main home folder Projects folder and synced".

### What moved

Entire project tree (excluding the `monero-ref/.git/` orphan that the FUSE
mount couldn't delete) copied from `~/.hermes/Projects/distill/` to
`~/Projects/moire/`. New canonical project root: **`~/Projects/moire/`**.

The old `~/.hermes/Projects/<name>/` convention is deprecated for all
Hermes projects going forward — see `docs/project_layout.md`.

### Git repo initialized

`git init -b main` at the new root. Initial commit `d7d603d`:

> Day-1 Moire scaffold

`.gitignore` covers build artifacts, OS cruft, and the cloned baseline
source (`monero-src/`). The toolchain manifest IS committed; the real
hashes that Hermes populates ride on subsequent commits.

### Sync mechanism

`scripts/sync.sh` provides:

| Command | Action |
|---|---|
| `./scripts/sync.sh init <url>` | one-time: set the remote URL |
| `./scripts/sync.sh` | pull then push (default) |
| `./scripts/sync.sh push` | push only |
| `./scripts/sync.sh pull` | pull only |
| `./scripts/sync.sh status` | ahead/behind + dirty |

Provider-agnostic: the operator picks GitHub / Gitea / Codeberg /
self-hosted on a per-project basis. No remote is set yet — the operator
runs `init <url>` once when they decide.

Multi-machine sync (M4 ↔ canary nodes ↔ build farm) is via clone-and-pull;
git is the protocol.

### Convention doc

`docs/project_layout.md` written to fix the new convention:

- All projects in `~/Projects/<name>/`, lowercase, hyphenated.
- Standard skeleton: README, DESIGN, BUILD_LOG, HERMES_HANDOFF, roadmap,
  scripts/sync.sh, docs/, notes/, plus project-specific dirs.
- One git repo per project, one remote, branch `main`.
- `BUILD_LOG.md` is append-only; merge conflicts mean two agents wrote at
  once and resolution is concatenation.

### Old location

`~/.hermes/Projects/distill/` still exists. Operator can delete it once
they verify the new location has everything. The orphan `monero-ref/.git/`
inside it could not be removed from the sandbox due to FUSE EPERM; on the
host it's a one-line `rm -rf`.

A breadcrumb at `~/.hermes/Projects/distill/MOVED.md` will be added in
the next bash pass to redirect anything still looking there.

### Other Hermes projects on this machine

Confirmed under `~/Projects/`: `all-hands`, `crypto-games`, `dewey`,
`hermes-dashboard`, `hyperframes-cinematic-demo`, `pit`, `research`,
`youtube`, plus a `domains` and `fortnite` and `gta-rp`. The `~/Projects/distill/`
shell at the host's `~/Projects/` is now redundant; operator can delete.

---

## (Hermes appends from here)
