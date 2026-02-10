#!/usr/bin/env bash
set -euo pipefail

# Always run from the script's own directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HTML_FILE="calendar.html"

# Commit & push every day, even if nothing changed
git add "$HTML_FILE" arrivals.html departures.html quick_overview.html
git commit -m "Daily update $(date -u '+%Y-%m-%d %H:%M:%SZ')" || true
git push origin master
