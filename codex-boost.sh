#!/usr/bin/env bash
set -euo pipefail

export CODEX_MODE=evolution
export CODEX_CLUSTER=true
export CODEX_SWARM_SIZE=2
export CODEX_LOG=./ops/logs/codex.jsonl
export PROMETHEUS_URL=http://prometheus:9090
export DOCKER_HOST=unix:///var/run/docker.sock
export COMPOSE_PROJECT_NAME=baileys-bridge

mkdir -p ops/logs sessions/api sessions/worker

echo "🚀 Codex evolution mode starting..."
docker compose up -d --build
# ./codex run --self-heal --cluster $CODEX_SWARM_SIZE
