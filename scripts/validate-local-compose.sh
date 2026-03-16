#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/compose/docker-compose.yml"
compose_env="$repo_root/compose/.env"

if [[ ! -f "$compose_env" ]]; then
  cp "$repo_root/compose/.env.example" "$compose_env"
fi

compose_cmd() {
  docker compose -f "$compose_file" --env-file "$compose_env" "$@"
}

cleanup() {
  compose_cmd down --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "Validating Docker Compose rendering"
compose_cmd config >/dev/null

echo "Starting local stack for smoke test"
compose_cmd up -d artifact-server postgres dp-storage-jsondb-service hex-core-service >/dev/null

echo "Running HTTP smoke checks through the Docker-only demo runner"
compose_cmd run --rm --entrypoint sh demo-runner -lc '
  set -e
  for url in \
    http://hex-core-service:8080/admin/health \
    http://hex-core-service:8080/admin/ready \
    http://dp-storage-jsondb-service:8080/health \
    http://dp-storage-jsondb-service:8080/ready
  do
    code="$(curl -sS -o /tmp/resp -w "%{http_code}" "$url")"
    if [ "$code" != "200" ]; then
      echo "Smoke check failed for $url: HTTP $code" >&2
      cat /tmp/resp >&2 || true
      exit 1
    fi
  done
'

echo "Compose validation completed"
