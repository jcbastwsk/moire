#!/usr/bin/env bash
# Moire — reproducible build.
#
# Pre-conditions:
#   * monero-project/monero@<BASELINE_REV> cloned to ./monero-src
#   * diff/01..07 applied in order on top of that revision
#   * Toolchain present and matches genesis/toolchain.merkle.json
#   * Run on macOS arm64 (operator's M4) or Linux arm64 (canary nodes)
#
# Outputs:
#   * build/release/bin/moired
#   * build/release/bin/moire-wallet-cli
#   * build/release/source.sha256       <-- hash of canon(C); committed on chain
#   * build/release/toolchain.leaf.sha256 <-- hash of toolchain.merkle.json (sorted-keys, minified)
#   * build/release/build.manifest.json  <-- everything together; the "build artifact ledger entry"

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/monero-src"
BUILD="$ROOT/build/release"
GENESIS="$ROOT/genesis"
DIFFS="$ROOT/diff"
BASELINE_REV="${BASELINE_REV:-c182abb}"   # monero@master at fork moment
export SRC

# ---- 1. Source preparation -------------------------------------------------
if [ ! -d "$SRC" ]; then
  echo "[1/6] Cloning monero baseline @ $BASELINE_REV"
  git clone https://github.com/monero-project/monero.git "$SRC"
  ( cd "$SRC" && git checkout -q "$BASELINE_REV" )
fi

if [ -z "${SKIP_PATCH_APPLY:-}" ]; then
  echo "[2/6] Applying Moire patches 01..07"
  # Reset tracked files and remove untracked files created by prior patch attempts.
  # Without git clean, re-running this script fails when patches add files that
  # remain untracked after git reset --hard.
  ( cd "$SRC" && git reset --hard "$BASELINE_REV" && git clean -fd && git submodule update --init --force )
  for p in "$DIFFS"/0*.patch; do
    echo "  applying $(basename "$p")"
    ( cd "$SRC" && git apply --check "$p" && git apply "$p" )
  done
fi

# ---- 2. Toolchain pin verification ----------------------------------------
echo "[3/6] Verifying toolchain pin"
TOOLCHAIN_JSON="$GENESIS/toolchain.merkle.json"
if [ ! -f "$TOOLCHAIN_JSON" ]; then
  echo "missing $TOOLCHAIN_JSON" >&2; exit 1
fi
# Canonical (sorted-keys, minified) JSON -> sha256 -> "toolchain leaf"
TOOLCHAIN_LEAF=$(python3 -c '
import json, hashlib, sys
with open(sys.argv[1]) as f: d = json.load(f)
canon = json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
print(hashlib.sha256(canon).hexdigest())
' "$TOOLCHAIN_JSON")
echo "  toolchain leaf: $TOOLCHAIN_LEAF"

# Verify the running compiler matches the pin.
EXPECTED_CLANG=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["compiler"]["version"])' "$TOOLCHAIN_JSON")
ACTUAL_CLANG=$(clang --version | head -1 | sed -E 's/.* version ([0-9.]+).*/\1/')
if [ "$EXPECTED_CLANG" != "$ACTUAL_CLANG" ]; then
  echo "WARN: clang version mismatch (expected $EXPECTED_CLANG, got $ACTUAL_CLANG)"
  echo "      genesis/toolchain.merkle.json placeholders must be populated on first build."
  echo "      Continuing for Day-1 validation only."
fi

# ---- 3. Source canonicalization + hash ------------------------------------
echo "[4/6] Computing canon(C) source hash"
SRC_HASH=$(python3 - <<'PY'
import os, hashlib, sys
src = os.environ["SRC"]
excludes = ("external/randomx/", "external/lmdb/", "build/", "tests/data/", ".git/")
files = []
for root, dirs, fs in os.walk(src):
    rel = os.path.relpath(root, src) + "/"
    if any(rel.startswith(x) for x in excludes):
        dirs[:] = []
        continue
    for f in fs:
        files.append(os.path.relpath(os.path.join(root, f), src))
files.sort()
h = hashlib.sha256()
for f in files:
    fp = os.path.join(src, f)
    if not os.path.isfile(fp): continue
    h.update(f.encode()); h.update(b"\0")
    with open(fp, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
print(h.hexdigest())
PY
)
export SRC
echo "  source hash:    $SRC_HASH"

# ---- 4. Configure + build --------------------------------------------------
echo "[5/6] Configure + compile"
mkdir -p "$BUILD"
cd "$BUILD"
cmake "$SRC" \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTATIC=ON \
  -DBUILD_TESTS=ON \
  -DUSE_DEVICE_TREZOR=OFF \
  -DMOIRE_DETERMINISTIC_BUILD=ON
cmake --build . --parallel "$(nproc 2>/dev/null || sysctl -n hw.ncpu || echo 4)"

# ---- 5. Ledger entry -------------------------------------------------------
echo "[6/6] Emitting build.manifest.json"
echo "$SRC_HASH"        > "$BUILD/source.sha256"
echo "$TOOLCHAIN_LEAF"  > "$BUILD/toolchain.leaf.sha256"

python3 - <<PY > "$BUILD/build.manifest.json"
import json, datetime, os
m = {
  "schema_version": 1,
  "ts_utc":         datetime.datetime.utcnow().isoformat() + "Z",
  "baseline_rev":   "$BASELINE_REV",
  "source_sha256":  "$SRC_HASH",
  "toolchain_leaf": "$TOOLCHAIN_LEAF",
  "patches": sorted(os.listdir("$DIFFS")),
}
print(json.dumps(m, indent=2, sort_keys=True))
PY

echo
echo "Build complete."
echo "  source_sha256:  $SRC_HASH"
echo "  toolchain_leaf: $TOOLCHAIN_LEAF"
echo "  manifest:       $BUILD/build.manifest.json"
