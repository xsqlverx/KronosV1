#!/bin/bash
set -e
cd "$(dirname "$0")"
for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)' 2>/dev/null; then
        exec "$candidate" scripts/bootstrap_kronos.py "$@"
    fi
done
echo "Install Python 3.11 or 3.12, then run: bash start-kronos.command"
exit 2
