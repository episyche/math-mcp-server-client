"""
Telegram MCP Server

The server uses FastMCP to expose Telegram functionality in a standardized way,
with each tool implemented as a decorated function. This allows Claude (or other MCP clients) to:
1. Search contacts and chats
2. Retrieve message history with optional context
3. Send messages to individuals or groups

The server connects to the local SQLite database maintained by the Telegram Bridge,
and also communicates with the Bridge's HTTP API for sending messages.
"""

from typing import List, Dict, Any, Optional, Tuple
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import logging

# --- Import bridge functions ---
from telegram import (
    search_contacts as telegram_search_contacts,
    list_messages as telegram_list_messages,
    list_chats as telegram_list_chats,
    get_chat as telegram_get_chat,
    get_all_contacts as telegram_get_all_contacts,
    get_direct_chat_by_contact as telegram_get_direct_chat_by_contact,
    get_contact_chats as telegram_get_contact_chats,
    get_last_interaction as telegram_get_last_interaction,
    get_message_context as telegram_get_message_context,
    send_message as telegram_send_message,
)

# --- Logging setup ---
logging.basicConfig(
    filename="telegram_mcp.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Initialize FastMCP server
mcp = FastMCP("telegram")

# --- universal safe serializer ---
def to_dict(obj: Any) -> Any:
    """Recursively convert custom objects into dicts/lists."""
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_dict(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {k: to_dict(v) for k, v in vars(obj).items()}
    return obj

# ----------------- TOOLS -----------------

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search Telegram contacts by name or username."""
    contacts = telegram_search_contacts(query)
    return to_dict(contacts)

@mcp.tool()
def get_all_contacts(limit: int = 1000, page: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve all Telegram contacts (users only).
    Use `limit` and `page` for pagination if you have many contacts.
    Example: get_all_contacts(limit=50, page=2)
    """
    contacts = telegram_get_all_contacts(limit=limit, page=page)
    return to_dict(contacts)


@mcp.tool()
def list_messages(
    date_range: Optional[Tuple[datetime, datetime]] = None,
    sender_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1,
) -> List[Dict[str, Any]]:
    """Get Telegram messages matching specified criteria with optional context."""
    messages = telegram_list_messages(
        date_range=date_range,
        sender_id=sender_id,
        chat_id=chat_id,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after,
    )
    return to_dict(messages)

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    chat_type: Optional[str] = None,
    sort_by: str = "last_active",
) -> List[Dict[str, Any]]:
    """Get Telegram chats matching specified criteria."""
    chats = telegram_list_chats(
        query=query,
        limit=limit,
        page=page,
        chat_type=chat_type,
        sort_by=sort_by,
    )
    return to_dict(chats)

@mcp.tool()
def get_chat(chat_id: int) -> Dict[str, Any]:
    """Get Telegram chat metadata by ID."""
    chat = telegram_get_chat(chat_id)
    return to_dict(chat)

@mcp.tool()
def get_direct_chat_by_contact(contact_id: int) -> Dict[str, Any]:
    """Get Telegram chat metadata by contact ID."""
    chat = telegram_get_direct_chat_by_contact(contact_id)
    return to_dict(chat)

@mcp.tool()
def get_contact_chats(contact_id: int, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all Telegram chats involving the contact."""
    chats = telegram_get_contact_chats(contact_id, limit, page)
    return to_dict(chats)

@mcp.tool()
def get_last_interaction(contact_id: int) -> Dict[str, Any]:
    """Get most recent Telegram message involving the contact."""
    message = telegram_get_last_interaction(contact_id)
    return to_dict(message)

@mcp.tool()
def get_message_context(
    chat_id: int,
    message_id: int,
    before: int = 5,
    after: int = 5,
) -> Dict[str, Any]:
    """Get context around a specific Telegram message."""
    context = telegram_get_message_context(chat_id, message_id, before, after)
    return to_dict(context)

@mcp.tool()
def send_message(recipient: str, message: str) -> Dict[str, Any]:
    """Send a Telegram message to a person or group."""
    if not recipient:
        return {"success": False, "message": "Recipient must be provided"}
    try:
        success, status_message = telegram_send_message(recipient, message)
        return {"success": success, "message": status_message}
    except Exception as e:
        logging.error(f"send_message error: {e}")
        return {"success": False, "message": str(e)}

# ----------------- MAIN -----------------

if __name__ == "__main__":
    import sys, os
    os.makedirs(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"),
        exist_ok=True,
    )
    sys.stderr = open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "mcp_error.log"),
        "w",
    )
    mcp.run(transport="stdio")
