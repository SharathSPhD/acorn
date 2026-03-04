#!/bin/bash
# OAK Tier 3 Installer — auto-detect hardware and start stack
# Usage: bash install.sh
# Detects GPU, downloads compose file, pulls models, starts OAK

set -euo pipefail

echo "🌳 OAK Installer — detecting hardware..."

# Detect GPU
DETECTED_MODE="cpu"
if command -v nvidia-smi &> /dev/null; then
    DETECTED_MODE="dgx"
    echo "✓ NVIDIA GPU detected — using DGX mode (Ollama with GPU)"
elif [[ "$OSTYPE" == "darwin"* ]] && sysctl -a | grep -q "hw.model"; then
    # macOS with Apple Silicon (M4, etc)
    if sysctl hw.machine | grep -q "arm64"; then
        DETECTED_MODE="mini"
        echo "✓ Apple Silicon detected — using Mini mode (Ollama with Metal)"
    fi
fi

MODE="${1:-$DETECTED_MODE}"
echo "📦 Starting OAK in $MODE mode..."

# Clone or use existing repo
if [ ! -d ".git" ]; then
    echo "ℹ️ Cloning OAK repository..."
    git clone https://github.com/SharathSPhD/oak.git
    cd oak
fi

# Run bootstrap
echo "🔨 Building and starting stack..."
bash scripts/bootstrap.sh "$MODE"

echo ""
echo "✅ OAK is ready!"
echo "🌐 Hub: http://localhost:8501"
echo "⚙️  API: http://localhost:8000"
echo "🔀 Proxy: http://localhost:9000"
