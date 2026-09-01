#!/usr/bin/env bash
#
# run_instagrapi_server.sh
# Usage:
#   From repo root:   ./scripts/instagrapi_server/run_instagrapi_server.sh
#   Or from script dir: ./run_instagrapi_server.sh
#

set -e

# Step 1: cd to the script's directory (contains Dockerfile and secrets/)
cd "$(dirname "$0")" || exit 1

# Create secrets/ if it doesn't exist
if [[ ! -d "secrets" ]]; then
  echo "Creating secrets/ directory..."
  mkdir secrets
fi
chmod 700 secrets

echo "Enter your Instagram credentials to store in secrets/.env"
read -rp "Instagram Username: " IGUSER
read -rsp "Instagram Password: " IGPASS
echo ""

# Generate a random API key that clients must send in the x-access-key header
API_KEY="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"

cat <<EOF > secrets/.env
INSTAGRAM_USERNAME=$IGUSER
INSTAGRAM_PASSWORD=$IGPASS
INSTAGRAPI_API_KEY=$API_KEY
EOF
chmod 600 secrets/.env
echo "Created secrets/.env with your credentials and a generated API key."

# Build Docker image
IMAGE_NAME="instagrapi-server"
echo "Building Docker image '$IMAGE_NAME'..."
docker build -t "$IMAGE_NAME" .

# Run container
CONTAINER_NAME="ig-instasrv"
echo "Running container '$CONTAINER_NAME'..."
docker run -d \
  --env-file secrets/.env \
  -v "$(pwd)/secrets:/app/secrets" \
  -p 127.0.0.1:8000:8000 \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME"

echo "Done! Instagrapi server is running on http://127.0.0.1:8000 (localhost only)."
echo ""
echo "Configure the auto-archiver instagram_api_extractor with:"
echo "  api_endpoint: http://127.0.0.1:8000"
echo "  access_token: $API_KEY"
echo ""
echo "Use 'docker logs $CONTAINER_NAME' to view logs."
echo "Use 'docker stop $CONTAINER_NAME' and 'docker rm $CONTAINER_NAME' to stop/remove the container."
