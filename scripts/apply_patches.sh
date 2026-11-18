#!/usr/bin/env bash
# Apply patches/*.diff to third_party/LAPA (idempotent). Called by env/install.sh and checked by eval.py.
set -euo pipefail
cd "$(dirname "$0")/../third_party/LAPA"
for p in ../../patches/*.diff; do
  [ -e "$p" ] || continue
  if git apply --reverse --check "$p" 2>/dev/null; then
    echo "already applied: $(basename "$p")"
  else
    git apply "$p" && echo "applied: $(basename "$p")"
  fi
done
