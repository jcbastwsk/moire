# moire

Clean fork of Monero implementing a hybrid PoA → PoR emission with
codebase-entropy-reduction as the path to hard-cap digital-gold scarcity.

Privacy reduced to its semantic minimum (transparent UTXO + optional
stealth-address unlinkability only).

- Constitution: `constitution.md` — ratified primitives, articles I–VIII.
- Architecture: `DESIGN.md`, `WHITEPAPER.md`.
- Roadmap: `roadmap.md` (30 sessions, Phase 0 → mainnet).
- Build: `build.sh` (Hermes M4; sandbox cannot compile Monero).
- Tests: `tests/` (Python ref + invariants suite, 74/74 green).
- Patches: `diff/01..07-*.patch` against `monero-project/monero@c182abb`.
- Pickup brief for next agent: `HERMES_HANDOFF.md`.
- Append-only ledger: `BUILD_LOG.md`.

Emission constants pinned at `genesis/params.toml`. Golden test vectors at
`genesis/golden_vectors.json`. Don't edit pinned numbers without a
`reduce(ΔC)` tx and a fresh ledger entry.
