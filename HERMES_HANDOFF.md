# Moire — Hermes Handoff (Day 1 → Day 2)

**To:** Hermes (M4, full toolchain)
**From:** Day-1 sandbox session
**Project root:** `~/Projects/moire/`
**Baseline:** `monero-project/monero@c182abb` (master, 2026-05-06)

---

## Mission

Pick up the Day-1 design + 7-patch scaffold and **prove the fork builds**. You
have the machine; this sandbox does not.

---

## Pickup prompt for Hermes

> You are Hermes on the M4. The Day-1 sandbox session at
> `~/Projects/moire/` has produced:
> - `DESIGN.md` — full architecture and invariants.
> - `constitution.md` — the on-chain monetary constitution.
> - `diff/01..07.patch` — applicable unified diffs against `monero@c182abb`.
> - `genesis/{params.toml,spec.lean,toolchain.merkle.json,derivation.md}`.
> - `build.sh` — reproducible build recipe with toolchain pin.
> - `roadmap.md` — 30-session plan.
> - `notes/excision_map.md` — privacy excision blast radius.
>
> Your job for the next 4-hour session:
>
> 1. **Verify the patch stack applies cleanly** by running `./build.sh` (it
>    clones monero, applies the 7 patches in order, then attempts to compile).
>    Expected outcome: patches 01–07 apply with `git apply --check` zero-exit;
>    compile WILL fail with unresolved references (see §3 below). Capture the
>    full failure list — this is the patch-02b sweep that finishes the privacy
>    excision.
>
> 2. **Populate `genesis/toolchain.merkle.json`** by replacing every
>    `PLACEHOLDER_*` field with the actual sha256 of the corresponding
>    component on your M4. Append a new section `host` with `os`, `arch`,
>    `xcode_clt_version` for full reproducibility audit. Recompute the
>    toolchain leaf and write it to `genesis/toolchain.leaf.sha256`.
>
> 3. **Run patch-02b sweep**: for every reference flagged by the compile, do
>    one of: (a) delete the call site if it was RingCT/Bulletproof/multisig/
>    view-tag-only; (b) replace with transparent-UTXO equivalent; (c) leave
>    `// MOIRE_TODO_HERMES:` comment and continue. Output: `diff/02b-sweep.patch`.
>    Stop when `cmake --build` succeeds for at least `moired` and
>    `moire-wallet-cli` targets.
>
> 4. **Run the surviving test suite**. Expected: many tests fail because they
>    exercised excised features. The behavioral-equivalence floor (constitution
>    Article VI) requires the Day-1 test corpus minus those tests to pass. Drop
>    the obviously dead tests in a single commit `tests/01-excise-privacy.patch`.
>    The genesis test corpus = `tests/` after that drop. Compute its sha256
>    and pin it in `genesis/test_corpus.sha256`.
>
> 5. **Stand up a single-node testnet** with the new emission curve. Mine 100
>    blocks at `--regtest` style settings; assert `R(n)` matches the formula
>    in `constitution.md` Article II within rounding error. Log to
>    `BUILD_LOG.md`.
>
> Report back to operator (jcb) when done. Constraints: ruthless minimalism,
> no new heavy deps, no scope creep beyond patch-02b finishing the privacy
> excision and bringing up the testnet daemon.

---

## File index

| Path | Role |
|---|---|
| `DESIGN.md` | Read first. The whole architecture. |
| `constitution.md` | Read second. The monetary constitution. |
| `diff/01-rename.patch` | 901 lines. Rebrand monero→moire + block_time → 60s + CRYPTONOTE_NAME = "moire". |
| `diff/02-privacy-excision.patch` | 19,915 lines. −19,458 / +9. ringct/, multisig/, seraphis_crypto/, device_trezor/ + struct surgery. |
| `diff/03-poa-oracle.patch` | 118 lines. New `src/cryptonote_core/poa_oracle.{h,cpp}`. `namespace moire`. |
| `diff/04-por-oracle.patch` | 137 lines. New `src/cryptonote_core/por_oracle.{h,cpp}`. `namespace moire`. |
| `diff/05-block-header.patch` | 31 lines. Two new fields in `block_header`. |
| `diff/06-reduce-tx-type.patch` | 120 lines. `txin_reduce` + `reduce_tx.{h,cpp}` canary state machine. |
| `diff/07-genesis-constitution.patch` | 205 lines. `genesis/*` + `cryptonote_config.h` `MOIRE_*` constants block. |
| `genesis/params.toml` | Genesis parameter table. |
| `genesis/spec.lean` | Formal spec with theorem statements; `sorry` placeholders to discharge. |
| `genesis/toolchain.merkle.json` | Toolchain pin manifest. PLACEHOLDERS → real hashes on M4. |
| `genesis/derivation.md` | λ and k derivation, audit trail. |
| `build.sh` | Reproducible build recipe. Pinned toolchain Merkle leaf. |
| `notes/excision_map.md` | Where the privacy excision lands. Surgical map. |
| `docs/gui_chat.md` | Bundled client (node+miner+wallet+chat) + MIRC chat protocol spec. |
| `roadmap.md` | 30-session plan + Phase 1.5 (sessions C1–C5) for the client. |
| `BUILD_LOG.md` | Append-only ledger; you append on the M4. |

## Phase 1.5 scope (added after Day-1)

The operator scoped in a bundled GUI client (node + miner + wallet + chat
in one binary) and an IRC-like decentralized chat layer that lives inside
that client. Spec is `docs/gui_chat.md`. Roadmap sessions C1–C5 own the
work, and they can run in parallel with Phase 1 (testnet validation). The
client is layer-7: it does not enter consensus, it does not appear in the
constitution, and the reduction oracle treats its source identically to
core code.

---

## What Day-1 deliberately did NOT do

- **No compile.** The sandbox cannot run a 2-hour C++ build.
- **No patch-02b cross-file sweep.** RingCT references in
  `blockchain.cpp`, `wallet2.cpp`, `cryptonote_format_utils.cpp`, etc. are
  flagged with `// MOIRE_EXCISE:` comments at the top of `cryptonote_basic.h`.
  The compiler will surface them on first build.
- **No `genesis_block_blob` constant.** Computed once toolchain pin is real.
- **No `tests/invariants/` directory yet.** Hermes seeds it from the
  property checks that survive after the test-corpus excision.
- **No tree-sitter / brotli vendor drop.** Submodules added in patch-02b.

---

## Top 3 risks Hermes should flag if hit

1. **Patch-02b larger than expected.** If the cross-file RingCT references
   exceed ~30 kLOC of edits, escalate. Probably means we missed a struct
   that needs further surgery in patch 02 (and 02 needs a re-cut, not just an
   addendum).
2. **`block_header` size change breaks LMDB serialization.** The two new
   `crypto::hash` fields add 64 bytes to every block header. Verify
   `db_lmdb.cpp` block-record serializer accepts the new layout, or add
   migration code.
3. **`txin_v` variant addition breaks Boost serialization.** Adding
   `txin_reduce` to the variant changes the discriminant indices. If
   anywhere the variant index is hard-coded (e.g., wire-format constants),
   patch 06 will brick. Grep for `txin_v.*which()` to find these sites.

---

## Communication

- All work product → `~/Projects/moire/`.
- Append findings to `BUILD_LOG.md`. Day-1 ledger entry seeded.
- New patches → `diff/` with sequential numbering (`02b-sweep.patch`,
  `08-testnet-genesis.patch`, …).
- Operator (jcb) reads the BUILD_LOG, not the chat log.

The reduction gradient continues.
