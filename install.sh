#!/usr/bin/env bash
set -e

APP_DIR="$HOME/.local/share/nvidia-ai-monitor"
BIN_DIR="$HOME/.local/bin"

echo "Installing NVIDIA AI & Compute Monitor CLI command..."
mkdir -p "$APP_DIR" "$BIN_DIR"

cp ai-monitor-gui.py "$APP_DIR/ai-monitor-gui.py"
chmod +x "$APP_DIR/ai-monitor-gui.py"
ln -sf "$APP_DIR/ai-monitor-gui.py" "$BIN_DIR/ai-monitor"

echo "Installation complete!"
echo "Launch anytime from your terminal with: ai-monitor"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Note: Add ~/.local/bin to your PATH if 'ai-monitor' is not immediately recognized:"
  echo '  echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc && source ~/.bashrc'
fi
