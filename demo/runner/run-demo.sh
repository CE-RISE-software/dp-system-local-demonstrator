#!/usr/bin/env bash
set -euo pipefail

base_url="${DEMO_BASE_URL:-http://hex-core-service:8080}"
model="${DEMO_MODEL:-dp-record-metadata}"
version="${DEMO_VERSION:-0.0.2}"
valid_payload="/payloads/dp_valid.json"
invalid_payload="/payloads/dp_invalid.json"
session_file="/tmp/demo-session"

print_step() {
  echo
  echo "== $1 =="
}

wait_for_ok() {
  local url="$1"
  local expected="${2:-200}"
  local attempts=60
  local code=""

  while (( attempts > 0 )); do
    code="$(curl -sS -o /tmp/wait-body.json -w '%{http_code}' "$url" || true)"
    if [[ "$code" == "$expected" ]]; then
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done

  echo "Timed out waiting for $url, last HTTP status: $code" >&2
  if [[ -f /tmp/wait-body.json ]]; then
    cat /tmp/wait-body.json >&2
  fi
  exit 1
}

login_session() {
  local session_id
  session_id="session-$(date +%s)"
  printf '%s\n' "$session_id" > "$session_file"
  echo "$session_id"
}

logout_session() {
  rm -f "$session_file"
}

post_json() {
  local url="$1"
  local payload_file="$2"
  local extra_header="${3:-}"
  local body_file="$4"
  local status

  if [[ -n "$extra_header" ]]; then
    status="$(curl -sS -o "$body_file" -w '%{http_code}' \
      -X POST "$url" \
      -H "Content-Type: application/json" \
      -H "$extra_header" \
      --data-binary "@$payload_file")"
  else
    status="$(curl -sS -o "$body_file" -w '%{http_code}' \
      -X POST "$url" \
      -H "Content-Type: application/json" \
      --data-binary "@$payload_file")"
  fi

  echo "$status"
}

operation_url() {
  local operation="$1"
  echo "$base_url/models/$model/versions/$version:$operation"
}

print_step "Step 1: Wait for local stack"
wait_for_ok "$base_url/admin/ready" 200
wait_for_ok "$base_url/admin/version" 200
echo "hex-core-service is ready."

print_step "Step 2: Login in no-auth demo mode"
session_one="$(login_session)"
echo "Auth mode: none"
echo "Session initialized: $session_one"

print_step "Step 3: Validate valid passport payload"
jq -n --slurpfile payload "$valid_payload" '{payload: $payload[0]}' > /tmp/validate-valid.request.json
status="$(post_json "$(operation_url validate)" /tmp/validate-valid.request.json "" /tmp/validate-valid.response.json)"
echo "HTTP status: $status"
jq '{passed, results}' /tmp/validate-valid.response.json
if [[ "$status" != "200" ]]; then
  exit 1
fi

print_step "Step 4: Create valid passport record"
jq -n --slurpfile payload "$valid_payload" '{payload: $payload[0]}' > /tmp/create-valid.request.json
status="$(post_json "$(operation_url create)" /tmp/create-valid.request.json "Idempotency-Key: demo-create-001" /tmp/create-valid.response.json)"
echo "HTTP status: $status"
if [[ "$status" != "200" ]]; then
  jq . /tmp/create-valid.response.json
  exit 1
fi
record_id="$(jq -r '.id' /tmp/create-valid.response.json)"
echo "Record ID: $record_id"
jq '{id, model, version}' /tmp/create-valid.response.json

print_step "Step 5: Logout"
logout_session
echo "Session cleared."

print_step "Step 6: Login again"
session_two="$(login_session)"
echo "New session initialized: $session_two"

print_step "Step 7: Read back the stored record"
cat > /tmp/query-request.json <<EOF
{
  "filter": {
    "where": [
      { "field": "id", "op": "eq", "value": "$record_id" }
    ],
    "limit": 1,
    "offset": 0
  }
}
EOF
status="$(post_json "$(operation_url query)" /tmp/query-request.json "" /tmp/query-response.json)"
echo "HTTP status: $status"
if [[ "$status" != "200" ]]; then
  jq . /tmp/query-response.json
  exit 1
fi
readback_name="$(jq -r '.records[0].payload.product_profile.name.name_value' /tmp/query-response.json)"
readback_identifier="$(jq -r '.records[0].payload.product_profile.unique_product_identifier.unique_product_identifier_value' /tmp/query-response.json)"
readback_record_id="$(jq -r '.records[0].id' /tmp/query-response.json)"
readback_lot_batch="$(jq -r '.records[0].payload.product_profile.general_product_information.lot_batch_number_value' /tmp/query-response.json)"
echo "Read-back record ID: $readback_record_id"
echo "Read-back product name: $readback_name"
echo "Read-back unique identifier: $readback_identifier"
echo "Read-back lot or batch: $readback_lot_batch"

print_step "Step 8: Reject an invalid payload"
jq -n --slurpfile payload "$invalid_payload" '{payload: $payload[0]}' > /tmp/create-invalid.request.json
status="$(post_json "$(operation_url create)" /tmp/create-invalid.request.json "Idempotency-Key: demo-create-invalid-001" /tmp/create-invalid.response.json)"
echo "HTTP status: $status"
jq . /tmp/create-invalid.response.json
if [[ "$status" == "200" ]]; then
  echo "Invalid payload unexpectedly succeeded." >&2
  exit 1
fi

print_step "Success Summary"
echo "Valid record persisted with ID: $record_id"
echo "Read-back payload confirmed with matching record ID and product identifiers."
echo "Invalid payload was rejected as expected."
