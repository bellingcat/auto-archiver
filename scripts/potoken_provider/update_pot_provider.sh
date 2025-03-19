#!/bin/bash
set -e

SCRIPTS_DIR="scripts/potoken_provider"
TARGET_DIR="$SCRIPTS_DIR/bgutil-provider"
BGUTIL_REPO="https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git"
BGUTIL_TEMP_DIR="$SCRIPTS_DIR/bgutil-temp"

# Clone fresh copy of the POT generation script repo into temporary directory
git clone --depth 1 "$BGUTIL_REPO" "$BGUTIL_TEMP_DIR"

# Ensure the target directory exists, clear for a fresh install
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy only the contents inside /server/ into bgutil-provider,
# as this is the part containing the PO Token generation script
echo "Copy /server/ contents into $TARGET_DIR..."
cp -r "$BGUTIL_TEMP_DIR/server/"* "$TARGET_DIR/"

# Clean up: remove the cloned repository as we only needed the /server/ contents
echo "Cleaning up temporary files..."
rm -rf "$BGUTIL_TEMP_DIR"

echo "PO Token provider script is ready in: $TARGET_DIR/build"
echo "Commit and push changes to include it in version control."
