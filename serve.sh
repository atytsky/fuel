#!/bin/sh
# Локальный запуск: обновить данные и открыть SPA
cd "$(dirname "$0")"
python3 parser.py "$@" && (sleep 1; open http://localhost:8765) & python3 -m http.server 8765
