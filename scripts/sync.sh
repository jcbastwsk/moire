#!/usr/bin/env bash
# Moire — sync to remote.
#
# Operator usage:
#   ./scripts/sync.sh                # pull, then push (default branch: main)
#   ./scripts/sync.sh push           # push only
#   ./scripts/sync.sh pull           # pull only
#   ./scripts/sync.sh init <url>     # one-time: set the remote URL
#   ./scripts/sync.sh status         # show ahead/behind + dirty state
#
# The remote URL is read from `git config remote.origin.url`. To set it:
#   ./scripts/sync.sh init git@github.com:<user>/moire.git
# or equivalently:
#   git remote add origin git@github.com:<user>/moire.git
#
# This script makes no assumptions about the remote provider (GitHub, Gitea,
# Codeberg, self-hosted). It is the operator's choice.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

cmd="${1:-sync}"

case "$cmd" in
  init)
    if [ -z "${2:-}" ]; then
      echo "usage: $0 init <remote_url>" >&2; exit 2
    fi
    if git remote | grep -q '^origin$'; then
      git remote set-url origin "$2"
    else
      git remote add origin "$2"
    fi
    echo "remote.origin.url := $(git remote get-url origin)"
    ;;

  status)
    git fetch -q origin 2>/dev/null || true
    branch=$(git rev-parse --abbrev-ref HEAD)
    ahead=$(git rev-list --count "@{u}"..HEAD 2>/dev/null || echo "?")
    behind=$(git rev-list --count HEAD.."@{u}" 2>/dev/null || echo "?")
    dirty=$(git status --porcelain | wc -l | tr -d ' ')
    echo "branch:   $branch"
    echo "ahead:    $ahead"
    echo "behind:   $behind"
    echo "dirty:    $dirty file(s)"
    ;;

  push)
    branch=$(git rev-parse --abbrev-ref HEAD)
    git push origin "$branch"
    ;;

  pull)
    branch=$(git rev-parse --abbrev-ref HEAD)
    git pull --ff-only origin "$branch"
    ;;

  sync|"")
    if ! git remote | grep -q '^origin$'; then
      echo "no remote configured. run: $0 init <remote_url>" >&2
      exit 1
    fi
    branch=$(git rev-parse --abbrev-ref HEAD)
    echo "[1/2] pulling $branch from origin"
    git pull --ff-only origin "$branch"
    echo "[2/2] pushing $branch to origin"
    git push origin "$branch"
    echo "synced."
    ;;

  *)
    echo "unknown command: $cmd" >&2
    echo "usage: $0 [sync|push|pull|init <url>|status]" >&2
    exit 2
    ;;
esac
