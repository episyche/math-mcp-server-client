#!/usr/bin/env python3
"""
Direct test of YouTube MCP server functionality
"""

import json
import subprocess
import sys
import time
import threading

def test_youtube_server_directly():
    """Test YouTube server by calling it directly."""
    
    print("🚀 Testing YouTube MCP Server directly...")
    
    # Start the YouTube server
    process = subprocess.Popen(
        [sys.executable, "youtube/youtube_mcp_minimal.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Give the server a moment to start
        time.sleep(2)
        
        # Test the server by sending a simple request
        print("📡 Sending test request to YouTube server...")
        
        # First, initialize the session
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send initialization request
        init_json = json.dumps(init_request) + "\n"
        process.stdin.write(init_json)
        process.stdin.flush()
        
        # Read initialization response
        init_response = process.stdout.readline()
        print("🔧 Initialization response:")
        print(init_response)
        
        # Now create a tool call request
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_videos",
                "arguments": {
                    "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0"
                }
            }
        }
        
        # Send the request
        request_json = json.dumps(request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("✅ Server responded successfully!")
            print("📋 Response:")
            print(json.dumps(response, indent=2))
        else:
            print("❌ No response from server")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        process.terminate()
        process.wait()
        print("🧹 Cleaned up server process")

if __name__ == "__main__":
    test_youtube_server_directly()
