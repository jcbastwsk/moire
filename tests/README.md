# Moire — tests/

Sandbox-runnable Python reference for the C++ oracles in
`src/cryptonote_core/{poa,por,reduce_tx}_oracle.{h,cpp}`. These exist so
invariants can be exercised before the full Monero toolchain compiles on
Hermes M4. **They do not replace the C++ tests; they pin the math.**

Layout:

    tests/
      conftest.py             # path setup
      gen_golden_vectors.py   # emits genesis/golden_vectors.json
      oracles/                # ref impl: poa, por, emission, reduce, crypto
      invariants/             # 5 constitution-pinned properties
      oracle_unit/            # reference-impl unit + golden-vector regression

Run:

    cd ~/Projects/moire
    python3 -m pytest tests/ -q

Last result on Day-2: **74 passed in 0.62s**.

The 5 invariants (Phase-0 Session 3, roadmap §):

1. `test_block_reward.py`         — R(n) = k·pivot·exp(-λn), monotone, saturating.
2. `test_transition_predicate.py` — N_trans monotone in grad_H, anti-monotone in A.
3. `test_hard_cap.py`             — S(N) ≤ S(∞); discrete vs continuous cap doc.
4. `test_reduce_tx_roundtrip.py`  — txin_reduce serialize/deserialize fixpoint.
5. `test_cumulative_root.py`      — Merkle pairwise + extend_cumulative_root.

`genesis/golden_vectors.json` is the canonical input/output table the C++
unit tests on M4 must reproduce byte-for-byte.
