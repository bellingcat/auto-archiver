#!/bin/bash
set -e

SCRIPTS_DIR="scripts/potoken_provider"
BGUTIL_DIR="$SCRIPTS_DIR/bgutil-ytdlp-pot-provider"
UPDATE=false

# Parse optional flag
if [[ "$1" == "--update" ]]; then
    UPDATE=true
fi

# Clone the repository, or update if it exists
if [ ! -d "$BGUTIL_DIR" ]; then
    echo "Cloning bgutil-ytdlp-pot-provider repository..."
    git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$BGUTIL_DIR"
elif [ "$UPDATE" == true ]; then
    echo "Updating existing bgutil-ytdlp-pot-provider repository..."
    cd "$BGUTIL_DIR" || exit 1
    git pull origin master
fi

# Move into the server directory
cd "$BGUTIL_DIR/server" || exit 1

# Install dependencies and transpile the script
yarn install --frozen-lockfile
npx tsc

# The transpiled POT generation script is now available and will be used automatically by the generic extractor
echo "PO Token provider script is ready: $BGUTIL_DIR/server/build/generate_once.js"
