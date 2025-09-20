#!/bin/bash

# MCP HTTP Server - Curl Streaming Examples
# This script contains curl commands to test the streaming endpoint

BASE_URL="http://localhost:8001"

echo "🚀 MCP HTTP Server Streaming Tests"
echo "=================================="
echo ""

# Test 1: Basic streaming query
echo "📡 Test 1: Basic Streaming Query"
echo "Command:"
echo "curl -N -H \"Accept: text/event-stream\" \\"
echo "  \"${BASE_URL}/query/stream?query=Hello, this is a test query&user_id=test-user-123&max_steps=5\""
echo ""
echo "Executing..."
curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/query/stream?query=Hello, this is a test query&user_id=test-user-123&max_steps=5"

echo ""
echo "=================================="
echo ""

# Test 2: YouTube video listing
echo "📡 Test 2: YouTube Video Listing (Streaming)"
echo "Command:"
echo "curl -N -H \"Accept: text/event-stream\" \\"
echo "  \"${BASE_URL}/query/stream?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0&max_steps=10\""
echo ""
echo "Executing..."
curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/query/stream?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0&max_steps=10"

echo ""
echo "=================================="
echo ""

# Test 3: Gmail unread emails
echo "📡 Test 3: Gmail Unread Emails (Streaming)"
echo "Command:"
echo "curl -N -H \"Accept: text/event-stream\" \\"
echo "  \"${BASE_URL}/query/stream?query=get my unread emails&user_id=your-gmail-user-id&max_steps=8\""
echo ""
echo "Note: Replace 'your-gmail-user-id' with actual Gmail user ID"
echo "Executing (with placeholder user ID)..."
curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/query/stream?query=get my unread emails&user_id=your-gmail-user-id&max_steps=8"

echo ""
echo "=================================="
echo ""

# Test 4: X (Twitter) post creation
echo "📡 Test 4: X (Twitter) Post Creation (Streaming)"
echo "Command:"
echo "curl -N -H \"Accept: text/event-stream\" \\"
echo "  \"${BASE_URL}/query/stream?query=create a post saying 'Hello from MCP HTTP Server!'&user_id=your-x-user-id&max_steps=6\""
echo ""
echo "Note: Replace 'your-x-user-id' with actual X user ID"
echo "Executing (with placeholder user ID)..."
curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/query/stream?query=create a post saying 'Hello from MCP HTTP Server!'&user_id=your-x-user-id&max_steps=6"

echo ""
echo "=================================="
echo ""

# Test 5: Shopify store analytics
echo "📡 Test 5: Shopify Store Analytics (Streaming)"
echo "Command:"
echo "curl -N -H \"Accept: text/event-stream\" \\"
echo "  \"${BASE_URL}/query/stream?query=get my store analytics and statistics&user_id=your-shopify-user-id&max_steps=10\""
echo ""
echo "Note: Replace 'your-shopify-user-id' with actual Shopify user ID"
echo "Executing (with placeholder user ID)..."
curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/query/stream?query=get my store analytics and statistics&user_id=your-shopify-user-id&max_steps=10"

echo ""
echo "=================================="
echo ""

echo "✅ All streaming tests completed!"
echo ""
echo "💡 Tips:"
echo "- Use Ctrl+C to stop any running curl command"
echo "- The streaming response will show real-time updates"
echo "- Replace placeholder user IDs with actual ones for real testing"
echo "- Check server logs for detailed execution information"
