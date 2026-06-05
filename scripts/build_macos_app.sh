#!/bin/bash
set -e

# Change directory to the repository root
CDPATH="" cd -- "$(dirname -- "$0")/.."

echo "=== 1. Building Web Dashboard Frontend ==="
if [ -d "web" ] && [ -f "web/package.json" ]; then
    if command -v npm >/dev/null 2>&1; then
        echo "Found npm, building static frontend dashboard..."
        cd web
        if [ ! -d "node_modules" ]; then
            npm install
        fi
        npm run build
        cd ..
    else
        echo "Warning: 'npm' command not found. Skipping web compilation."
        echo "Using existing assets in src/sgm/interface/web/static/"
    fi
fi

# Ensure static folder exists and has at least index.html
if [ ! -f "src/sgm/interface/web/static/index.html" ]; then
    echo "Error: static web assets (index.html) not found. Compile the frontend first."
    exit 1
fi

echo "=== 2. Creating macOS App Iconset ==="
mkdir -p build/logo.iconset
LOGO_PNG="src/sgm/interface/web/static/logo.png"

if [ -f "$LOGO_PNG" ]; then
    echo "Creating Apple .icns file from $LOGO_PNG..."
    sips -z 16 16     "$LOGO_PNG" --out build/logo.iconset/icon_16x16.png >/dev/null 2>&1
    sips -z 32 32     "$LOGO_PNG" --out build/logo.iconset/icon_16x16@2x.png >/dev/null 2>&1
    sips -z 32 32     "$LOGO_PNG" --out build/logo.iconset/icon_32x32.png >/dev/null 2>&1
    sips -z 64 64     "$LOGO_PNG" --out build/logo.iconset/icon_32x32@2x.png >/dev/null 2>&1
    sips -z 128 128   "$LOGO_PNG" --out build/logo.iconset/icon_128x128.png >/dev/null 2>&1
    sips -z 256 256   "$LOGO_PNG" --out build/logo.iconset/icon_128x128@2x.png >/dev/null 2>&1
    sips -z 256 256   "$LOGO_PNG" --out build/logo.iconset/icon_256x256.png >/dev/null 2>&1
    sips -z 512 512   "$LOGO_PNG" --out build/logo.iconset/icon_256x256@2x.png >/dev/null 2>&1
    sips -z 512 512   "$LOGO_PNG" --out build/logo.iconset/icon_512x512.png >/dev/null 2>&1
    sips -z 1024 1024 "$LOGO_PNG" --out build/logo.iconset/icon_512x512@2x.png >/dev/null 2>&1

    iconutil -c icns build/logo.iconset --o build/logo.icns
    rm -rf build/logo.iconset
    ICON_FLAG="--icon=build/logo.icns"
    echo "App icon compiled successfully!"
else
    echo "Warning: logo.png not found. App bundle will use default fallback icon."
    ICON_FLAG=""
fi

echo "=== 3. Packaging Standalone macOS App ==="
# Determine PyInstaller path (fallback to pyinstaller command if running in virtualenv)
PYINSTALLER_CMD="pyinstaller"
if ! command -v "$PYINSTALLER_CMD" >/dev/null 2>&1; then
    PYINSTALLER_CMD="python3 -m PyInstaller"
fi

# Run PyInstaller using the custom spec file
$PYINSTALLER_CMD --noconfirm --clean Sigma.spec

echo "=== 4. Cleaning intermediate build files ==="
# No spec file to move since we use the version controlled Sigma.spec in root

echo "========================================="
echo "Success! macOS app compiled successfully."
echo "Application bundle path: dist/Sigma.app"
echo "You can double click dist/Sigma.app to launch the app,"
echo "or move it to your /Applications folder."
echo "========================================="
