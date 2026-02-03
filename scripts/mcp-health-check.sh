#!/bin/bash
#
# MCP Health Check - Entry Point
#
# Standalone diagnostic tool for the Om Apex MCP Server.
# Use this when the MCP server is not starting or behaving unexpectedly.
#
# Usage:
#   ./scripts/mcp-health-check.sh
#   ./scripts/mcp-health-check.sh --verbose
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Om Apex MCP Server Health Check"
echo "========================================"
echo ""

# Check for Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[FAIL] Python not found in PATH"
    echo "       Please install Python 3.10 or later"
    exit 1
fi

# Get Python version
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "[FAIL] Python $PY_VERSION detected - requires 3.10+"
    echo "       Update Python or set PATH to correct version"
    exit 1
fi

echo "[PASS] Python $PY_VERSION"

# Run the detailed Python health check
cd "$MCP_ROOT"
$PYTHON "$SCRIPT_DIR/mcp-health-check.py" "$@"
