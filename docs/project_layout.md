# Hermes Project Layout Convention

**As of 2026-05-06.** Established by operator jcb during Day-1 of Moire.

---

## Where projects live

All Hermes projects live under `~/Projects/`. One directory per project, named
in lowercase with no spaces. Examples already in place on this machine:

```
~/Projects/
├── all-hands/
├── crypto-games/
├── dewey/
├── hermes-dashboard/
├── hyperframes-cinematic-demo/
├── moire/                       <-- this project
├── pit/
├── research/
└── youtube/
```

The previous convention (`~/.hermes/Projects/<name>/`) is **deprecated** as of
the move that produced this file. Projects in the old location should be moved
when convenient. See the breadcrumb at `~/.hermes/Projects/distill/MOVED.md`.

---

## Per-project structure

Every Hermes project follows the same skeleton:

```
~/Projects/<name>/
├── .git/                # local git history
├── .gitignore           # build artifacts, OS cruft
├── README.md            # short. what is this project, how to run it
├── DESIGN.md            # the architecture; the math; the invariants
├── BUILD_LOG.md         # append-only ledger of sessions and decisions
├── HERMES_HANDOFF.md    # pickup brief for the next agent (Hermes M4 etc.)
├── roadmap.md           # session-by-session plan
├── scripts/
│   └── sync.sh          # ./scripts/sync.sh [sync|push|pull|init <url>|status]
├── docs/                # supporting design docs
├── notes/               # working notes, scratch
└── (project-specific)   # diff/, genesis/, src/, etc.
```

A project that doesn't need one of these files just doesn't have it. There is
no template ceremony.

---

## Sync

Each project is a git repo with one remote, named `origin`. The operator
chooses the remote provider (GitHub, Gitea, Codeberg, self-hosted) on a
per-project basis.

### One-time setup per project

```bash
cd ~/Projects/<name>
./scripts/sync.sh init <remote_url>
./scripts/sync.sh push    # first push
```

### Ongoing

```bash
cd ~/Projects/<name>
./scripts/sync.sh         # pull then push
```

Or run it from a launchd / cron job for autosync. A reasonable interval is
every 15 minutes during active work, hourly otherwise.

### Multi-machine

If the operator runs Moire on both the M4 and another machine (a canary
node, a build farm node), sync is the substrate that keeps them aligned.
Both clone the same remote; both run `./scripts/sync.sh` after every change.
There is no other coordination protocol — git is the protocol.

---

## What goes in git, what doesn't

**In git:**

- Source, design, docs, configs, patches.
- `genesis/toolchain.merkle.json` (the manifest itself; the *real* hashes
  Hermes populates also go in git — that's the point).
- `BUILD_LOG.md` (append-only; conflicts mean two agents wrote at once,
  resolve by concatenating both entries).

**Not in git** (covered by `.gitignore`):

- `build/` artifacts.
- The cloned baseline source (`monero-src/` for Moire, etc.) — it's a
  read-only mirror of an upstream repo; clone fresh on each machine.
- OS cruft (`.DS_Store`, swap files, IDE config).

---

## Naming convention

- Project directory name: lowercase, hyphenated. `moire`, `hermes-dashboard`,
  `crypto-games`. Mirrors the project's own preferred display name.
- Branch names: `main` is canonical. Feature branches use `<topic>` form:
  `por-oracle`, `client-scaffold`, `gui-chat`.
- Commit messages: imperative mood, ≤ 72 char subject, blank line, body.
  Example: `patch 03: PoA oracle`.

---

## When in doubt

The operator's manifesto (CB v0.4) is the tiebreaker. Ruthless minimalism.
Primitives over products. Hash-sealed artifacts. Conversation as a closed-loop
compiler whose outputs reproduce themselves.
