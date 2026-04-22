#!/usr/bin/env bash
set -euo pipefail

# scrape.sh — Fetch HN stories, extract content, save HTML + Markdown locally
#
# Usage:
#   ./scripts/scrape.sh
#   HN_TOP_N=20 ./scripts/scrape.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

python -m hacknews scrape
