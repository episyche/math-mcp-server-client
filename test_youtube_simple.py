#!/usr/bin/env python3
"""
Simple test script for YouTube MCP server without mcp_use dependency
"""

import asyncio
import json
import subprocess
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def test_youtube_server():
    """Test the YouTube MCP server directly."""
    
    # Start the YouTube server
    process = subprocess.Popen(
        [sys.executable, "youtube/youtube_mcp_server_simple.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Connect to the server using the correct stdio_client syntax
        async with stdio_client(process.stdin, process.stdout) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                print("✅ Connected to YouTube MCP server successfully!")
                
                # List available tools
                tools = await session.list_tools()
                print(f"📋 Available tools: {[tool.name for tool in tools.tools]}")
                
                # Test list_videos tool
                print("\n🔍 Testing list_videos tool...")
                result = await session.call_tool(
                    "list_videos",
                    {"user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0"}
                )
                
                print("📹 Videos result:")
                print(json.dumps(result.content[0].text, indent=2))
                
                # Test search_videos tool
                print("\n🔍 Testing search_videos tool...")
                result = await session.call_tool(
                    "search_videos",
                    {
                        "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0",
                        "query": "tutorial"
                    }
                )
                
                print("🔍 Search result:")
                print(json.dumps(result.content[0].text, indent=2))
                
                # Test get_channel_analytics tool
                print("\n📊 Testing get_channel_analytics tool...")
                result = await session.call_tool(
                    "get_channel_analytics",
                    {"user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0"}
                )
                
                print("📊 Channel analytics result:")
                print(json.dumps(result.content[0].text, indent=2))
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    asyncio.run(test_youtube_server())
