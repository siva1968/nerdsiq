#!/bin/bash
# Build Custom Onyx Web Container with Logout Fix
# This script automates the process of building a custom Onyx web image
# with the logout bug fixes applied.

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONYX_VERSION="${ONYX_VERSION:-v2.11.0}"
IMAGE_NAME="${IMAGE_NAME:-onyx-web-custom:logout-fix}"

echo "=========================================="
echo "Building Custom Onyx Web Container"
echo "=========================================="
echo "Version: $ONYX_VERSION"
echo "Image: $IMAGE_NAME"
echo ""

# Step 1: Clone Onyx source if not exists
ONYX_SOURCE_DIR="$SCRIPT_DIR/../onyx-source"
if [ ! -d "$ONYX_SOURCE_DIR" ]; then
    echo "[1/5] Cloning Onyx source code..."
    cd "$SCRIPT_DIR/.."
    git clone --depth 1 --branch "$ONYX_VERSION" https://github.com/onyx-dot-app/onyx.git onyx-source
    echo "✓ Source code cloned"
else
    echo "[1/5] Onyx source already exists, skipping clone"
fi

# Step 2: Apply patches
echo ""
echo "[2/5] Applying logout fix patches..."

cd "$ONYX_SOURCE_DIR"

# Check if patches already applied
if grep -q "Delete cookies on logout (fixed for self-hosted instances)" web/src/app/auth/logout/route.ts; then
    echo "✓ Patches already applied"
else
    echo "  - Applying route.ts patch..."
    if [ -f "$SCRIPT_DIR/patches/logout-route-fix.patch" ]; then
        git apply "$SCRIPT_DIR/patches/logout-route-fix.patch"
        echo "  ✓ route.ts patched"
    else
        echo "  ⚠ Patch file not found, skipping"
    fi

    echo "  - Applying userSS.ts patch..."
    if [ -f "$SCRIPT_DIR/patches/userss-header-filter-fix.patch" ]; then
        git apply "$SCRIPT_DIR/patches/userss-header-filter-fix.patch"
        echo "  ✓ userSS.ts patched"
    else
        echo "  ⚠ Patch file not found, skipping"
    fi
fi

# Step 3: Build Docker image
echo ""
echo "[3/5] Building Docker image..."
cd "$ONYX_SOURCE_DIR/web"
sudo docker build -t "$IMAGE_NAME" .

if [ $? -eq 0 ]; then
    echo "✓ Image built successfully"
else
    echo "✗ Build failed"
    exit 1
fi

# Step 4: Verify image
echo ""
echo "[4/5] Verifying image..."
if sudo docker images | grep -q "onyx-web-custom"; then
    echo "✓ Image exists in local registry"
    sudo docker images | grep "onyx-web-custom"
else
    echo "✗ Image not found"
    exit 1
fi

# Step 5: Update docker-compose (optional)
echo ""
echo "[5/5] Docker image ready!"
echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update docker-compose-onyx.yml to use image: $IMAGE_NAME"
echo "2. Run: cd $SCRIPT_DIR && sudo docker compose -f docker-compose-onyx.yml up -d --force-recreate web_server"
echo ""
echo "Or run this command to update automatically:"
echo "cd $SCRIPT_DIR && sudo docker compose -f docker-compose-onyx.yml up -d --force-recreate web_server"
echo ""
