#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="$repo_root/compose/docker-compose.yml"
compose_env="$repo_root/compose/.env"

ensure_env() {
  if [[ ! -f "$compose_env" ]]; then
    cp "$repo_root/compose/.env.example" "$compose_env"
  fi
}

compose_cmd() {
  docker compose -f "$compose_file" --env-file "$compose_env" "$@"
}

case "${1:-}" in
  up)
    ensure_env
    compose_cmd up -d artifact-server postgres dp-storage-jsondb-service hex-core-service
    ;;
  demo)
    ensure_env
    compose_cmd up -d artifact-server postgres dp-storage-jsondb-service hex-core-service
    compose_cmd run --rm demo-runner
    ;;
  down)
    ensure_env
    compose_cmd down --remove-orphans
    ;;
  clean)
    ensure_env
    compose_cmd down --remove-orphans --volumes
    ;;
  validate)
    ensure_env
    "$repo_root/scripts/validate-local-compose.sh"
    ;;
  *)
    echo "Usage: $0 {up|demo|down|clean|validate}" >&2
    exit 1
    ;;
esac
