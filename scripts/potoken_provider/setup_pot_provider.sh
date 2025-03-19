#!/bin/bash
set -e

SCRIPTS_DIR="scripts/potoken_provider"
TARGET_DIR="$SCRIPTS_DIR/bgutil-provider"
GEN_SCRIPT="$TARGET_DIR/build/generate_once.js"

# Ensure the server directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: PO Token provider server directory is missing! Please run scripts/update_pot_provider.sh first."
    exit 1
fi

cd "$TARGET_DIR" || exit 1

# Check if dependencies need installation
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    yarn install --frozen-lockfile
else
    echo "Dependencies already installed. Skipping yarn install."
fi

# Check if build directory exists and if transpiling is needed
if [ ! -d "build" ]; then
    echo "Build directory missing or outdated. Running transpilation..."
    npx tsc
else
    echo "Build directory is up to date. Skipping transpilation."
fi


echo "PO Token provider script is ready for use."
