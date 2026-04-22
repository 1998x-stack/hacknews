#!/usr/bin/env bash
set -euo pipefail

# send.sh — Send saved Markdown digest via email
#
# Usage:
#   ./scripts/send.sh
#   ./scripts/send.sh --date 2026-04-20

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

python -m hacknews send "$@"
