#!/usr/bin/env bash
# Scan git-tracked files for likely secrets / personal identifiers.
# Run before committing to catch credentials or real IDs headed for a public repo.
#
#   bash scripts/scan-secrets.sh
#
# Exits non-zero when a likely finding appears, so it can gate a pre-commit hook
# or CI step. Test fixtures and docs placeholders are excluded where appropriate.
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root" || exit 1

# Tracked files, excluding test fixtures (they contain real sample HTML).
files=$(git ls-files -- ':(exclude)tests/fixtures/*')

fail=0

scan() {
  local label="$1"; shift
  local pattern="$1"
  local hits
  hits=$(printf '%s\n' "$files" | tr -d '\r' | xargs -r grep -nIE "$pattern" 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "❌ [$label]"
    echo "$hits" | sed 's/^/    /'
    fail=1
  else
    echo "✅ [$label] clean"
  fi
}

echo "Scanning $(printf '%s\n' "$files" | wc -l | tr -d ' ') tracked files..."
echo

# Real API keys by common prefixes (allow obvious test/placeholder values).
scan "API key (oc_sk_ / ark-)" 'oc_sk_[A-Za-z0-9_-]{10,}|ark-[0-9a-f]{8}-'
# SMTP / generic secrets assigned a real-looking value.
scan "secret assignment"       '(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*["'"'"'][^"'"'"'<]{12,}["'"'"']'
# Real corporate / personal email domains (not example.com).
scan "real email domain"       '@(qq|gmail|outlook|163|126|servyou)\.[a-z]+'
# WeChat peer / bot identifiers.
scan "WeChat identifier"       '[a-z0-9]{12,}@im\.wechat|im-bot'
# Long bearer tokens.
scan "bearer token"            'Bearer [A-Za-z0-9._-]{20,}'

echo
if [ "$fail" -ne 0 ]; then
  echo "Found potential secrets. Review before committing."
  exit 1
fi
echo "No secrets detected."
