#!/bin/bash

# Telegram MCP Server Runner for Unix/Linux
# This script runs the unified Telegram MCP server

echo "🚀 Starting Telegram MCP Server..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the telegram directory
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python not found. Please install Python 3.8+ and add it to PATH"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "✅ Python found: $($PYTHON_CMD --version)"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️ No .env file found. Please create one with your Telegram credentials:"
    echo "   TELEGRAM_API_ID=your_api_id_here"
    echo "   TELEGRAM_API_HASH=your_api_hash_here"
    echo "   TELEGRAM_PHONE=+1234567890"
    echo "   See README.md for setup instructions"
    exit 1
fi

# Check if requirements are installed
echo "🔍 Checking dependencies..."
if ! $PYTHON_CMD -c "import telethon, mcp, fastmcp" 2>/dev/null; then
    echo "⚠️ Installing dependencies..."
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

echo "✅ All dependencies are installed"

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo "📁 Created logs directory"
fi

# Run the MCP server
echo "🚀 Starting Telegram MCP Server..."
echo "Press Ctrl+C to stop the server"

trap 'echo "🛑 Telegram MCP Server stopped"; exit 0' INT TERM

$PYTHON_CMD telegram_mcp_server.py
