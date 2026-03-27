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

run_compose_quiet() {
  local log_file="$1"
  shift
  if ! docker compose -f "$compose_file" --env-file "$compose_env" "$@" >"$log_file" 2>&1; then
    echo "Compose command failed: docker compose $*" >&2
    cat "$log_file" >&2
    return 1
  fi
}

wait_for_http_code() {
  local url="$1"
  local expected="$2"
  local timeout="$3"
  local started
  local code=""

  started="$(date +%s)"
  while true; do
    code="$(curl -sS -o /tmp/dp-validate-body.json -w '%{http_code}' "$url" || true)"
    if [[ "$code" == "$expected" ]]; then
      return 0
    fi
    if (( "$(date +%s)" - started >= timeout )); then
      echo "Timed out waiting for $url to return HTTP $expected; last HTTP $code" >&2
      if [[ -f /tmp/dp-validate-body.json ]]; then
        cat /tmp/dp-validate-body.json >&2
      fi
      return 1
    fi
    sleep 2
  done
}

cleanup() {
  timeout 180s docker compose -f "$compose_file" --env-file "$compose_env" down --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"; cleanup' EXIT

echo "Check 1/5: Compose file renders"
run_compose_quiet "$tmp_dir/config.log" config >/dev/null

echo "Check 2/5: Previous stack is cleared"
timeout 180s docker compose -f "$compose_file" --env-file "$compose_env" down --remove-orphans >/dev/null 2>&1 || true

echo "Check 3/5: Stack start is requested"
if ! timeout 180s docker compose -f "$compose_file" --env-file "$compose_env" up -d artifact-server postgres dp-storage-jsondb-service hex-core-service >"$tmp_dir/up.log" 2>&1; then
  echo "Compose did not exit cleanly during stack start. Checking service availability instead."
fi

echo "Check 4/5: Core health and readiness"
wait_for_http_code "http://127.0.0.1:8080/admin/ready" "200" "60"
wait_for_http_code "http://127.0.0.1:8080/admin/version" "200" "60"

echo "Check 5/5: Backend health"
wait_for_http_code "http://127.0.0.1:8081/health" "200" "60"

echo "Validation passed"
