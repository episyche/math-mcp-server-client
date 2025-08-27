# Telegram MCP Server Runner for Windows
# This script runs the unified Telegram MCP server

Write-Host "🚀 Starting Telegram MCP Server..." -ForegroundColor Green

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the telegram directory
Set-Location $scriptDir

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+ and add it to PATH" -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ No .env file found. Please create one with your Telegram credentials:" -ForegroundColor Yellow
    Write-Host "   TELEGRAM_API_ID=your_api_id_here" -ForegroundColor Cyan
    Write-Host "   TELEGRAM_API_HASH=your_api_hash_here" -ForegroundColor Cyan
    Write-Host "   TELEGRAM_PHONE=+1234567890" -ForegroundColor Cyan
    Write-Host "   See README.md for setup instructions" -ForegroundColor Cyan
    exit 1
}

# Check if requirements are installed
Write-Host "🔍 Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import telethon, mcp, fastmcp" 2>$null
    Write-Host "✅ All dependencies are installed" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "📁 Created logs directory" -ForegroundColor Green
}

# Run the MCP server
Write-Host "🚀 Starting Telegram MCP Server..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow

try {
    python telegram_mcp_server.py
} catch {
    Write-Host "❌ Server stopped with error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Write-Host "🛑 Telegram MCP Server stopped" -ForegroundColor Yellow
}
