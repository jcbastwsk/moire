# Moire — Privacy Excision Blast Radius

Reference: monero-project/monero @ `c182abb` (master, fetched 2026-05-06).

## Total volume
- `src/` total: **209,564 LOC** (.cpp/.cc/.c/.h/.hpp).
- Excision target: ~12 kLOC of pure deletion before any reductions, plus surgical strikes across the consuming code.

## Whole-directory deletions

| Path | LOC | Rationale |
|---|---|---|
| `src/ringct/` | 7,213 | RingCT, Bulletproofs, Bulletproofs+, multiexp. All amount-hiding + range-proof machinery. |
| `src/multisig/` | 3,729 | Threshold-signature plumbing; depends on ring sigs; no minimal-monetary use case. |
| `src/seraphis_crypto/` | 448 | Forward-prep for next-gen privacy. Unneeded. |
| `src/device_trezor/` (partial) | — | Strip Trezor's RingCT path; keep core HW-wallet hooks only if zero-cost. Likely full delete in Day-1 cycle. |

## Surgical strikes (file → what changes)

| File | Hunk |
|---|---|
| `src/cryptonote_basic/cryptonote_basic.h` | Delete `txout_to_tagged_key` struct (lines ~83–98). Strip `view_tag` field. Strip `rct::rctSig rct_signatures` from `transaction` (line ~214). Strip `key_offsets` (ring offset list) from `txin_to_key` (lines ~139–150). Update `txout_target_v` variant to drop `txout_to_tagged_key`. Update `transaction::set_null()`, copy ctors, and `END_SERIALIZE()` blocks that touch `rct_signatures`. |
| `src/cryptonote_basic/cryptonote_format_utils.cpp` | Strip every code path keyed on `rct::RCTType*`, view-tag derivation, decoy selection, mixin scanning. |
| `src/cryptonote_basic/account_generators.h` | Delete RingCT key-image and stealth-mask generators; keep only the basic stealth-address (one-time-public-key) generator. |
| `src/cryptonote_basic/CMakeLists.txt` | Drop links to `ringct`, `multisig`. |
| `src/cryptonote_core/blockchain.{h,cpp}` | Delete: `expand_transaction_2`, all `rct::verRct*` callsites, `check_tx_inputs`'s ring-membership branch, decoy/mixin policy, dynamic-ringsize logic. Replace `check_tx_inputs` with a transparent UTXO check (key_image not in spent-set, sum(in.amount) ≥ sum(out.amount) + fee). |
| `src/cryptonote_core/cryptonote_tx_utils.{h,cpp}` | Replace `construct_tx_*` family with a single transparent-UTXO `construct_tx`. Strip mixin selection. |
| `src/cryptonote_core/tx_verification_utils.{h,cpp}` | Strip RingCT verification helpers; transparent-only path. |
| `src/cryptonote_core/CMakeLists.txt` | Drop `ringct`, `multisig` deps; add `poa_oracle.cpp`, `por_oracle.cpp`. |
| `src/cryptonote_core/cryptonote_core.cpp` | Strip RingCT init and verification queues. Wire PoA/PoR oracles into block-acceptance pipeline. |
| `src/wallet/wallet2.{h,cpp}` | Strip ring-construction, decoy selection, RingCT signing, multisig, view-tag scanning. ~5–8 kLOC of pure deletion expected. |
| `src/serialization/json_object.{h,cpp}` | Drop `rctSig` (de)serializers. |
| `src/blockchain_db/blockchain_db.{h,cpp}` and `lmdb/db_lmdb.{h,cpp}` | Drop RingCT output-distribution columns; add reduction-ledger column + activity-ledger column. |
| `src/rpc/daemon_handler.cpp`, `message_data_structs.h`, `zmq_pub.cpp` | Strip RingCT fields from RPC payloads. |
| `src/simplewallet/simplewallet.cpp` | Strip ring-size CLI args, mixin policy, multisig commands. |
| `src/cryptonote_config.h` | Delete `HF_VERSION_BULLETPROOF*`, `HF_VERSION_VIEW_TAGS`, mixin constants. Replace `MONEY_SUPPLY`/`EMISSION_SPEED_FACTOR_PER_MINUTE`/`FINAL_SUBSIDY_PER_MINUTE` with Moire emission constants. Rename `CRYPTONOTE_NAME "bitmonero"` → `"moire"`. |
| `src/version.cpp.in` | Rebrand. |
| `tests/` | Delete every test that exercises ring sigs, RingCT, Bulletproofs, multisig, view tags. Floor = surviving tests. |

## Block-header expansion (patch 05)

Add to `block_header`:
```
crypto::hash cumulative_reduction_root;  // Merkle root over all accepted reduce(ΔC) txs in the chain
crypto::hash activity_ledger_hash;       // hash of A(B_n) ledger snapshot at this height
```
Both included in the block hash. Genesis values are `{0x00...}`.

## Reduce-tx kind (patch 06)

New variant member of `txin_v` and `tx_out`-equivalent: a `reduce_tx_body` that is **not** a value-transfer. Carries:
- `parent_codebase_hash` (32B)
- `child_codebase_hash` (32B)
- `entropy_delta` (int64, must be > 0; signed so reverter txs are typed)
- `patch_blob_hash` (32B; canonical patch retrieved via gossip)
- `signature` (issuer commits credit at risk)
- `canary_window_start_height` (uint64)

Validity = parent matches current `cumulative_reduction_root`, behavioral-equivalence floor passes (oracle re-runs surviving test corpus), entropy delta verified against weighted Brotli+AST+proof model. Reward credited only after `K_canary = 2016` blocks of canary nodes running the new binary without consensus failures.

## Already-known Monero baseline numbers

- `MONEY_SUPPLY = (uint64_t)(-1)` (Monero uses tail emission)
- `EMISSION_SPEED_FACTOR_PER_MINUTE = 20`
- `FINAL_SUBSIDY_PER_MINUTE = 0.6 XMR` (300000000000 atomic)
- `DIFFICULTY_TARGET_V2 = 120s` (block time)
- Reward formula: `base_reward = (MONEY_SUPPLY - already_generated_coins) >> 20`

Moire replaces the entire reward formula. `block_time` is reset to **60 s** per spec.

## Out-of-scope today (intentional)

- `external/randomx` — keep verbatim. PoW survives PoA phase only.
- `external/lmdb` — keep verbatim. New columns added, schema otherwise untouched.
- `external/easylogging++`, `external/miniupnp`, `external/unbound` — keep; reduction targets later.
