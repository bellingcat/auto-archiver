#!/bin/bash
set -e  # Exit on error

SCRIPTS_DIR="scripts/potoken_provider"
TARGET_DIR="$SCRIPTS_DIR/bgutil-provider"
BGUTIL_REPO="https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git"
BGUTIL_TEMP_DIR="$SCRIPTS_DIR/bgutil-temp"


# Clone fresh copy into temporary directory
git clone --depth 1 "$REPO_URL" "$TMP_DIR"

# Ensure the target directory exists
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy the entire server directory
echo "Copying /server/ directory..."
cp -r "$BGUTIL_TEMP_DIR/server" "$TARGET_DIR/"

# Clean up: remove the cloned repository
echo "Cleaning up temporary files..."
rm -rf "$BGUTIL_TEMP_DIR"

# Confirm success
echo "PO Token provider script is ready in: $TARGET_DIR/server"
echo "Commit and push changes to include it in version control."
