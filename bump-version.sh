#!/usr/bin/env bash
# bump-version.sh — bump version across all files and open+merge a PR
#
# Usage:
#   ./bump-version.sh <new-version>        # e.g. ./bump-version.sh 0.7.5
#   ./bump-version.sh <new-version> --dry  # print changes without writing
#
# Files updated:
#   pyproject.toml        — version = "..."
#   server.json           — top-level "version" + packages[0] "version"
#   src/landing.py        — statusbar, badge, news-box, footer
#
# Git workflow (mirrors CLAUDE.md ruleset):
#   main (pull) → branch bump-<version> → commit → push → gh pr create → gh pr merge --squash

set -euo pipefail

# ── Args ─────────────────────────────────────────────────────────────────────

NEW_VERSION="${1:-}"
DRY=false
[[ "${2:-}" == "--dry" ]] && DRY=true

if [[ -z "$NEW_VERSION" ]]; then
  echo "Usage: $0 <new-version> [--dry]"
  echo "  Example: $0 0.7.5"
  exit 1
fi

if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: version must be semver (e.g. 0.7.5), got: $NEW_VERSION"
  exit 1
fi

# ── Detect current versions (each file may differ) ───────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CURRENT_VERSION=$(grep -m1 '^version = ' pyproject.toml | sed 's/version = "//;s/"//')

if [[ -z "$CURRENT_VERSION" ]]; then
  echo "Error: could not detect current version from pyproject.toml"
  exit 1
fi

# landing.py may lag behind — detect its version independently
LANDING_VERSION=$(grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' src/landing.py | head -1 | tr -d 'v')
if [[ -z "$LANDING_VERSION" ]]; then
  LANDING_VERSION="$CURRENT_VERSION"
fi

echo "Current version (pyproject.toml / server.json) : $CURRENT_VERSION"
echo "Current version (src/landing.py)               : $LANDING_VERSION"
echo "New version                                     : $NEW_VERSION"
echo ""

if [[ "$CURRENT_VERSION" == "$NEW_VERSION" && "$LANDING_VERSION" == "$NEW_VERSION" ]]; then
  echo "Already at $NEW_VERSION everywhere — nothing to do."
  exit 0
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

do_sed() {
  # Portable in-place sed (macOS uses BSD sed; -i '' works on both)
  local pattern="$1" file="$2"
  if $DRY; then
    echo "  [dry] sed '$pattern' $file"
  else
    sed -i '' "$pattern" "$file"
  fi
}

# ── Update files ──────────────────────────────────────────────────────────────

echo "==> pyproject.toml"
do_sed "s/^version = \"${CURRENT_VERSION}\"/version = \"${NEW_VERSION}\"/" pyproject.toml

echo "==> server.json"
# Top-level "version" field and packages[0] version field — both share the same value
do_sed "s/\"version\": \"${CURRENT_VERSION}\"/\"version\": \"${NEW_VERSION}\"/g" server.json

echo "==> src/landing.py  (from $LANDING_VERSION)"
do_sed "s/VERSION ${LANDING_VERSION}/VERSION ${NEW_VERSION}/g"   src/landing.py
do_sed "s/v${LANDING_VERSION}/v${NEW_VERSION}/g"                  src/landing.py

echo ""

# ── Verify no stale references remain ────────────────────────────────────────

if ! $DRY; then
  STALE=""
  # Check for old version in pyproject.toml and server.json
  STALE+=$(grep -n "$CURRENT_VERSION" pyproject.toml server.json 2>/dev/null || true)
  # Check for old landing.py version (may differ)
  STALE+=$(grep -n "v${LANDING_VERSION}\|VERSION ${LANDING_VERSION}" src/landing.py 2>/dev/null || true)
  if [[ -n "$STALE" ]]; then
    echo "WARNING: stale version string still found:"
    echo "$STALE"
    echo ""
    echo "Fix manually, then re-run or commit by hand."
    exit 1
  fi
  echo "All files updated — no stale references."
  echo ""
fi

# ── Git workflow ──────────────────────────────────────────────────────────────

if $DRY; then
  echo "[dry run] Would create branch bump-${NEW_VERSION}, commit, push, PR, and merge."
  exit 0
fi

BRANCH="bump-${NEW_VERSION}"

echo "==> git: syncing main"
git checkout main
git pull origin main

echo "==> git: creating branch $BRANCH"
git checkout -b "$BRANCH"

echo "==> git: staging changed files"
git add pyproject.toml server.json src/landing.py

echo "==> git: committing"
git commit -m "chore: bump version to ${NEW_VERSION}"

echo "==> git: pushing $BRANCH"
git push origin "$BRANCH"

echo "==> gh: creating PR"
PR_URL=$(gh pr create \
  --title "chore: bump version to ${NEW_VERSION}" \
  --body "$(cat <<EOF
## Summary
- Bump version from \`${CURRENT_VERSION}\` to \`${NEW_VERSION}\` in \`pyproject.toml\`, \`server.json\`, and \`src/landing.py\`

## Files changed
- \`pyproject.toml\` — \`version\`
- \`server.json\` — top-level \`version\` + \`packages[0].version\`
- \`src/landing.py\` — statusbar, badge, news-box, footer
EOF
)" \
  --base main \
  --head "$BRANCH")

echo "PR: $PR_URL"

PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')

echo "==> gh: merging PR #${PR_NUMBER} (squash)"
gh pr merge "$PR_NUMBER" --squash --delete-branch

echo "==> git: pulling merged main"
git checkout main
git pull origin main

echo ""
echo "Done. Version is now ${NEW_VERSION}."
