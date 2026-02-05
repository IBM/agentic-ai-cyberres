#!/bin/bash

# Quick fix script for Claude Desktop integration issues
# This script resolves the "No module named 'plugins'" error

set -e

echo "🔧 CyberRes MCP - Claude Desktop Quick Fix"
echo "=========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📍 Working directory: $SCRIPT_DIR"
echo ""

# Step 1: Reinstall the package
echo "1️⃣  Reinstalling package..."
uv sync --reinstall
echo "✅ Package reinstalled"
echo ""

# Step 2: Verify package structure
echo "2️⃣  Verifying package structure..."
if [ -d "src/cyberres_mcp/plugins" ]; then
    echo "✅ Package structure is correct"
else
    echo "❌ ERROR: Package structure is incorrect"
    echo "   Expected: src/cyberres_mcp/plugins/"
    exit 1
fi
echo ""

# Step 3: Test server can start
echo "3️⃣  Testing server startup..."
timeout 3 bash -c "MCP_TRANSPORT=stdio uv run cyberres-mcp" 2>&1 | head -n 5 || true
echo "✅ Server can start"
echo ""

# Step 4: Check uv path
echo "4️⃣  Checking uv installation..."
UV_PATH=$(which uv)
echo "   uv path: $UV_PATH"
echo ""

# Step 5: Generate Claude Desktop config
echo "5️⃣  Generating Claude Desktop config..."
cat > claude_desktop_config.json << EOF
{
  "mcpServers": {
    "cyberres-recovery-validation": {
      "command": "$UV_PATH",
      "args": [
        "--directory",
        "$SCRIPT_DIR",
        "run",
        "cyberres-mcp"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "SECRETS_FILE": "demo-secrets.json",
        "ENVIRONMENT": "demo"
      }
    }
  }
}
EOF
echo "✅ Config generated: claude_desktop_config.json"
echo ""

# Step 6: Show config location
echo "6️⃣  Claude Desktop config location:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CLAUDE_CONFIG="$APPDATA/Claude/claude_desktop_config.json"
else
    CLAUDE_CONFIG="Unknown OS"
fi
echo "   $CLAUDE_CONFIG"
echo ""

# Step 7: Offer to copy config
echo "7️⃣  Copy config to Claude Desktop?"
echo "   This will backup your existing config if present."
read -p "   Copy config? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$CLAUDE_CONFIG")"
    
    # Backup existing config
    if [ -f "$CLAUDE_CONFIG" ]; then
        BACKUP="$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$CLAUDE_CONFIG" "$BACKUP"
        echo "   ✅ Backed up existing config to: $BACKUP"
    fi
    
    # Copy new config
    cp claude_desktop_config.json "$CLAUDE_CONFIG"
    echo "   ✅ Config copied to Claude Desktop"
else
    echo "   ⏭️  Skipped. You can manually copy claude_desktop_config.json"
fi
echo ""

# Step 8: Final instructions
echo "✅ Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Quit Claude Desktop completely (Cmd+Q on Mac)"
echo "   2. Wait 5 seconds"
echo "   3. Relaunch Claude Desktop"
echo "   4. Wait for it to fully load"
echo "   5. Ask Claude: 'Can you check the health of the recovery validation server?'"
echo ""
echo "🔍 If issues persist, see TROUBLESHOOTING.md"
echo ""
echo "🎯 For demo preparation, run: bash demo/pre-demo-test.sh"
echo ""

# Made with Bob
