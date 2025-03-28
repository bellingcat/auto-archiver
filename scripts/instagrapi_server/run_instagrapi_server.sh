#!/usr/bin/env bash
#
# run_instagrapi_server.sh
# Usage:
#   From repo root:   ./scripts/instagrapi_server/run_instagrapi_server.sh
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

echo "Enter your Instagram credentials to store in secrets/.env"
read -rp "Instagram Username: " IGUSER
read -rsp "Instagram Password: " IGPASS
echo ""

cat <<EOF > secrets/.env
INSTAGRAM_USERNAME=$IGUSER
INSTAGRAM_PASSWORD=$IGPASS
EOF
echo "Created secrets/.env with your credentials."

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
  -p 8000:8000 \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME"

echo "Done! Instagrapi server is running on port 8000."
echo "Use 'docker logs $CONTAINER_NAME' to view logs."
echo "Use 'docker stop $CONTAINER_NAME' and 'docker rm $CONTAINER_NAME' to stop/remove the container."
