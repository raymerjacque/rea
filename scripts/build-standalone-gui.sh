#!/usr/bin/env bash
# ==============================================================================
# Build Standalone Single-File Linux Executable for REA Desktop GUI
# Compiles PyQt5 GUI and bundles the REA engine into a single ELF executable.
# When launched, it opens the REA GUI immediately.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================================================="
echo "⚡ Building REA Single-File Standalone Executable (GUI + Engine)"
echo "=============================================================================="

# 1. Ensure Node and Bun are available
if [ -f "$HOME/.local/opt/node/bin/node" ]; then
    export PATH="$HOME/.local/opt/node/bin:$PATH"
fi
if [ -f "$HOME/.bun/bin/bun" ]; then
    export PATH="$HOME/.bun/bin:$PATH"
fi

# 2. Check/compile rea.bin if missing
if [ ! -f "$SCRIPT_DIR/rea.bin" ]; then
    echo "[1/3] Compiling REA TypeScript engine into rea.bin..."
    bash "$SCRIPT_DIR/scripts/compile-linux-binary.sh"
else
    echo "[1/3] Using existing REA engine binary ($SCRIPT_DIR/rea.bin)..."
fi

# 3. Ensure icon exists
ICON_SRC="/home/jacque/AI-center/ai-icon.png"
if [ ! -f "$ICON_SRC" ]; then
    ICON_SRC="$SCRIPT_DIR/ai-icon.png"
    touch "$ICON_SRC"
fi

OUTPUT_DIR="$SCRIPT_DIR/dist"
mkdir -p "$OUTPUT_DIR"

echo "[2/3] Compiling with Nuitka (translating Python & PyQt5 to native C/ELF)..."
python3 -m nuitka \
    --mode=onefile \
    --enable-plugin=pyqt5 \
    --include-data-file="$SCRIPT_DIR/rea.bin=rea.bin" \
    --include-data-file="$ICON_SRC=ai-icon.png" \
    --python-flag=no_docstrings \
    --assume-yes-for-downloads \
    --remove-output \
    --jobs=8 \
    --nofollow-import-to=*.tests,*.test,unittest,pytest,doctest \
    --output-dir="$OUTPUT_DIR" \
    --output-filename=rea-app \
    "$SCRIPT_DIR/rea_gui.py"

# Clean up transient build artifacts
rm -rf "$OUTPUT_DIR/rea_gui.dist" "$OUTPUT_DIR/rea_gui.onefile-build" "$OUTPUT_DIR/rea_gui.build" 2>/dev/null || true

chmod +x "$OUTPUT_DIR/rea-app"
cp -f "$OUTPUT_DIR/rea-app" "$SCRIPT_DIR/rea-app"

echo "=============================================================================="
echo "✅ Build Complete! Single-file standalone executable created:"
echo "   - $OUTPUT_DIR/rea-app"
echo "   - $SCRIPT_DIR/rea-app"
echo ""
ls -lh "$SCRIPT_DIR/rea-app"
echo "=============================================================================="
echo "When executed, this single file directly launches the REA GUI."
echo "=============================================================================="
