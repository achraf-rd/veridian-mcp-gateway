#!/bin/sh
set -e
# Inside a container Traefik must reach us, so bind all interfaces (code default is local-only).
export GATEWAY_HOST=0.0.0.0
export GATEWAY_PORT="${GATEWAY_PORT:-8100}"
exec uv run python server.py
