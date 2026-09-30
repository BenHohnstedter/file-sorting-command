#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROJECT="$(basename "$REPO_ROOT")"
BRANCH="${BRANCH:-main}"

echo "[homelab] $PROJECT | Branch: $BRANCH (nur Git-Sync, kein Web-Dienst)"

git fetch -q origin "$BRANCH"
git reset -q --hard "origin/$BRANCH"

if ! git ls-remote --heads origin develop | grep -qP '\trefs/heads/develop$'; then
    git branch -f develop "origin/$BRANCH"
    git push -q -u origin develop
fi

echo "[homelab] $PROJECT aktualisiert (kein Container)"