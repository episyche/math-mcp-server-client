from __future__ import annotations

import io
import logging
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import requests
from dotenv import load_dotenv, set_key
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Import Telethon for direct Telegram API access
try:
    from telethon import TelegramClient
    from telethon.tl.types import User, Chat, Channel, Message, Dialog
    from telethon.utils import get_display_name
    from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
except ImportError:
    print("ERROR: Telethon not installed. Run: pip install telethon")
    sys.exit(1)

mcp = FastMCP("TelegramServer")

# Path to .env file
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# Load environment variables at startup
load_dotenv(ENV_PATH)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger("TelegramServer")

# Global client instance
telegram_client = None

def sanitize_text(text: str) -> str:
    """Sanitize text to avoid encoding issues in MCP responses."""
    if not text:
        return ""
    try:
        # Convert to string and handle encoding gracefully
        sanitized = str(text)
        # Only allow basic ASCII characters (32-126) plus newlines and tabs
        # Also remove any potential problematic characters
        sanitized = ''.join(char for char in sanitized if 32 <= ord(char) <= 126 or char in '\n\r\t')
        
        # Additional safety: replace any remaining problematic characters
        sanitized = sanitized.replace('\x00', '')  # Remove null bytes
        sanitized = sanitized.replace('\ufffd', '?')  # Replace replacement characters
        
        # Ensure the result is a valid string
        sanitized = sanitized.encode('ascii', errors='replace').decode('ascii')
        
        return sanitized
    except Exception:
        # Fallback: return a safe string
        safe_text = str(text)[:100] if len(str(text)) > 100 else str(text)
        return safe_text.encode('ascii', errors='replace').decode('ascii')

def safe_mcp_response(text: str) -> CallToolResult:
    """Create a safe MCP response that won't cause encoding issues."""
    try:
        # Convert to string first
        text_str = str(text) if text else ""
        
        # Completely strip all non-ASCII characters
        safe_text = ""
        for char in text_str:
            if 32 <= ord(char) <= 126 or char in '\n\r\t':
                safe_text += char
            else:
                safe_text += "?"  # Replace problematic characters with ?
        
        # Final safety: encode/decode to ensure complete compatibility
        safe_text = safe_text.encode('ascii', errors='replace').decode('ascii')
        
        # Remove any remaining problematic characters
        safe_text = ''.join(char for char in safe_text if ord(char) < 128)
        
        # Ensure we have a valid response
        if not safe_text.strip():
            safe_text = "No data available (encoding issues)"
        
        logger.info(f"Created safe MCP response: {len(safe_text)} characters")
        
        return CallToolResult(
            content=[TextContent(type="text", text=safe_text)]
        )
    except Exception as e:
        # Ultimate fallback: return a simple error message
        logger.error(f"Failed to create safe MCP response: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Unable to process response due to encoding issues")]
        )

def update_env(key: str, value: str):
    """Update or add a key=value pair in .env and reload."""
    set_key(ENV_PATH, key, value)
    os.environ[key] = value

def get_telegram_credentials():
    """Get Telegram API credentials from environment."""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    session_file = os.getenv("TELEGRAM_SESSION_FILE", "telegram_session")
    
    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
    
    return api_id, api_hash, phone, session_file

async def get_telegram_client():
    """Get or create Telegram client instance."""
    global telegram_client
    
    if telegram_client is None:
        api_id, api_hash, phone, session_file = get_telegram_credentials()
        
        # Create session file path
        session_path = os.path.join(os.path.dirname(__file__), session_file)
        
        telegram_client = TelegramClient(session_path, int(api_id), api_hash)
        
        try:
            await telegram_client.connect()
            if not await telegram_client.is_user_authorized():
                if phone:
                    logger.info("Sending code request to phone number...")
                    await telegram_client.send_code_request(phone)
                    logger.info("Please check your phone for the verification code")
                else:
                    raise ValueError("TELEGRAM_PHONE must be set for first-time authentication")
            else:
                logger.info("Already authorized with Telegram")
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            raise
    
    return telegram_client

# ---------------------------
# Authentication Tools
# ---------------------------

@mcp.tool()
async def authenticate_with_code(code: str):
    """Authenticate with Telegram using the verification code sent to your phone."""
    try:
        client = await get_telegram_client()
        
        if await client.is_user_authorized():
            return CallToolResult(
                content=[TextContent(type="text", text="Already authenticated with Telegram")]
            )
        
        try:
            await client.sign_in(phone=os.getenv("TELEGRAM_PHONE"), code=code)
            logger.info("Successfully authenticated with Telegram")
            return CallToolResult(
                content=[TextContent(type="text", text="Successfully authenticated with Telegram")]
            )
        except SessionPasswordNeededError:
            return CallToolResult(
                content=[TextContent(type="text", text="Two-factor authentication required. Use authenticate_with_password()")]
            )
        except PhoneCodeInvalidError:
            return CallToolResult(
                content=[TextContent(type="text", text="Invalid verification code. Please try again.")]
            )
            
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Authentication failed: {str(e)}")]
        )

@mcp.tool()
async def authenticate_with_password(password: str):
    """Complete two-factor authentication with your password."""
    try:
        client = await get_telegram_client()
        
        if await client.is_user_authorized():
            return CallToolResult(
                content=[TextContent(type="text", text="Already authenticated with Telegram")]
            )
        
        await client.sign_in(password=password)
        logger.info("Successfully completed two-factor authentication")
        return CallToolResult(
            content=[TextContent(type="text", text="Successfully completed two-factor authentication")]
            )
            
    except Exception as e:
        logger.error(f"Two-factor authentication failed: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Two-factor authentication failed: {str(e)}")]
        )

# ---------------------------
# Contact and Chat Tools
# ---------------------------

@mcp.tool()
async def get_my_info():
    """Get information about the current user."""
    try:
        client = await get_telegram_client()
        me = await client.get_me()
        
        user_info = {
            "id": me.id,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "phone": me.phone,
            "is_bot": me.bot,
            "verified": me.verified,
            "premium": getattr(me, 'premium', False)
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"Current user: {user_info['first_name']} {user_info['last_name']} (@{user_info['username']}) - ID: {user_info['id']}")]
        )
        
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to get user info: {str(e)}")]
        )

@mcp.tool()
async def search_contacts(query: str, limit: int = 20):
    """Search Telegram contacts by name or username."""
    try:
        client = await get_telegram_client()
        
        # Get all dialogs (chats)
        dialogs = await client.get_dialogs(limit=limit)
        
        matching_contacts = []
        for dialog in dialogs:
            entity = dialog.entity
            
            # Check if it's a user (contact)
            if hasattr(entity, 'first_name') and hasattr(entity, 'last_name'):
                full_name = f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip()
                username = getattr(entity, 'username', '')
                
                # Check if query matches name or username
                if (query.lower() in full_name.lower() or 
                    (username and query.lower() in username.lower())):
                    matching_contacts.append({
                        "id": entity.id,
                        "name": full_name,
                        "username": username,
                        "phone": getattr(entity, 'phone', None),
                        "verified": getattr(entity, 'verified', False),
                        "premium": getattr(entity, 'premium', False)
                    })
        
        if matching_contacts:
            result_text = f"Found {len(matching_contacts)} matching contacts:\n"
            for contact in matching_contacts:
                # Use sanitize_text function
                clean_name = sanitize_text(contact['name']) if contact['name'] else 'Unknown'
                clean_username = sanitize_text(contact['username']) if contact['username'] else 'None'
                result_text += f"• {clean_name} (@{clean_username}) - ID: {contact['id']}\n"
        else:
            result_text = f"No contacts found matching '{query}'"
        
        return safe_mcp_response(result_text)
        
    except Exception as e:
        logger.error(f"Failed to search contacts: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to search contacts: {str(e)}")]
        )

@mcp.tool()
async def list_chats(limit: int = 20, chat_type: str = "all"):
    """List Telegram chats (dialogs)."""
    try:
        client = await get_telegram_client()
        
        dialogs = await client.get_dialogs(limit=limit)
        
        chats = []
        for dialog in dialogs:
            entity = dialog.entity
            chat_type_actual = "user" if hasattr(entity, 'first_name') else "group" if hasattr(entity, 'megagroup') else "channel"
            
            if chat_type == "all" or chat_type == chat_type_actual:
                if chat_type_actual == "user":
                    name = f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip()
                    username = getattr(entity, 'username', '')
                    chats.append({
                        "id": entity.id,
                        "name": name,
                        "username": username,
                        "type": "user",
                        "last_message": dialog.message.message if dialog.message else None,
                        "last_message_date": dialog.date.isoformat() if dialog.date else None
                    })
                else:
                    chats.append({
                        "id": entity.id,
                        "name": getattr(entity, 'title', 'Unknown'),
                        "username": getattr(entity, 'username', None),
                        "type": chat_type_actual,
                        "last_message": dialog.message.message if dialog.message else None,
                        "last_message_date": dialog.date.isoformat() if dialog.date else None
                    })
        
        result_text = f"Found {len(chats)} chats:\n"
        for chat in chats:
            # Use sanitize_text function
            clean_name = sanitize_text(chat['name']) if chat['name'] else 'Unknown'
            clean_message = sanitize_text(chat['last_message']) if chat['last_message'] else None
            
            result_text += f"• {clean_name} ({chat['type']}) - ID: {chat['id']}\n"
            if clean_message:
                result_text += f"  Last message: {clean_message[:50]}...\n"
        
        return safe_mcp_response(result_text)
        
    except Exception as e:
        logger.error(f"Failed to list chats: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to list chats: {str(e)}")]
        )

# ---------------------------
# Message Tools
# ---------------------------

@mcp.tool()
async def get_chat_history(chat_id: int, limit: int = 20):
    """Get message history for a specific chat."""
    try:
        client = await get_telegram_client()
        
        # Get the entity (chat/user)
        entity = await client.get_entity(chat_id)
        
        # Get messages
        messages = await client.get_messages(entity, limit=limit)
        
        if not messages:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No messages found for chat ID {chat_id}")]
            )
        
        # Use sanitize_text function
        chat_name = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
        clean_chat_name = sanitize_text(chat_name)
        
        result_text = f"Chat: {clean_chat_name}\n"
        result_text += f"Last {len(messages)} messages:\n\n"
        
        for msg in reversed(messages):
            if msg.message:
                sender = "You" if msg.out else getattr(msg.sender, 'first_name', 'Unknown')
                clean_sender = sanitize_text(sender)
                time = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "Unknown time"
                clean_message = sanitize_text(msg.message)
                result_text += f"[{time}] {clean_sender}: {clean_message[:100]}{'...' if len(clean_message) > 100 else ''}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to get chat history: {str(e)}")]
        )

@mcp.tool()
async def send_message(recipient: str, message: str):
    """Send a message to a recipient (can be username, phone, or chat ID)."""
    try:
        client = await get_telegram_client()
        
        # Try to resolve the recipient
        try:
            if recipient.isdigit():
                # If it's a numeric ID
                entity = await client.get_entity(int(recipient))
            elif recipient.startswith('@'):
                # If it's a username
                entity = await client.get_entity(recipient)
            else:
                # Try as username without @
                entity = await client.get_entity(f"@{recipient}")
        except Exception:
            # Try as phone number
            entity = await client.get_entity(recipient)
        
        # Send the message
        sent_message = await client.send_message(entity, message)
        
        recipient_name = getattr(entity, 'title', getattr(entity, 'first_name', str(entity.id)))
        
        return CallToolResult(
            content=[TextContent(type="text", text=f"Message sent successfully to {recipient_name}")]
        )
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to send message: {str(e)}")]
        )

@mcp.tool()
async def search_messages(query: str, chat_id: Optional[int] = None, limit: int = 20):
    """Search for messages containing specific text."""
    try:
        client = await get_telegram_client()
        
        if chat_id:
            # Search in specific chat
            entity = await client.get_entity(chat_id)
            messages = await client.get_messages(entity, search=query, limit=limit)
        else:
            # Search in all dialogs
            messages = []
            dialogs = await client.get_dialogs(limit=50)
            
            for dialog in dialogs:
                try:
                    chat_messages = await client.get_messages(dialog.entity, search=query, limit=5)
                    messages.extend(chat_messages)
                except Exception:
                    continue
        
        if not messages:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No messages found containing '{query}'")]
            )
        
        result_text = f"Found {len(messages)} messages containing '{query}':\n\n"
        
        for msg in messages[:limit]:
            if msg.message:
                chat_name = getattr(msg.chat, 'title', getattr(msg.chat, 'first_name', 'Unknown'))
                sender = "You" if msg.out else getattr(msg.sender, 'first_name', 'Unknown')
                time = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "Unknown time"
                
                # Use sanitize_text function
                clean_chat_name = sanitize_text(chat_name)
                clean_sender = sanitize_text(sender)
                clean_message = sanitize_text(msg.message)
                
                result_text += f"[{time}] {clean_chat_name} - {clean_sender}: {clean_message[:100]}{'...' if len(clean_message) > 100 else ''}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
        
    except Exception as e:
        logger.error(f"Failed to search messages: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to search messages: {str(e)}")]
        )

# ---------------------------
# Utility Tools
# ---------------------------

@mcp.tool()
async def get_chat_info(chat_id: int):
    """Get detailed information about a specific chat."""
    try:
        client = await get_telegram_client()
        
        entity = await client.get_entity(chat_id)
        
        if hasattr(entity, 'first_name'):  # User
            info = {
                "id": entity.id,
                "type": "user",
                "name": f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip(),
                "username": getattr(entity, 'username', None),
                "phone": getattr(entity, 'phone', None),
                "verified": getattr(entity, 'verified', False),
                "premium": getattr(entity, 'premium', False),
                "bot": getattr(entity, 'bot', False)
            }
        elif hasattr(entity, 'megagroup'):  # Group
            info = {
                "id": entity.id,
                "type": "group",
                "title": getattr(entity, 'title', 'Unknown'),
                "username": getattr(entity, 'username', None),
                "megagroup": getattr(entity, 'megagroup', False),
                "gigagroup": getattr(entity, 'gigagroup', False),
                "verified": getattr(entity, 'verified', False)
            }
        else:  # Channel
            info = {
                "id": entity.id,
                "type": "channel",
                "title": getattr(entity, 'title', 'Unknown'),
                "username": getattr(entity, 'username', None),
                "verified": getattr(entity, 'verified', False),
                "broadcast": getattr(entity, 'broadcast', False)
            }
        
        result_text = f"Chat Information:\n"
        for key, value in info.items():
            if value is not None:
                # Use sanitize_text function
                clean_value = sanitize_text(value)
                result_text += f"• {key}: {clean_value}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat info: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to get chat info: {str(e)}")]
        )

@mcp.tool()
async def export_chat_history(chat_id: int, limit: int = 100, format: str = "text"):
    """Export chat history in various formats."""
    try:
        client = await get_telegram_client()
        
        entity = await client.get_entity(chat_id)
        messages = await client.get_messages(entity, limit=limit)
        
        if not messages:
            return CallToolResult(
                content=[TextContent(type="text", text=f"No messages found for chat ID {chat_id}")]
            )
        
        chat_name = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
        # Use sanitize_text function
        clean_chat_name = sanitize_text(chat_name)
        
        if format.lower() == "json":
            # Export as JSON-like structure
            export_data = {
                "chat_name": clean_chat_name,
                "chat_id": chat_id,
                "export_date": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": []
            }
            
            for msg in reversed(messages):
                if msg.message:
                    sender = "You" if msg.out else getattr(msg.sender, 'first_name', 'Unknown')
                    clean_sender = sanitize_text(sender)
                    clean_message = sanitize_text(msg.message)
                    export_data["messages"].append({
                        "id": msg.id,
                        "sender": clean_sender,
                        "message": clean_message,
                        "date": msg.date.isoformat() if msg.date else None,
                        "reply_to": msg.reply_to.reply_to_msg_id if msg.reply_to else None
                    })
            
            result_text = f"Exported {len(messages)} messages from {clean_chat_name} in JSON format:\n"
            result_text += str(export_data)
        else:
            # Default text format
            result_text = f"Chat History Export - {clean_chat_name}\n"
            result_text += f"Exported {len(messages)} messages\n"
            result_text += "=" * 50 + "\n\n"
            
            for msg in reversed(messages):
                if msg.message:
                    sender = "You" if msg.out else getattr(msg.sender, 'first_name', 'Unknown')
                    time = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "Unknown time"
                    clean_sender = sanitize_text(sender)
                    clean_message = sanitize_text(msg.message)
                    result_text += f"[{time}] {clean_sender}: {clean_message}\n"
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_text)]
        )
        
    except Exception as e:
        logger.error(f"Failed to export chat history: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to export chat history: {str(e)}")]
        )

# ---------------------------
# Main Execution
# ---------------------------

if __name__ == "__main__":
    import asyncio
    
    # Create logs directory
    os.makedirs(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"),
        exist_ok=True,
    )
    
    # Redirect stderr to log file
    sys.stderr = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "mcp_error.log"),
        "w",
    )
    
    # Run the MCP server
    mcp.run(transport="stdio")
