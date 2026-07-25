#!/bin/bash
# Builds dist/Sigma.app. Run through `make app`.
set -euo pipefail

CDPATH="" cd -- "$(dirname -- "$0")/.."

STATIC="src/sigma/web/static"
LOGO="web/public/logo.png"

echo "==> 1/3  Interfaz"
if command -v npm >/dev/null 2>&1; then
    (cd web && [ -d node_modules ] || npm install)
    (cd web && npm run build)
else
    echo "    npm no encontrado; se usará el build existente."
fi

if [ ! -f "$STATIC/index.html" ]; then
    echo "Error: falta $STATIC/index.html. Compila la interfaz con 'make web'." >&2
    exit 1
fi

echo "==> 2/3  Icono"
if [ -f "$LOGO" ]; then
    rm -rf build/logo.iconset
    mkdir -p build/logo.iconset
    for size in 16 32 128 256 512; do
        sips -z $size $size "$LOGO" \
            --out "build/logo.iconset/icon_${size}x${size}.png" >/dev/null 2>&1
        sips -z $((size * 2)) $((size * 2)) "$LOGO" \
            --out "build/logo.iconset/icon_${size}x${size}@2x.png" >/dev/null 2>&1
    done
    iconutil -c icns build/logo.iconset --output build/logo.icns
    rm -rf build/logo.iconset
else
    echo "    logo.png no encontrado; se usará el icono por defecto."
fi

echo "==> 3/3  Empaquetado"
if command -v pyinstaller >/dev/null 2>&1; then
    pyinstaller --noconfirm --clean Sigma.spec
else
    python3.12 -m PyInstaller --noconfirm --clean Sigma.spec
fi

SIZE=$(du -sh dist/Sigma.app | cut -f1)
echo
echo "Listo: dist/Sigma.app ($SIZE)"
echo "Arrástrala a /Applications para instalarla."
