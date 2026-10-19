#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "⚡ Compiling REA Linux Executable..."
if [ -f "$HOME/.local/opt/node/bin/node" ]; then
    export PATH="$HOME/.local/opt/node/bin:$PATH"
fi
if [ -f "$HOME/.bun/bin/bun" ]; then
    export PATH="$HOME/.bun/bin:$PATH"
fi

echo "1. Compiling TypeScript modules..."
npm run compile

echo "2. Building standalone Linux ELF binary (rea.bin)..."
bun build ./scripts/entry-binary.mjs --compile --outfile rea.bin --external playwright-core --external fsevents --external frida

chmod +x rea.bin

# Write smart rea wrapper script
cat << 'EOF' > rea
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="${SCRIPT_DIR}/rea.bin"
GUI_PATH="${SCRIPT_DIR}/rea_gui.py"

if [ "$1" = "--gui" ]; then
    shift
    exec python3 "${GUI_PATH}" "$@"
fi

if [ "$1" = "--cli" ]; then
    shift
    exec "${BIN_PATH}" "$@"
fi

if [ $# -eq 0 ]; then
    if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
        exec python3 "${GUI_PATH}"
    else
        exec "${BIN_PATH}" --help
    fi
fi

exec "${BIN_PATH}" "$@"
EOF
chmod +x rea

echo "✅ REA Linux Executable & Wrapper successfully ready:"
echo "   - $SCRIPT_DIR/rea.bin (Standalone CLI binary)"
echo "   - $SCRIPT_DIR/rea     (Smart Launcher: GUI on desktop, CLI if args passed)"
"$SCRIPT_DIR/rea.bin" --version
