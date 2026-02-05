#!/bin/bash

#
# Copyright contributors to the agentic-ai-cyberres project
#

# Pre-Demo Test Script for CyberRes MCP Server
# This script verifies that the MCP server is ready for demo

set -e

echo "=========================================="
echo "CyberRes MCP Server - Pre-Demo Test"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Function to print test result
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

# Function to print warning
test_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

echo "1. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo "$PYTHON_VERSION" | cut -d'.' -f1) -ge 3 ]] && [[ $(echo "$PYTHON_VERSION" | cut -d'.' -f2) -ge 13 ]]; then
        test_result 0 "Python $PYTHON_VERSION installed (>= 3.13 required)"
    else
        test_result 1 "Python $PYTHON_VERSION found, but 3.13+ required"
    fi
else
    test_result 1 "Python 3 not found"
fi
echo ""

echo "2. Checking uv CLI..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version | cut -d' ' -f2)
    test_result 0 "uv $UV_VERSION installed"
else
    test_result 1 "uv CLI not found (install with: pip install uv)"
fi
echo ""

echo "3. Checking Node.js and npm..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    test_result 0 "Node.js $NODE_VERSION installed"
else
    test_result 1 "Node.js not found (required for MCP inspector)"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    test_result 0 "npm $NPM_VERSION installed"
else
    test_result 1 "npm not found"
fi
echo ""

echo "4. Checking project files..."
if [ -f "server.py" ]; then
    test_result 0 "server.py found"
else
    test_result 1 "server.py not found (are you in the cyberres-mcp directory?)"
fi

if [ -f "pyproject.toml" ]; then
    test_result 0 "pyproject.toml found"
else
    test_result 1 "pyproject.toml not found"
fi

if [ -f ".env.example" ]; then
    test_result 0 ".env.example found"
else
    test_warning ".env.example not found"
fi

if [ -f ".env" ]; then
    test_result 0 ".env configuration file exists"
else
    test_warning ".env not found (copy from .env.example)"
fi

if [ -f "secrets.json" ]; then
    test_result 0 "secrets.json exists"
else
    test_warning "secrets.json not found (copy from secrets.example.json and configure)"
fi
echo ""

echo "5. Checking demo files..."
if [ -f "demo/DEMO_SCRIPT.md" ]; then
    test_result 0 "Demo script found"
else
    test_warning "demo/DEMO_SCRIPT.md not found"
fi

if [ -f "demo/example-requests.json" ]; then
    test_result 0 "Example requests found"
else
    test_warning "demo/example-requests.json not found"
fi

if [ -f "demo/tool-examples.md" ]; then
    test_result 0 "Tool examples documentation found"
else
    test_warning "demo/tool-examples.md not found"
fi
echo ""

echo "6. Checking plugin files..."
for plugin in net.py vms_validator.py oracle_db.py mongo_db.py utils.py error_codes.py; do
    if [ -f "plugins/$plugin" ]; then
        test_result 0 "Plugin $plugin found"
    else
        test_result 1 "Plugin $plugin not found"
    fi
done
echo ""

echo "7. Checking resource files..."
for resource in vm-core.json db-oracle.json db-mongo.json; do
    if [ -f "resources/acceptance/$resource" ]; then
        test_result 0 "Resource $resource found"
    else
        test_result 1 "Resource $resource not found"
    fi
done
echo ""

echo "8. Checking prompt files..."
for prompt in planner.md evaluator.md summarizer.md; do
    if [ -f "prompts/$prompt" ]; then
        test_result 0 "Prompt $prompt found"
    else
        test_result 1 "Prompt $prompt not found"
    fi
done
echo ""

echo "9. Checking port availability..."
if command -v lsof &> /dev/null; then
    if lsof -i :8000 &> /dev/null; then
        test_warning "Port 8000 is already in use (server may be running or use different port)"
    else
        test_result 0 "Port 8000 is available"
    fi
else
    test_warning "lsof not available, cannot check port 8000"
fi

if command -v lsof &> /dev/null; then
    if lsof -i :6274 &> /dev/null; then
        test_warning "Port 6274 is already in use (MCP inspector may be running)"
    else
        test_result 0 "Port 6274 is available (for MCP inspector)"
    fi
fi
echo ""

echo "10. Testing server startup (dry run)..."
if command -v uv &> /dev/null && [ -f "server.py" ]; then
    # Try to import the server module to check for syntax errors
    if python3 -c "import sys; sys.path.insert(0, '.'); import server" 2>/dev/null; then
        test_result 0 "Server module imports successfully"
    else
        test_result 1 "Server module has import errors"
    fi
else
    test_warning "Cannot test server startup (uv or server.py missing)"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start the server: uv run cyberres-mcp"
    echo "2. Start MCP inspector: npx @modelcontextprotocol/inspector"
    echo "3. Connect inspector to: http://localhost:8000/mcp"
    echo "4. Review demo/DEMO_SCRIPT.md for demo flow"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please fix the issues above.${NC}"
    echo ""
    exit 1
fi

# Made with Bob
