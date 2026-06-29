#!/bin/sh
set -eu

MATRIX_URL="http://127.0.0.1:${TUWUNEL_PORT:-6167}"
OUTPUT_FILE="/output/tuwunel-backup.env"

ADMIN_USER="${MATRIX_INIT_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${MATRIX_INIT_ADMIN_PASSWORD}"
REGISTRATION_TOKEN="${TUWUNEL_REGISTRATION_TOKEN}"
SERVER_NAME="${TUWUNEL_SERVER_NAME}"

# Wait for Tuwunel to accept connections
echo "Waiting for Tuwunel at ${MATRIX_URL}..."
TIMEOUT=120; ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    if curl -sf "${MATRIX_URL}/_matrix/client/versions" > /dev/null 2>&1; then
        echo "Tuwunel is ready."
        break
    fi
    sleep 5; ELAPSED=$((ELAPSED + 5))
done
[ "$ELAPSED" -lt "$TIMEOUT" ] || { echo "ERROR: Tuwunel not ready after ${TIMEOUT}s." >&2; exit 1; }

# Try login first in case the admin user already exists (e.g. partial previous run)
echo "Attempting login as ${ADMIN_USER}..."
LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"m.login.password\",\"identifier\":{\"type\":\"m.id.user\",\"user\":\"${ADMIN_USER}\"},\"password\":\"${ADMIN_PASSWORD}\"}" \
    "${MATRIX_URL}/_matrix/client/v3/login")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Login failed; registering ${ADMIN_USER}..."

    # Step 1: get the UIAA session ID (server returns 401 with session in body)
    UIAA_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
        "${MATRIX_URL}/_matrix/client/v3/register?kind=user")

    SESSION=$(echo "$UIAA_RESPONSE" | jq -r '.session // empty')
    [ -n "$SESSION" ] || { echo "ERROR: Could not obtain UIAA session." >&2; exit 1; }

    # Step 2: register using the registration token
    REGISTER_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASSWORD}\",\"auth\":{\"type\":\"m.login.registration_token\",\"token\":\"${REGISTRATION_TOKEN}\",\"session\":\"${SESSION}\"}}" \
        "${MATRIX_URL}/_matrix/client/v3/register?kind=user")

    ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token // empty')
    [ -n "$ACCESS_TOKEN" ] || { echo "ERROR: Registration failed: $(echo "$REGISTER_RESPONSE" | jq -r '.error // .')" >&2; exit 1; }
    echo "User ${ADMIN_USER} registered and granted admin."
else
    echo "Logged in as ${ADMIN_USER}."
fi

# Find the admin room: the one that contains the server bot (@tuwunel:<server>)
echo "Looking for admin room..."
JOINED_ROOMS=$(curl -sf \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${MATRIX_URL}/_matrix/client/v3/joined_rooms" | jq -r '.joined_rooms[]')

ADMIN_ROOM_ID=""
for ROOM_ID in $JOINED_ROOMS; do
    MEMBERS=$(curl -sf \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        "${MATRIX_URL}/_matrix/client/v3/rooms/${ROOM_ID}/joined_members" 2>/dev/null || echo '{}')
    # The Tuwunel admin bot is @tuwunel:<server_name>
    if echo "$MEMBERS" | jq -e ".joined | (has(\"@tuwunel:${SERVER_NAME}\") or has(\"@conduit:${SERVER_NAME}\"))" > /dev/null 2>&1; then
        ADMIN_ROOM_ID="$ROOM_ID"
        break
    fi
done

[ -n "$ADMIN_ROOM_ID" ] || { echo "ERROR: Admin room not found. Is the server bot in a room with ${ADMIN_USER}?" >&2; exit 1; }
echo "Admin room: ${ADMIN_ROOM_ID}"

# Write generated credentials to output (picked up by ExecStartPost)
cat > "${OUTPUT_FILE}" << EOF
MATRIX_BACKUP_ACCESS_TOKEN=${ACCESS_TOKEN}
MATRIX_BACKUP_ROOM_ID=${ADMIN_ROOM_ID}
EOF

echo "Initialization complete. Credentials written to ${OUTPUT_FILE}."
