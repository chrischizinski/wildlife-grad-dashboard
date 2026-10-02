#!/usr/bin/env bash
# Remove email addresses and contact_info from the JSON files attached to the
# rolling `data-archive` GitHub release (public downloads).
#
# Dry run by default: downloads the assets and reports how many emails each
# holds. Pass --apply to scrub them and re-upload in place (same file names).
#
# Usage: scripts/scrub_release_assets.sh [--apply] [release-tag]
set -euo pipefail

APPLY=0
if [ "${1:-}" = "--apply" ]; then
  APPLY=1
  shift
fi
TAG="${1:-data-archive}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+'

gh release download "$TAG" --dir "$WORK" --pattern '*.json'

total=0
dirty=0
for f in "$WORK"/*.json; do
  total=$((total + 1))
  # grep exits 1 on "no match"; don't let pipefail treat that as failure
  n=$({ grep -oE "$EMAIL_RE" "$f" || true; } | sort -u | wc -l | tr -d ' ')
  if [ "$n" -gt 0 ]; then
    dirty=$((dirty + 1))
    echo "$n distinct emails: $(basename "$f")"
  fi
done
echo "$dirty of $total assets contain emails"

if [ "$APPLY" -ne 1 ]; then
  echo "Dry run only. Re-run with --apply to scrub and re-upload."
  exit 0
fi

ORIG="$(mktemp -d)"
trap 'rm -rf "$WORK" "$ORIG"' EXIT
cp "$WORK"/*.json "$ORIG"/

python3 "$ROOT/scripts/sanitize_published_data.py" "$WORK"

for f in "$WORK"/*.json; do
  if grep -qE "$EMAIL_RE" "$f"; then
    echo "ERROR: emails remain in $(basename "$f"); not uploading" >&2
    exit 1
  fi
done

# Upload only the files that changed (re-uploading identical files is harmless
# but slow); --clobber replaces the asset of the same name.
for f in "$WORK"/*.json; do
  if ! cmp -s "$f" "$ORIG/$(basename "$f")"; then
    gh release upload "$TAG" "$f" --clobber
    echo "re-uploaded: $(basename "$f")"
  fi
done
