#!/usr/bin/env python3
"""
Test script for the Telegram MCP Server

This script tests the basic functionality of the telegram MCP server
without requiring full MCP client setup.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the telegram directory to the path
telegram_dir = Path(__file__).parent
sys.path.insert(0, str(telegram_dir))

# Import the telegram MCP server functions
try:
    from telegram_mcp_server import (
        get_telegram_credentials,
        get_telegram_client,
        get_my_info,
        search_contacts,
        list_chats
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the telegram directory and all dependencies are installed")
    sys.exit(1)

async def test_credentials():
    """Test if Telegram credentials are properly configured."""
    print("🔍 Testing Telegram credentials...")
    
    try:
        api_id, api_hash, phone, session_file = get_telegram_credentials()
        print(f"✅ Credentials loaded successfully:")
        print(f"   API ID: {api_id}")
        print(f"   API Hash: {api_hash[:10]}...")
        print(f"   Phone: {phone}")
        print(f"   Session File: {session_file}")
        return True
    except ValueError as e:
        print(f"❌ Credentials error: {e}")
        print("Please check your .env file")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_connection():
    """Test connection to Telegram API."""
    print("\n🔌 Testing Telegram API connection...")
    
    try:
        client = await get_telegram_client()
        print("✅ Successfully connected to Telegram API")
        
        # Check if authorized
        if await client.is_user_authorized():
            print("✅ User is already authorized")
            return True
        else:
            print("⚠️ User not authorized - authentication required")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_basic_functions():
    """Test basic MCP server functions."""
    print("\n🧪 Testing basic functions...")
    
    try:
        # Test get_my_info
        print("Testing get_my_info...")
        result = await get_my_info()
        print(f"✅ get_my_info result: {result}")
        
        # Test list_chats
        print("Testing list_chats...")
        result = await list_chats(limit=5)
        print(f"✅ list_chats result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Function test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Starting Telegram MCP Server tests...\n")
    
    # Test 1: Credentials
    if not await test_credentials():
        print("\n❌ Credentials test failed. Cannot continue.")
        return
    
    # Test 2: Connection
    if not await test_connection():
        print("\n⚠️ Connection test failed. Authentication may be required.")
        print("Use the MCP server tools to authenticate first.")
        return
    
    # Test 3: Basic functions
    if await test_basic_functions():
        print("\n✅ All tests passed! The Telegram MCP server is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
    
    print("\n📝 Next steps:")
    print("1. If authentication is required, use the MCP server tools")
    print("2. Run the server with: python telegram_mcp_server.py")
    print("3. Integrate with your MCP client")

if __name__ == "__main__":
    # Check if .env file exists
    env_file = telegram_dir / ".env"
    if not env_file.exists():
        print("⚠️ No .env file found. Please create one with your Telegram credentials.")
        print("See README.md for setup instructions.")
        sys.exit(1)
    
    # Run tests
    asyncio.run(main())
