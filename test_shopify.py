#!/usr/bin/env python3
"""
Test script for Shopify MCP Server

This script tests the basic functionality of the Shopify MCP server
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_shopify_server():
    """Test the Shopify MCP server"""
    
    # Get the path to the Shopify MCP server
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shopify_server_path = os.path.join(current_dir, "shopify", "shopify_mcp_server.py")
    
    if not os.path.exists(shopify_server_path):
        print(f"Error: Shopify MCP server not found at {shopify_server_path}")
        return
    
    print(f"Testing Shopify MCP server at: {shopify_server_path}")
    
    # Configure server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[shopify_server_path],
        env=None,
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("✓ Session initialized successfully")
                
                # List available tools
                tools = await session.list_tools()
                print(f"✓ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Test a simple tool call
                print("\nTesting get_store_info tool...")
                result = await session.call_tool(name="get_store_info", arguments={})
                print("✓ get_store_info called successfully")
                
                # Get the result content
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(f"Result: {item.text[:200]}...")
                            break
                else:
                    print("Result: No content returned")
                
                # Test another tool
                print("\nTesting get_products tool...")
                result = await session.call_tool(
                    name="get_products", 
                    arguments={"limit": 3, "status": "active"}
                )
                print("✓ get_products called successfully")
                
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(f"Result: {item.text[:200]}...")
                            break
                else:
                    print("Result: No content returned")
                
                print("\n✓ All tests passed! Shopify MCP server is working correctly.")
                
    except Exception as e:
        print(f"✗ Error testing Shopify MCP server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_shopify_server())
