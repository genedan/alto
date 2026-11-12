#!/bin/sh
# Warn when the interface has changed since the screenshots in docs/assets/img were last updated.
# It only warns, so a small interface change never blocks a push. Set ALTO_DOCS_STRICT=1 to make it fail instead.
cd "$(dirname "$0")/.." || exit 1
last=$(git log -1 --format=%H -- docs/assets/img 2>/dev/null)
[ -n "$last" ] || exit 0
count=$(git rev-list --count "$last"..HEAD -- alto/ui)
[ "$count" -gt 0 ] || { echo "Docs screenshots are up to date with alto/ui."; exit 0; }
echo "The interface (alto/ui) has changed in $count commit(s) since the docs screenshots were last updated:"
git log --format='  %h %s' "$last"..HEAD -- alto/ui | head -8
echo "Check the docs pages and regenerate the pictures:  .venv/bin/python scripts/screenshots.py"
[ "${ALTO_DOCS_STRICT:-0}" = 1 ] && exit 1
exit 0
