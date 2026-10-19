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
cp -f rea.bin rea

echo "✅ REA Linux Executable successfully compiled:"
echo "   - $SCRIPT_DIR/rea.bin"
echo "   - $SCRIPT_DIR/rea"
"$SCRIPT_DIR/rea.bin" --version
