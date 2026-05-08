# Moire — Plain-English Explainer

**Companion to `WHITEPAPER.md`. No equations. Read in one sitting.**

---

## The one-sentence version

Moire is a Bitcoin-style cryptocurrency that pays people to make its own
software smaller, and stops paying them when there is nothing left to
shrink.

That is the entire idea. The rest of this document explains why anyone
would build that, and why it might work.

---

## 1. Why another cryptocurrency

The two cryptocurrencies that actually have a monetary story today are
Bitcoin and Monero. Both have a problem the other doesn't fix.

**Bitcoin** has a hard cap of 21 million coins. The number was picked.
Satoshi wrote it down and walked away. Every few years someone proposes
changing it ("tail emission" to keep paying miners forever), and every
few years that argument has to be relitigated. The cap is a tradition,
not a derivation.

**Monero** kept emission honest by acknowledging miners need to be paid
forever, but it accumulated privacy machinery — ring signatures, range
proofs, Bulletproofs, multisig, half a dozen other layers — faster than
anyone could read. The protocol now runs to thousands of pages of
cryptography. No single person audits it. Every year there is more.

Moire is the third option: derive the cap from the rules of the system
instead of picking it, delete the privacy machinery that isn't strictly
needed for money to work, and make the protocol's own ongoing
simplification the thing that earns rewards.

---

## 2. The reward loop

In Bitcoin, miners earn coins for guessing numbers (proof-of-work).
In Moire, that's still true at first — but layered on top is a second
way to earn: submit a patch to the Moire source code that genuinely
makes the codebase smaller and simpler, and the protocol pays you.

Not "smaller" by counting lines. The protocol measures the codebase
three ways at once:

- How well it compresses (a standard compression algorithm runs over
  the whole tree).
- How many pieces of structure it contains (the code is parsed and
  syntactic nodes are counted).
- How much formal proof is attached (machine-checked theorems about
  what the code does).

Take a weighted average of those three numbers and you get a single
score. Lower is better. A patch is paid in proportion to how much it
lowers the score per byte of patch — the marginal rate matters, not
the gross size.

The reason for three measures is straightforward: any one measure can
be gamed. If you only counted compressed size, someone would submit
a patch full of repeating characters that the compressor crushes to
nothing. If you only counted syntactic nodes, someone would ship gibberish
that parses to two tokens. Three weakly-correlated measures, all moving
in the same direction, are much harder to fool than one.

---

## 3. The hard cap, derived

Bitcoin's 21 million is hand-set. Moire's 21 million falls out of two
rules:

- Every block's reward is multiplied by an exponentially decaying
  envelope. The envelope is tuned so that 95% of all coins are minted
  by year 16.
- The activity score on the front end of the formula is clamped at 1
  by definition.

Multiply those two rules together, integrate over all time, and you
get a finite number. Pick the constants so that the finite number
equals 21 million. Done. The cap is not stored as a constant
anywhere in the code; it's a corollary of the rules.

This matters because if the cap is a corollary, it can't be raised
without breaking other things. There is no "21 million" line of code
to delete. To inflate the supply you would have to change `k` or
`λ` (the rate constant), and any change to those rides on the same
patch mechanism that pays for shrinking the codebase — which means an
inflation patch has to itself pass the shrinkage test. We'll come back
to this.

---

## 4. The two phases

Moire has two life stages.

**Phase one (Proof of Activity).** Early on, when the codebase is still
big and reduction patches are rare, miners earn block rewards based
on network usage: transaction fees being burned, reduction patches
being submitted, and a small stake-attestation signal. This phase
behaves like any other proof-of-work coin from a user perspective.

**Phase two (Proof of Reduction).** Once reduction patches are
arriving fast enough — specifically, when the average shrinkage rate
exceeds twice the average activity rate over the last 1024 patches —
the protocol flips a switch. The activity term drops out. The block
reward is now based purely on how much the codebase is shrinking.

The switch is one-way. Once flipped, it stays flipped. This is
deliberate: a reversible switch could be exploited by an attacker who
briefly inflates activity to push the chain back into Phase 1 and
resume Phase 1 inflation.

The switch is automatic. There is no vote, no foundation, no developer
committee. The math fires and the protocol updates.

**Phase end.** As the codebase approaches its irreducible floor, the
shrinkage term goes to zero, and so does the block reward. The
protocol stops paying anyone, because the protocol is done. From that
point, miners are paid by transaction fees alone.

---

## 5. Privacy, honestly

Moire is **not private like Monero**. Moire's chain is **transparent
like Bitcoin's**, with one improvement: stealth addresses.

What that means concretely:

- **Anyone can see every transaction.** Inputs, outputs, amounts, and
  addresses are fully public. Anyone running a node sees the same
  thing.
- **Recipient privacy is improved.** When you receive money, the
  sender computes a fresh one-time public key derived from your real
  address. Without your view key, an outside observer cannot link two
  payments to you as belonging to the same wallet.
- **Sender privacy is not protected at the protocol layer.** If you
  want sender anonymity, route your transactions through a mixer or
  Tor — that's a wallet-level concern, not a chain-level one.

This is a deliberate downgrade from Monero. The case for it is
maintainability: Monero's privacy stack is the part of Monero that
grew without bound. Cutting it removes about 17,000 lines of
consensus-relevant code, makes the rest legible, and makes the
"reduce the protocol" reward loop actually possible. You can't have
people audit and shrink a codebase nobody can read.

Moire is honest about what it is: Bitcoin-grade transparency with
strictly better receiver privacy. If a user requires strong sender
anonymity or amount hiding, that belongs in software they run
themselves, off-chain.

---

## 6. The hardest question — what stops a malicious patch

The obvious attack: someone submits a "patch" that deletes the part
of the code that checks signatures, claims a huge shrinkage, collects
the reward, and now the network can be cheated by anyone.

This must be impossible, and four mechanisms work together to make it
so.

**Mechanism 1 — Tests must keep passing.** The codebase ships with a
test corpus that exercises the consensus rules. Any patch that breaks
those tests is rejected before it gets paid for.

**Mechanism 2 — Test deletions must be paired with feature deletions.**
The obvious counter-attack is to delete the test for the consensus rule
in the same patch. The protocol checks: every test that's removed must
have its coverage entirely contained in the code that's also removed.
You can delete the test for feature X only if you're also deleting
feature X.

**Mechanism 3 — A two-week canary period.** Even after a patch passes
the mechanical checks, it doesn't take effect immediately. Instead, a
group of opt-in "canary nodes" — currently required to be at least 4
on different network providers — compile the patched binary and run
it alongside the real binary for two weeks. They watch for any
divergence. If anything goes wrong, the patch is reverted, and the
patch author's stake (minimum 100 MOI, posted with the patch) is
burned. Only after two clean weeks does the patch get promoted into
the actual running binary.

**Mechanism 4 — Reproducible builds.** The compiler, libraries, and
build flags are all pinned at genesis. A patch is only valid if the
binary that comes out of the canary build matches what every other
canary node produces from the same source. A node can't be convinced
to run a different binary by lying about the source.

The result: a malicious patch must (a) pass the test suite without
deleting tests illegitimately, (b) survive two weeks of live
side-by-side observation across at least four independent network
operators, and (c) compile to exactly the right binary hash. Failing
any one of these costs the attacker their stake.

This is the part of the design that took the longest to settle. The
mechanism that pays for changes has to be dumber than the thing it's
changing — a textual diff plus a signed envelope, no scripting, no
templates, no Turing-complete migration. The simplicity is what makes
it safe.

---

## 7. The "constitution can't be rewritten" property

People reasonably ask: what about the parameters? What if someone
submits a patch that changes the decay rate, or raises the per-block
reward, or lowers the threshold for the phase switch?

That's allowed. It's just another `reduce` transaction. But it has
to satisfy the same shrinkage rule as every other patch — the patch
must reduce the overall codebase score, **measured under the new
parameters**.

This is self-defeating for an attacker. To inflate the supply, you'd
have to do a chunk of legitimate codebase-cleanup work in the same
patch — exactly the work the protocol pays for. At which point you've
done the protocol a favor, and the marginal inflation you sneak in is
the protocol's fee for the favor.

There is no other amendment path. No foundation. No developer fund.
No on-chain governance vote. No off-chain ballot binding consensus.
The transition predicate is the only "vote," and it counts patches,
not people.

---

## 8. The bundled application

Moire ships as a single binary that combines four things:

- **Node** — the part that talks to other Moire nodes, validates
  blocks, holds the chain.
- **Miner** — the part that does the proof-of-work computation.
- **Wallet** — keeps your keys, sends and receives transactions.
- **Chat** — a peer-to-peer chat protocol modeled on IRC, keyed off
  your wallet identity, used to coordinate canary operators and
  patch authors.

The chat is layer-7: not consensus, not anonymous, no fees. It's a
coordination tool, not a product. It exists because patch authors and
canary operators need a way to talk to each other that doesn't depend
on Discord, Slack, or any third party.

Headless command-line versions still ship for servers and automation.
The combined GUI client is for individual operators.

---

## 9. What Moire is not

- **Not a privacy coin.** It is more transparent than Monero by
  design.
- **Not a smart contract platform.** No Turing-complete on-chain
  programs. The only on-chain "program" is the patch, and patches are
  textual diffs with metadata.
- **Not a stake-based system.** The proof-of-work is RandomX,
  inherited from Monero. Stake is a small input to the activity
  score during Phase 1 and goes to zero in Phase 2.
- **Not governed by a foundation.** No company, no committee, no
  treasury. The transition predicate is the only governance.
- **Not a perpetual-subsidy chain.** When the codebase reaches its
  floor, miner subsidy goes to zero. Security is then funded by fees
  alone. If fees aren't enough, the chain stalls, which is the right
  outcome for a system whose thesis is finite scarcity.

---

## 10. Where it is today

This is a Day-1 project. Architecturally complete: the constitution
is written, the issuance formula is derived, the threat model is
analyzed, the source-tree edits to turn Monero into Moire are
generated as a sequence of seven patches, and a thirty-session
roadmap to mainnet exists.

What hasn't happened yet: a single binary has not been compiled.
The next several sessions are about getting `moired` to build, run a
single-node testnet, then a multi-node testnet, then wire the
reduction oracle's actual encoders (a compression library and a code
parser are vendored as next steps).

Mainnet is many sessions away. The roadmap is goal-shaped, not
calendar-shaped — sessions can be banked or skipped. The constitution
does not move.

---

## 11. The honest list of things we don't know

A short list of open questions, named so they don't surprise anyone
later:

- **Compiler trust.** v0.1 pins one compiler. A compromised compiler
  is undetectable from inside the system. The fix is dual-compiler
  builds with cross-validated outputs, queued for a later phase.
- **Reward calibration.** The per-patch reward formula is normalized
  against the largest patch in the recent window. This might starve
  smaller patches once a single huge cleanup lands. Real testnet data
  will say.
- **Test corpus drift.** The test suite is constitution-protected,
  but it can grow over time. If it grows faster than the codebase
  shrinks, the gaming-resistance floor stops being useful. We have
  one mitigation built in (test deletions paired with feature
  deletions) and will need empirical data on whether more is needed.
- **What happens after the floor.** When the codebase reaches its
  irreducible Kolmogorov floor, fees alone fund miners. Whether fees
  are enough depends on usage. There is no graceful-degradation
  story; if the chain can't pay for its own security, the chain
  stalls. That is the design choice. Scarcity is more important than
  perpetual subsidy.

---

## 12. The shape of the bet

Moire is a bet on three things:

1. **Derived caps beat picked caps.** A 21M coin number that falls
   out of the formula is more durable than a 21M coin number written
   into a constant.
2. **Auditable simplicity beats accumulating complexity.** A protocol
   you can read in an evening is safer, in the long run, than one
   you can't.
3. **A protocol that pays for its own shrinkage will eventually
   shrink itself out of needing to pay anyone.** The reward loop is
   self-extinguishing. When the work is done, the subsidy ends.

If those three are right, Moire becomes a small, finished, transparent
monetary system that no one needs to maintain. If they are wrong,
Moire is an interesting failed experiment. Either way, it is finite.

---

*For the technical specification, equations, parameter derivations,
and threat-model details, see `WHITEPAPER.md`. For the on-chain
constitution, see `constitution.md`.*
