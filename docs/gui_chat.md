# Moire — Bundled Client (Node + Miner + Wallet + Chat)

**Single binary.** `moire-client`. Four panes. No web view, no Electron, no Qt theme drift.

This document spans the presentation layer and the chat overlay. Both are
explicitly **layer-7** — they do not enter consensus. They evolve under the
same reduction gradient as everything else (constitution Article XIII).

---

## 1. The binary

`moire-client` bundles:

| Pane | Role |
|---|---|
| Node | block height, peer count, sync status, mempool, recent blocks. |
| Miner | RandomX threads, hashrate, reward earned this epoch (PoA phase only). |
| Wallet | balance, send, receive (stealth addr), tx history, reduce-tx submit. |
| Chat | channels, NAMES list, message scrollback, /commands. |

These are panes of one application, not four programs. They share:

- The local node process (in-process; no IPC). The GUI thread runs the Dear
  ImGui loop; a background thread runs the daemon loop. They communicate via
  lock-free SPSC queues for tx submission and event delivery.
- The wallet keystore (one file per identity, encrypted at rest with the
  user's passphrase via libsodium `crypto_secretstream`).
- The chat identity (derived from the wallet spend-key — see §4.2).

`moired` (the headless daemon binary, output by patch 01) and
`moire-wallet-cli` continue to ship for ops/automation/test scenarios.
`moire-client` is the human-facing surface.

---

## 2. GUI stack — Dear ImGui + GLFW

Picked over Qt, Tauri, Electron, AppKit, GTK, Slint, etc. because:

- **Single-file headers.** ImGui core ≈ 12 kLOC across ~6 files. GLFW ≈ 20
  kLOC. Both vendor cleanly as submodules with hashes pinned in
  `genesis/toolchain.merkle.json`.
- **No platform widget drift.** Renders identically across macOS, Linux,
  Windows. Reproducible visual output is a property of the build.
- **No JavaScript runtime.** No V8, no Webkit, no Chromium. The reduction
  gradient cannot reach into Electron; it can reach every line of ImGui.
- **No theme system.** Colors are constants. One look. (Manifesto §I:
  primitives over products.)
- **Trivial deletion.** When a pane is dropped via `reduce(ΔC)`, the diff
  is contained.

What we do **not** add:

- No CSS, no HTML, no skinning engine.
- No animation framework. Polls at 30 Hz, draws what changed.
- No internationalization framework — the binary is English-only at v0.1;
  i18n is a post-mainnet reduction-cycle decision.
- No accessibility shim. (Tracked as a known gap in `notes/known_gaps.md`.)

### File layout (added by patch 08, scaffolded as a stub today)

```
src/client/
  CMakeLists.txt
  main.cpp                 // entrypoint; arg parsing; spawns daemon thread + ImGui loop
  app.{h,cpp}              // application state; pane registry
  ui/
    pane_node.{h,cpp}
    pane_miner.{h,cpp}
    pane_wallet.{h,cpp}
    pane_chat.{h,cpp}
    theme.{h,cpp}          // single struct of color constants
  bridge/
    daemon_bridge.{h,cpp}  // SPSC queues to/from cryptonote_core
    wallet_bridge.{h,cpp}  // SPSC queues to/from wallet
external/
  imgui/                   // submodule, pinned
  glfw/                    // submodule, pinned
```

CMake target: `moire-client` (added in patch 08). Output binary:
`moire-client[.exe]`.

---

## 3. Chat — what it is and what it isn't

### What it is

An IRC-flavored, decentralized, gossip-borne chat overlay. Channels, nicks,
private messages, `/commands`. Wire-format minimal. Identity is
cryptographic, not registered. Messages are signed and ephemeral.

### What it isn't

- **Not on chain.** Chat messages are not transactions. They never enter the
  Merkle history. They never affect issuance.
- **Not consensus-protected.** A node can drop messages, censor a channel,
  or refuse to relay. The protocol is best-effort, like IRC over a flooding
  mesh.
- **Not Discord.** No avatars, no rich embeds, no reactions, no threads, no
  voice, no video. If you want any of those, build a different product.
- **Not anonymous.** Identities are pseudonymous (sha256(pubkey) prefix).
  If you need anonymity, route the client through Tor at the OS level.

### Why it ships in v0.1

The point of bundling chat with the client is **operator coordination**:
operators of canary nodes, reduction-patch issuers, and miners want a
common watering hole that doesn't depend on a third party (Discord, Slack,
Matrix). The chat is to Moire what `#bitcoin-dev` was to Bitcoin in 2010,
except it lives **inside the wallet** with no external service to fail.

---

## 4. Chat protocol — MIRC v0.1

### 4.1 Transport

Chat rides on the existing P2P gossip layer (the one Moire inherits from
Monero and that already carries blocks and txs). One new opcode:

```
P2P_COMMAND_CHAT_MSG = 2010   // 0x7DA — distinct from existing block/tx codes
```

Payload schema (binary, little-endian, fixed offsets):

| Offset | Bytes | Field |
|---|---:|---|
| 0  | 1  | version (= 0x01) |
| 1  | 1  | opcode (see §4.4) |
| 2  | 8  | nonce (anti-replay; per-sender monotonic) |
| 10 | 8  | timestamp_unix_seconds |
| 18 | 8  | ttl_blocks (default 144 ≈ 2.4 h @ 60 s) |
| 26 | 8  | channel_topic (= sha256(channel_name_lower)[:8]) |
| 34 | 32 | sender_pubkey (curve25519, derived from wallet spend-key) |
| 66 | 64 | signature (Ed25519 over bytes [0..66]+payload) |
| 130 | 2  | payload_len |
| 132 | N  | payload (UTF-8) |

Total minimum frame: 132 bytes + payload. Hard cap on payload: 4096 bytes.
Hard cap on per-node chat bandwidth: 64 KB/s (configurable, default).

### 4.2 Identity

A chat identity is derived deterministically from the wallet:

```
chat_seed       = sha256("moire-chat" || wallet_spend_secret)[:32]
chat_keypair    = ed25519_from_seed(chat_seed)
sender_pubkey   = chat_keypair.public
nick_default    = "u" + base58(sha256(sender_pubkey)[:6])   // 8-char vanity
```

The nick is **derived**, not chosen. A user can set a `display_name` locally
that the GUI shows next to the canonical nick, but other clients see only
the canonical form. This eliminates impersonation: there is one true nick
per pubkey, and the pubkey is signed into every message.

If the user nukes the wallet, the chat identity dies with it. There is no
recovery flow because there is no central registry to recover from.

### 4.3 Channels

Channels are first-class but unowned. To "join" a channel, a client begins
filtering inbound messages by `channel_topic = sha256(name_lower)[:8]` and
emitting `JOIN` opcodes for membership announcements. There is no channel
registration, no operator, no kickban (clients can locally mute).

Reserved channels (gossip-amplified by all canary nodes by default):

| Name | Purpose |
|---|---|
| `#general` | Operator hangout. |
| `#por-cycles` | Reduction-patch coordination. |
| `#canary` | Canary-node status reports (machine-emitted). |
| `#mempool` | High-fee tx alerts (machine-emitted). |
| `#help` | New-operator support. |

Other channels exist as soon as someone gossips a `JOIN` for them.

### 4.4 Opcodes

Mirror IRC's RFC 1459 minimal set, in numeric form:

| Opcode | Name | Payload |
|---:|---|---|
| 0x01 | JOIN     | (channel_name UTF-8) |
| 0x02 | PART     | (channel_name UTF-8) |
| 0x03 | PRIVMSG  | (text UTF-8) — to channel = channel_topic |
| 0x04 | NOTICE   | (text UTF-8) — like PRIVMSG, suppressed in alerts |
| 0x05 | TOPIC    | (text UTF-8) — set channel topic line (last writer wins per node) |
| 0x06 | NAMES    | (no payload) — request current channel members |
| 0x07 | NAMES_R  | (concat of pubkey || nick_len || nick for each member) |
| 0x08 | LIST     | (no payload) — request known channels |
| 0x09 | LIST_R   | (concat of channel_topic || name_len || name) |
| 0x0A | DIRECT   | (recipient_pubkey || ciphertext) — encrypted DM via curve25519 |
| 0x0B | ME       | (text UTF-8) — /me action |

Anything else is dropped. The set is intentionally tiny so the reduction
gradient can shrink it.

### 4.5 Anti-flood and TTL

- Per-sender, per-channel rate limit: 10 messages / 10 seconds. Enforced by
  every relayer; over-limit messages are dropped silently.
- Global per-node chat bandwidth: 64 KB/s default; over-limit triggers
  random-drop with weight inversely proportional to sender's recent volume.
- TTL: every chat message carries `ttl_blocks`. After that many blocks past
  `timestamp`, the message is dropped from local cache. Default 144 blocks
  (≈ 2.4 h). Hard ceiling: 1440 (one day).
- No persistent backlog. Joining a channel shows you only what nodes around
  you still hold. (Like IRC: if you weren't there, you weren't there.)

### 4.6 Encryption

`PRIVMSG` is plaintext (anyone can read; channel chat is public).
`DIRECT` is encrypted: `ciphertext = crypto_box(payload, recipient_pubkey,
sender_secret, nonce)`. Forward secrecy is not provided in v0.1.

### 4.7 Spam

Every message costs the sender bandwidth and a signature. There is no
fee-per-message in v0.1; if spam becomes a real problem, we add a tiny
proof-of-work tag (3 leading zero bits in
`sha256(frame || pow_nonce)`) — that's a future reduction-pressure
addition, not a v0.1 lever. The gossip layer is rate-limited at the relayer
side (§4.5), so flooding burns the spammer's bandwidth without harming the
network.

---

## 5. Chat pane (GUI)

```
┌──────────────────────────────────────────────────────────┐
│ Moire Client v0.1     [Node] [Miner] [Wallet] [Chat *] │
├────────────────┬─────────────────────────────────────────┤
│ Channels       │ #por-cycles                             │
│ ✓ #general     │ Topic: Reduction proposals welcome.     │
│   #por-cycles  ├─────────────────────────────────────────┤
│ ✓ #canary      │ 21:14 u2g4f3 joined                     │
│   #mempool     │ 21:14 u9k2m1: heads up — patch 02b done │
│   #help        │ 21:14 *  u9k2m1 commits sha 7a3b...     │
│                │ 21:15 u3p1q2: nice. CI green?           │
│ ─── DMs ───    │ 21:16 u9k2m1: green on M4. running      │
│   u3p1q2       │             canary now.                 │
│   u7n8r5       │                                         │
│                │                                         │
│                ├─────────────────────────────────────────┤
│ Members: 14    │ /me ▏                                   │
└────────────────┴─────────────────────────────────────────┘
```

ImGui draws this in well under 200 LOC. Scrollback is bounded (default 500
lines per channel). No images. No links — bare URLs render as text; the user
copies them out.

---

## 6. Slash commands (parser is one switch)

```
/join #foo
/part [#foo]
/msg <nick|pubkey6> <text>     // opens DM and sends
/me <action>
/topic <text>                  // for current channel
/names
/list
/quit
/nick <display_name>           // local display only; canonical nick is derived
/raw <hex>                     // emergency frame injection (debug)
```

That's the entire command set. Reduction targets later.

---

## 7. Reduction telos for client + chat

Both surfaces are explicitly subject to the same reduction gradient as the
core protocol. Phases-2-and-onward roadmap items target them:

- Drop unused chat opcodes if they go unused for 90 days.
- Collapse the four panes into a single tab strip if dual-pane affordance
  goes unused.
- Replace ImGui with a custom 2 kLOC immediate-mode draw loop once the UI
  shape stabilizes.
- Shrink the chat frame fixed header (currently 132 bytes; `nonce` and
  `ttl_blocks` are 8 bytes apiece and probably overkill).

The client and chat protocol versions evolve via `reduce(ΔC)` like any
other code. There is no app store. There is no auto-update except through
the canary-then-promote mechanism (constitution Article VIII).

---

## 8. What ships in patch 08 (Hermes Day-2 work)

Scaffold only — no integration with the daemon yet:

- `src/client/CMakeLists.txt`
- `src/client/main.cpp` (~30 LOC: opens an ImGui window, draws four empty
  tabs labeled Node/Miner/Wallet/Chat).
- `external/imgui/` and `external/glfw/` submodule entries with hashes
  pinned in `genesis/toolchain.merkle.json` (added to the toolchain
  manifest section, since they participate in the reproducible build).

Patch 09 (Session 6 in roadmap) adds the daemon-bridge and the chat
opcode wiring. Patch 10 (Session 7) wires the wallet pane.

This is layer-7 work: it does not touch consensus, the constitution, or
the formal spec. The reduction oracle treats the GUI/chat code identically
to any other source under `canon(C)`.
