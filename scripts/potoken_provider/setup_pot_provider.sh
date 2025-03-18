#!/bin/bash
set -e  # Exit on error

SCRIPTS_DIR="scripts/potoken_provider"
TARGET_DIR="$SCRIPTS_DIR/bgutil-provider"
SERVER_DIR="$TARGET_DIR/server"
GEN_SCRIPT="$SERVER_DIR/build/generate_once.js"

# Ensure the server directory exists
if [ ! -d "$SERVER_DIR" ]; then
    echo "Error: PO Token provider server directory is missing! Please run update_pot_provider.sh first."
    exit 1
fi

# Move into the server directory
cd "$SERVER_DIR" || exit 1

# Check if dependencies need installation
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    yarn install --frozen-lockfile
else
    echo "Dependencies already installed. Skipping yarn install."
fi

# Check if build directory exists and if transpiling is needed
if [ ! -d "build" ] || [ "$SERVER_DIR/src" -nt "$GEN_SCRIPT" ]; then
    echo "Build directory missing or outdated. Running transpilation..."
    npx tsc
else
    echo "Build directory is up to date. Skipping transpilation."
fi

# Ensure the script exists after transpilation
if [ ! -f "$GEN_SCRIPT" ]; then
    echo "Error: PO Token script not found after attempting transpilation."
    exit 1
fi


# Confirm success
echo "PO Token provider script is ready for use."
