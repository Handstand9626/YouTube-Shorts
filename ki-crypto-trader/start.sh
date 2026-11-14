#!/bin/sh
# KI Crypto Trader starten (Paper-Trading, kein echtes Geld)
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 start.py "$@"
fi
exec python start.py "$@"
