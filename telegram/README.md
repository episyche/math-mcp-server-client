# Telegram MCP Server

A unified Telegram MCP (Model Context Protocol) server that provides direct access to Telegram functionality through Claude and other MCP clients.

## Features

- **Direct Telegram API Integration**: Uses Telethon library for direct communication with Telegram
- **Authentication Management**: Handles phone verification and two-factor authentication
- **Contact Management**: Search and manage Telegram contacts
- **Chat Operations**: List chats, get chat history, and manage conversations
- **Message Operations**: Send messages, search messages, and export chat history
- **Self-Contained**: No external bridge service required

## Setup

### 1. Get Telegram API Credentials

1. Visit [https://my.telegram.org/auth](https://my.telegram.org/auth)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Note down your `API_ID` and `API_HASH`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the telegram directory with:

```env
# Telegram API Credentials
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# Your phone number (with country code, e.g., +1234567890)
TELEGRAM_PHONE=+1234567890

# Optional: Custom session file name (default: telegram_session)
TELEGRAM_SESSION_FILE=telegram_session
```

### 4. First-Time Authentication

1. Run the MCP server
2. Use `authenticate_with_code()` with the verification code sent to your phone
3. If you have two-factor authentication enabled, use `authenticate_with_password()`

## Available Tools

### Authentication
- `authenticate_with_code(code: str)` - Authenticate with verification code
- `authenticate_with_password(password: str)` - Complete 2FA authentication

### User Information
- `get_my_info()` - Get current user information

### Contact Management
- `search_contacts(query: str, limit: int = 20)` - Search contacts by name/username
- `list_chats(limit: int = 20, chat_type: str = "all")` - List all chats

### Message Operations
- `get_chat_history(chat_id: int, limit: int = 20)` - Get chat message history
- `send_message(recipient: str, message: str)` - Send message to recipient
- `search_messages(query: str, chat_id: Optional[int] = None, limit: int = 20)` - Search messages

### Utility
- `get_chat_info(chat_id: int)` - Get detailed chat information
- `export_chat_history(chat_id: int, limit: int = 100, format: str = "text")` - Export chat history

## Usage Examples

### Search for a Contact
```
search_contacts("John Doe")
```

### Send a Message
```
send_message("@username", "Hello from Claude!")
```

### Get Chat History
```
get_chat_history(123456789, 50)
```

### Search Messages
```
search_messages("important", 123456789)
```

## Architecture

This MCP server follows the same pattern as other MCP servers in the project:
- Direct API integration (no external bridge)
- Async/await pattern for Telegram operations
- Proper error handling and logging
- Environment-based configuration
- Session management for authentication

## Security Notes

- API credentials are stored in environment variables
- Session files contain authentication tokens - keep them secure
- Phone numbers are used only for initial authentication
- All operations respect Telegram's rate limits and policies

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `telethon` is installed
2. **Authentication Failed**: Check your API credentials and phone number
3. **Session Issues**: Delete the session file to start fresh
4. **Rate Limiting**: Telegram may limit API calls for new accounts

### Logs

Check the `logs/mcp_error.log` file for detailed error information.

## Migration from Old Bridge

If you were using the old telegram-bridge system:

1. The new server is self-contained and doesn't require the bridge
2. Your session file can be reused (copy `telegram_session` file)
3. Database operations are now handled directly through Telegram API
4. All functionality is available through MCP tools

## Contributing

Feel free to submit issues and enhancement requests!