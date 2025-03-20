#!/usr/bin/env bash

set -e  # Exit on error


UUID=$(LC_ALL=C tr -dc a-z0-9 </dev/urandom | head -c 16) 
PROJECT_NAME="auto-archiver-$UUID"
ACCOUNT_NAME="autoarchiver"
KEY_FILE="service_account-$UUID.json"
DEST_DIR="$1"

echo "====================================================="
echo "🔧 Auto-Archiver Google Services Setup Script"
echo "====================================================="
echo "This script will:"
echo "  1. Install Google Cloud SDK if needed"
echo "  2. Create a Google Cloud project named $PROJECT_NAME"
echo "  3. Create a service account for Auto-Archiver"
echo "  4. Generate a key file for API access"
echo ""
echo "  Tip: Pass a directory path as an argument to this script to move the key file there"
echo "  e.g. ./generate_google_services.sh /path/to/secrets"
echo "====================================================="

# Check and install Google Cloud SDK based on platform
install_gcloud_sdk() {
    if command -v gcloud &> /dev/null; then
        echo "✅ Google Cloud SDK is already installed"
        return 0
    fi

    echo "📦 Installing Google Cloud SDK..."
    
    # Detect OS
    case "$(uname -s)" in
        Darwin*)
            if command -v brew &> /dev/null; then
                echo "🍺 Installing via Homebrew..."
                brew install google-cloud-sdk --cask
            else
                echo "📥 Downloading Google Cloud SDK for macOS..."
                curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-latest-darwin-x86_64.tar.gz
                tar -xf google-cloud-cli-latest-darwin-x86_64.tar.gz
                ./google-cloud-sdk/install.sh --quiet
                rm google-cloud-cli-latest-darwin-x86_64.tar.gz
                echo "🔄 Please restart your terminal and run this script again"
                exit 0
            fi
            ;;
        Linux*)
            echo "📥 Downloading Google Cloud SDK for Linux..."
            curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-latest-linux-x86_64.tar.gz
            tar -xf google-cloud-cli-latest-linux-x86_64.tar.gz
            ./google-cloud-sdk/install.sh --quiet
            rm google-cloud-cli-latest-linux-x86_64.tar.gz
            echo "🔄 Please restart your terminal and run this script again"
            exit 0
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "⚠️ Windows detected. Please follow manual installation instructions at:"
            echo "https://cloud.google.com/sdk/docs/install-sdk"
            exit 1
            ;;
        *)
            echo "⚠️ Unknown operating system. Please follow manual installation instructions at:"
            echo "https://cloud.google.com/sdk/docs/install-sdk"
            exit 1
            ;;
    esac
    
    echo "✅ Google Cloud SDK installed"
}

# Install Google Cloud SDK if needed
install_gcloud_sdk

# Login to Google Cloud
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "✅ Already authenticated with Google Cloud"
else
    echo "🔑 Authenticating with Google Cloud..."
    gcloud auth login
fi

# Create project
echo "🌟 Creating Google Cloud project: $PROJECT_NAME"
gcloud projects create $PROJECT_NAME

# Create service account
echo "👤 Creating service account: $ACCOUNT_NAME"
gcloud iam service-accounts create $ACCOUNT_NAME --project $PROJECT_NAME

# Enable required APIs (uncomment and add APIs as needed)
echo "⬆️ Enabling required Google APIs..."
gcloud services enable sheets.googleapis.com --project $PROJECT_NAME
gcloud services enable drive.googleapis.com --project $PROJECT_NAME

# Get the service account email
echo "📧 Retrieving service account email..."
ACCOUNT_EMAIL=$(gcloud iam service-accounts list --project $PROJECT_NAME --format="value(email)")

# Create and download key
echo "🔑 Generating service account key file: $KEY_FILE"
gcloud iam service-accounts keys create $KEY_FILE --iam-account=$ACCOUNT_EMAIL

# move the file to TARGET_DIR if provided
if [[ -n "$DEST_DIR" ]]; then
    # Expand `~` if used
    DEST_DIR=$(eval echo "$DEST_DIR")

    # Ensure the directory exists
    if [[ ! -d "$DEST_DIR" ]]; then
        mkdir -p "$DEST_DIR"
    fi

    DEST_PATH="$DEST_DIR/$KEY_FILE"
    echo "🚚 Moving key file to: $DEST_PATH"
    mv "$KEY_FILE" "$DEST_PATH"
    KEY_FILE="$DEST_PATH"
fi

echo "====================================================="
echo "✅ SETUP COMPLETE!"
echo "====================================================="
echo "📝 Important Information:"
echo "  • Project Name: $PROJECT_NAME"
echo "  • Service Account: $ACCOUNT_EMAIL"
echo "  • Key File: $KEY_FILE"
echo ""
echo "📋 Next Steps:"
echo "  1. Share any Google Sheets with this email address:"
echo "     $ACCOUNT_EMAIL"
echo "  2. Move $KEY_FILE to your auto-archiver secrets directory"
echo "  3. Update your auto-archiver config to use this key file (if needed)"
echo "====================================================="