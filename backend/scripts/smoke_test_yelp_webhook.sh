#!/usr/bin/env bash
# Smoke test for AI Lead Responder Zapier webhook (prod or staging).
# Usage:
#   bash backend/scripts/smoke_test_yelp_webhook.sh
#   BASE_URL=https://... ZAPIER_WEBHOOK_SECRET=... bash backend/scripts/smoke_test_yelp_webhook.sh

set -euo pipefail

BASE_URL="${BASE_URL:-https://web-production-3b1a9.up.railway.app}"
WEBHOOK_PATH="/api/v1/ai-responder/webhooks/zapier/yelp"
HEALTH_PATH="/health"
LEAD_ID="smoke_${RANDOM}_$(date +%s)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}INFO${NC}: $1"; }

curl_headers=(-sS -H "Content-Type: application/json")
if [[ -n "${ZAPIER_WEBHOOK_SECRET:-}" ]]; then
  curl_headers+=(-H "X-Webhook-Secret: ${ZAPIER_WEBHOOK_SECRET}")
fi

post_webhook() {
  local payload="$1"
  curl "${curl_headers[@]}" -w "\n%{http_code}" -X POST \
    "${BASE_URL}${WEBHOOK_PATH}" \
    -d "$payload"
}

echo "=== AI Lead Responder Smoke Test ==="
echo "BASE_URL=${BASE_URL}"
echo "LEAD_ID=${LEAD_ID}"
echo ""

# Step 0: Health
info "Step 0: GET ${HEALTH_PATH}"
health_body=$(curl -sS "${BASE_URL}${HEALTH_PATH}")
health_code=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${HEALTH_PATH}")
if [[ "$health_code" != "200" ]]; then
  fail "Health returned HTTP ${health_code}: ${health_body}"
fi
if ! echo "$health_body" | grep -q '"status"'; then
  fail "Health body unexpected: ${health_body}"
fi
pass "Health HTTP 200 — ${health_body}"

# Step 1: New lead (first message)
info "Step 1: POST new_lead"
payload1=$(cat <<EOF
{
  "trigger": "new_lead",
  "lead_id": "${LEAD_ID}",
  "consumer_name": "Smoke Test Victor",
  "phone_number": "+13105551234",
  "project_description": "Sliding patio door glass replacement, foggy double pane",
  "zip_code": "90034",
  "service_type": "Door Installation",
  "user_type": "CONSUMER"
}
EOF
)

raw1=$(post_webhook "$payload1")
http1=$(echo "$raw1" | tail -n1)
body1=$(echo "$raw1" | sed '$d')

if [[ "$http1" != "200" ]]; then
  fail "new_lead HTTP ${http1}: ${body1}"
fi
if ! echo "$body1" | grep -q '"reply_text"'; then
  fail "new_lead missing reply_text: ${body1}"
fi
if echo "$body1" | grep -q '"reply_text":""'; then
  fail "new_lead empty reply_text: ${body1}"
fi
pass "new_lead — HTTP 200, reply_text present"
echo "       reply preview: $(echo "$body1" | sed -n 's/.*"reply_text":"\([^"]*\)".*/\1/p' | head -c 120)"
echo ""

# Step 2: Follow-up without trigger (live Zapier pattern)
info "Step 2: POST follow-up (no trigger field)"
payload2=$(cat <<EOF
{
  "lead_id": "${LEAD_ID}",
  "consumer_name": "Smoke Test Victor",
  "message": "What would it cost roughly? I prefer text, no phone calls.",
  "message_id": "smoke_msg_${LEAD_ID}",
  "user_type": "CONSUMER"
}
EOF
)

raw2=$(post_webhook "$payload2")
http2=$(echo "$raw2" | tail -n1)
body2=$(echo "$raw2" | sed '$d')

if [[ "$http2" != "200" ]]; then
  fail "follow-up HTTP ${http2}: ${body2}"
fi
state2=$(echo "$body2" | sed -n 's/.*"state":"\([^"]*\)".*/\1/p')
if [[ "$state2" == "duplicate" ]]; then
  info "follow-up state=duplicate (dedup) — OK if re-run"
elif echo "$body2" | grep -q '"reply_text":""'; then
  fail "follow-up empty reply_text (state=${state2}): ${body2}"
else
  pass "follow-up — HTTP 200, state=${state2}"
  echo "       reply preview: $(echo "$body2" | sed -n 's/.*"reply_text":"\([^"]*\)".*/\1/p' | head -c 120)"
fi
echo ""

# Step 3: BUSINESS message should skip (anti-loop)
info "Step 3: POST BUSINESS user_type (expect skip)"
payload3=$(cat <<EOF
{
  "lead_id": "${LEAD_ID}",
  "message": "This is our business reply",
  "user_type": "BUSINESS"
}
EOF
)

raw3=$(post_webhook "$payload3")
http3=$(echo "$raw3" | tail -n1)
body3=$(echo "$raw3" | sed '$d')

if [[ "$http3" != "200" ]]; then
  fail "BUSINESS skip HTTP ${http3}: ${body3}"
fi
if ! echo "$body3" | grep -q '"state":"skipped"'; then
  fail "BUSINESS should state=skipped: ${body3}"
fi
pass "BUSINESS message skipped (no loop)"
echo ""

# Step 4: Wrong secret (only if secret configured locally)
if [[ -n "${ZAPIER_WEBHOOK_SECRET:-}" ]]; then
  info "Step 4: Wrong secret → expect 401"
  wrong_code=$(curl -sS -o /dev/null -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Secret: wrong-secret" \
    -X POST "${BASE_URL}${WEBHOOK_PATH}" \
    -d '{"lead_id":"x","user_type":"CONSUMER","trigger":"new_lead"}')
  if [[ "$wrong_code" != "401" ]]; then
    fail "Expected 401 for wrong secret, got ${wrong_code}"
  fi
  pass "Wrong secret returns 401"
  echo ""
fi

echo "=== ALL SMOKE CHECKS PASSED ==="
echo "Next: docs/ai-responder/ZAPIER_LIVE_CHECKLIST.md — Zap A + Zap B"
