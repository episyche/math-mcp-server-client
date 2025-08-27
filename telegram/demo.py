#!/usr/bin/env python3
"""
Demo script for the Telegram MCP Server

This script demonstrates how to use the telegram MCP server
programmatically without going through the full MCP protocol.
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
        list_chats,
        get_chat_history,
        send_message,
        search_messages
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the telegram directory and all dependencies are installed")
    sys.exit(1)

async def demo_basic_operations():
    """Demonstrate basic Telegram operations."""
    print("🚀 Telegram MCP Server Demo")
    print("=" * 50)
    
    try:
        # Get user info
        print("\n1. Getting user information...")
        user_info = await get_my_info()
        print(f"   Result: {user_info}")
        
        # List chats
        print("\n2. Listing recent chats...")
        chats = await list_chats(limit=5)
        print(f"   Result: {chats}")
        
        # Search contacts
        print("\n3. Searching for contacts...")
        contacts = await search_contacts("", limit=3)
        print(f"   Result: {contacts}")
        
        print("\n✅ Basic operations completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

async def demo_message_operations():
    """Demonstrate message-related operations."""
    print("\n📱 Message Operations Demo")
    print("=" * 50)
    
    try:
        # List chats to get a chat ID for testing
        print("\n1. Getting chat list for testing...")
        chats = await list_chats(limit=3)
        print(f"   Available chats: {chats}")
        
        # Note: In a real scenario, you would use actual chat IDs
        print("\n2. Message operations available:")
        print("   - get_chat_history(chat_id, limit)")
        print("   - send_message(recipient, message)")
        print("   - search_messages(query, chat_id, limit)")
        
        print("\n✅ Message operations demo completed!")
        
    except Exception as e:
        print(f"❌ Message demo failed: {e}")

async def demo_authentication():
    """Demonstrate authentication flow."""
    print("\n🔐 Authentication Demo")
    print("=" * 50)
    
    try:
        # Check if already authenticated
        client = await get_telegram_client()
        
        if await client.is_user_authorized():
            print("✅ User is already authenticated")
            print("   You can use all Telegram features")
        else:
            print("⚠️ User not authenticated")
            print("   Use these tools to authenticate:")
            print("   1. authenticate_with_code(verification_code)")
            print("   2. authenticate_with_password(password) - if 2FA enabled")
        
        print("\n✅ Authentication demo completed!")
        
    except Exception as e:
        print(f"❌ Authentication demo failed: {e}")

async def main():
    """Main demo function."""
    print("🎯 Starting Telegram MCP Server Demo...\n")
    
    # Check if .env file exists
    env_file = telegram_dir / ".env"
    if not env_file.exists():
        print("⚠️ No .env file found. Please create one with your Telegram credentials.")
        print("See README.md for setup instructions.")
        sys.exit(1)
    
    try:
        # Run demos
        await demo_authentication()
        await demo_basic_operations()
        await demo_message_operations()
        
        print("\n🎉 All demos completed successfully!")
        print("\n📝 Next steps:")
        print("1. Use the MCP server tools in your MCP client")
        print("2. Run the server with: python telegram_mcp_server.py")
        print("3. Check the README.md for more examples")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Check your configuration and try again")

if __name__ == "__main__":
    asyncio.run(main())
