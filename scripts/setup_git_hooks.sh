#!/usr/bin/env bash
# Install repo git hooks (replaces Cursor co-author with Jahangir on commit).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp "$ROOT/.githooks/commit-msg" "$ROOT/.git/hooks/commit-msg"
chmod +x "$ROOT/.git/hooks/commit-msg"
echo "Installed commit-msg hook: Cursor co-author -> Jahangir"
