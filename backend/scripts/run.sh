#!/bin/bash
# Helper script to run utility scripts from any directory
# Usage: scripts/run.sh cleanup_orphaned_samples.py --stats

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR" || exit 1

if [ $# -eq 0 ]; then
    echo "Usage: scripts/run.sh <script_name> [args...]"
    echo ""
    echo "Available scripts:"
    ls -1 "$SCRIPT_DIR"/*.py | xargs -n1 basename
    exit 1
fi

SCRIPT_NAME="$1"
shift

# Add .py extension if not present
if [[ ! "$SCRIPT_NAME" =~ \.py$ ]]; then
    SCRIPT_NAME="${SCRIPT_NAME}.py"
fi

SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Script not found: $SCRIPT_NAME"
    echo ""
    echo "Available scripts:"
    ls -1 "$SCRIPT_DIR"/*.py | xargs -n1 basename
    exit 1
fi

python "$SCRIPT_PATH" "$@"