# Moire — 30-Session Roadmap

Each session = ~4 hours, single operator + one agent (Day-1 sandbox or Hermes).
Goal-shaped, not calendar-shaped. Sessions can be banked or skipped; the
constitution does not move.

## Phase 0 — Bring-up (Sessions 1–5)

| # | Session | Owner | Deliverable |
|---|---|---|---|
| 1 | Day-1 design + 7-patch scaffold | Sandbox | DESIGN, constitution, diff/01..07, genesis/, build.sh, HERMES_HANDOFF, roadmap, BUILD_LOG. **DONE.** |
| 2 | Patch-02b cross-file RingCT sweep | Hermes (M4) | `diff/02b-sweep.patch`. `cmake --build` succeeds for `moired`, `moire-wallet-cli`. |
| 3 | Test-corpus excision + invariants seed | Hermes (M4) | `tests/01-excise-privacy.patch`, `tests/invariants/` with first 5 properties (block_reward formula, transition_predicate monotonicity, hard_cap bound, `txin_reduce` round-trip, `cumulative_reduction_root` Merkle correctness). `genesis/test_corpus.sha256` pinned. |
| 4 | Single-node testnet bring-up | Hermes (M4) | `moired --regtest` mines 100 blocks; `R(n)` matches Article II within 1 attomoire; emit `BUILD_LOG` entry with first-100-block trace. |
| 5 | Multi-node testnet (3 peers) | Hermes (M4) | 3 daemons sync; first peer-broadcast `txin_reduce` tx; canary state machine ticks. |

## Phase 1 — Validate the dynamics (Sessions 6–10)

| # | Session | Deliverable |
|---|---|---|
| 6 | Studio-sim ↔ testnet wiring | In-game "release" emits real `reduce(ΔC)` tx on testnet; in-game capacity = real cluster capacity. (Manifesto §VI.) |
| 7 | First real PoR cycle | Issue a tiny reduction patch (e.g. drop a dead `#include`), full canary cycle, promotion. Append to `BUILD_LOG`. |
| 8 | Transition predicate validation | Inject synthetic high-reduction-rate window; assert `N_trans` fires at the right block; assert α=γ=0 post-trigger. |
| 9 | Reproducibility audit | Build twice on the M4 (cold caches), assert `source_sha256` identical, `build.manifest.json` deltas only on `ts_utc`. |
| 10 | Determinism diff drill | Cross-build canary node on Linux arm64; assert binary hashes match the M4. If not, surface the non-determinism source and add to `notes/repro_issues.md`. |

## Phase 1.5 — Bundled client + chat (Sessions C1–C5)

Runs in parallel with Phase 1. Owner: Hermes or a dedicated UI session.

| # | Session | Deliverable |
|---|---|---|
| C1 | `patch 08`: client scaffold | `src/client/{main.cpp, app.cpp, pane_*.cpp}` + ImGui/GLFW submodules pinned in `genesis/toolchain.merkle.json`. Window opens, four empty tabs render. CMake target `moire-client` builds. |
| C2 | `patch 09`: daemon bridge | SPSC queues between ImGui thread and `cryptonote_core`. Node pane shows live height/peers/mempool. Miner pane spawns N RandomX threads, reports hashrate. |
| C3 | `patch 10`: wallet pane | Send/receive (stealth addr), tx history, reduce-tx submit form. Wallet keystore via libsodium `crypto_secretstream`. |
| C4 | `patch 11`: chat protocol MIRC v0.1 | New P2P opcode `0x7DA`. Frame format from `docs/gui_chat.md` §4.1. Chat identity derived from spend-key. Reserved channels relayed by canary nodes. |
| C5 | `patch 12`: chat pane + slash commands | ImGui chat pane (channel list, scrollback, NAMES, message composer). Parser for `/join /part /msg /me /topic /names /list /quit /nick /raw`. DM via `crypto_box`. |

After C5 the operator can run a single `moire-client` binary that mines,
holds funds, sends reductions, and chats with other operators in
`#por-cycles`. All five patches are subject to the reduction gradient like
the rest of the tree.

## Phase 2 — Harden the oracles (Sessions 11–15)

| # | Session | Deliverable |
|---|---|---|
| 11 | Brotli integration | Vendor brotli@1.1.0 as submodule; pin sha256; wire into PoR oracle's `H()` computation. |
| 12 | tree-sitter C++ integration | Vendor tree-sitter + cpp grammar; wire AST node count into `H()`. |
| 13 | Behavioral-equivalence floor | Implement Article VI: AST-coverage intersection check for test deletions in `reduce(ΔC)` txs. |
| 14 | Stake registry | Wire `P_stake` term into PoA oracle. Off-chain registry signed at genesis; first 32 stake-attestors enumerated. |
| 15 | Activity-ledger LMDB column | Add `activity_ledger` column; rolling 720-block aggregator implemented. |

## Phase 3 — Adversarial Pressure (Sessions 16–20)

| # | Session | Deliverable |
|---|---|---|
| 16 | "Delete consensus logic" attack | Submit a `reduce(ΔC)` tx that deletes critical code; assert the equivalence floor rejects it. |
| 17 | Inflation-via-θ-tuning attack | Submit a `reduce(ΔC)` that lowers θ; assert overall H is not reduced and the patch is rejected. |
| 18 | Stake capture sim | Simulate adversarial stake concentration; assert `γ ≤ 0.1` cap holds; verify `α=γ=0` post-transition removes the lever. |
| 19 | Canary-period bypass attempt | Try to promote a `reduce(ΔC)` before `K_canary`; assert the chain rejects. |
| 20 | Chaos drill: bitrot snapshot | Corrupt one LMDB segment; assert per-segment checksum catches it; assert recovery via mirror. |

## Phase 4 — Reduction Cycles (Sessions 21–28)

Goal: drive `H(C)` down by ≥ 30 % from post-excision baseline. Each session
cuts a real reduction patch through the canary pipeline.

| # | Session | Deliverable (rough order; ordered by easiest gain) |
|---|---|---|
| 21 | Drop `external/easylogging++` | Use libc++ `<format>` + a 120-LOC sink. |
| 22 | Drop `external/miniupnp` | NAT traversal optional; default off. |
| 23 | Strip `wallet2.cpp` to UTXO-only | Expected: ~6 kLOC deletion. |
| 24 | Strip `cryptonote_format_utils.cpp` RingCT branches | Expected: ~3 kLOC deletion. |
| 25 | Collapse `core_rpc_server` to JSON-RPC only | Drop ZMQ pub/sub for now. |
| 26 | Drop `serialization/json_object.{h,cpp}` rctSig serializers | Expected: ~1 kLOC. |
| 27 | Replace boost::variant with std::variant | C++20 native; saves a Boost dep. |
| 28 | Reduce reduction-oracle weight tuple | Make `(0.6, 0.3, 0.1)` configurable per genesis block; audit no-regression. |

## Phase 5 — Mainnet Posture (Sessions 29–30)

| # | Session | Deliverable |
|---|---|---|
| 29 | Constitution audit pass | Operator reads `constitution.md` end-to-end in one sitting. Confirms "tax form, not philosophy paper." Any edits go through `reduce(ΔC)`. |
| 30 | Mainnet genesis ceremony | Compute final `genesis_block_blob`. Pin SHA-256 of all artifacts. Public release of the build manifest. Mainnet daemons launch from this point. |

---

## Banked items (not in 30 sessions, queued for Phase 6+)

- HW-wallet hooks beyond Trezor's RingCT-coupled path.
- Light-client Merkle proof verifier in WASM.
- zk-SNARK pluggable layer over stealth-address pay-to-script-hash.
- Mobile wallet (the canonical wallet is CLI; mobile is a future app).

## Cadence note

Phase 0–1 is sequential (each session unblocks the next). Phase 2–4 can run
in parallel across multiple agents if compute permits. Phase 5 is gated by
the operator alone.
