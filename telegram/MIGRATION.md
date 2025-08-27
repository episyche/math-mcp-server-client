# Migration Guide: From Old Bridge to New Unified MCP Server

This document explains the differences between the old telegram-bridge system and the new unified telegram MCP server, and how to migrate.

## Architecture Changes

### Old System (Complex)
```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│   MCP       │    │  Telegram       │    │  Telegram   │
│  Client     │◄──►│   Bridge        │◄──►│     API     │
│             │    │  (HTTP Server)  │    │             │
└─────────────┘    └─────────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────────┐
                   │  SQLite         │
                   │  Database       │
                   └─────────────────┘
```

### New System (Unified)
```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│   MCP       │    │  Telegram       │    │  Telegram   │
│  Client     │◄──►│  MCP Server     │◄──►│     API     │
│             │    │  (Direct)       │    │             │
└─────────────┘    └─────────────────┘    └─────────────┘
```

## Key Differences

| Aspect | Old Bridge System | New Unified Server |
|--------|------------------|-------------------|
| **Architecture** | Multi-service (bridge + MCP server) | Single MCP server |
| **Dependencies** | Complex (FastAPI, SQLAlchemy, etc.) | Simple (Telethon + MCP) |
| **Setup** | Requires running bridge service | Self-contained |
| **Database** | Local SQLite storage | Direct API access |
| **Maintenance** | Multiple components to manage | Single component |
| **Performance** | Database queries + API calls | Direct API calls |
| **Complexity** | High (multiple services) | Low (single service) |

## Migration Steps

### 1. Backup Your Data
If you have important data in the old SQLite database:
```bash
# Copy the old database
cp telegram-bridge/store/messages.db ./messages_backup.db
```

### 2. Install New Dependencies
```bash
# Remove old requirements
pip uninstall fastapi uvicorn sqlalchemy pydantic

# Install new requirements
pip install -r requirements.txt
```

### 3. Configure New Server
```bash
# Run the setup script
python setup.py

# Or manually create .env file
cp .env.example .env
# Edit .env with your credentials
```

### 4. Test the New Server
```bash
# Test basic functionality
python test_telegram_server.py

# Run demo
python demo.py
```

### 5. Update Your MCP Client Configuration
Replace the old bridge configuration with the new server:

**Old (Bridge-based):**
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["telegram-bridge/main.py"]
    }
  }
}
```

**New (Unified):**
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["telegram_mcp_server.py"]
    }
  }
}
```

## Feature Mapping

### Old Tools → New Tools

| Old Tool | New Tool | Notes |
|----------|----------|-------|
| `search_contacts` | `search_contacts` | Same functionality |
| `list_messages` | `get_chat_history` | More focused approach |
| `list_chats` | `list_chats` | Same functionality |
| `get_chat` | `get_chat_info` | Enhanced information |
| `send_message` | `send_message` | Same functionality |
| `get_message_context` | `search_messages` | More flexible search |
| - | `get_my_info` | New: Get user information |
| - | `authenticate_with_code` | New: Authentication helper |
| - | `authenticate_with_password` | New: 2FA support |
| - | `export_chat_history` | New: Export functionality |

## Benefits of Migration

### ✅ Advantages
- **Simpler Setup**: Single server instead of multiple services
- **Better Performance**: Direct API calls instead of database queries
- **Easier Maintenance**: One component to manage
- **Real-time Data**: Always fresh data from Telegram
- **Better Error Handling**: Direct error messages from API
- **Authentication Management**: Built-in auth flow

### ⚠️ Considerations
- **No Local Storage**: Messages aren't cached locally
- **API Rate Limits**: Subject to Telegram's API limits
- **Internet Required**: Always needs internet connection
- **Session Management**: Session files need to be managed

## Troubleshooting Migration

### Common Issues

1. **Import Errors**
   ```bash
   pip install telethon mcp fastmcp python-dotenv
   ```

2. **Authentication Issues**
   - Delete old session files
   - Use new authentication tools
   - Check API credentials

3. **Missing Dependencies**
   ```bash
   python setup.py  # This will check and install dependencies
   ```

4. **Configuration Issues**
   - Ensure .env file is in the right location
   - Check API credentials format
   - Verify phone number format

### Getting Help

- Check the logs in `logs/mcp_error.log`
- Run `python test_telegram_server.py` for diagnostics
- Use `python demo.py` to test functionality
- Review the README.md for detailed setup instructions

## Rollback Plan

If you need to rollback to the old system:

1. **Keep the old files**: Don't delete the `telegram-bridge/` directory
2. **Restore configuration**: Use your old MCP client configuration
3. **Restart services**: Start the bridge service again
4. **Verify functionality**: Test that the old system works

## Conclusion

The new unified telegram MCP server provides a simpler, more maintainable solution that follows the same pattern as other MCP servers in the project. While it removes local data storage, it offers better performance, easier setup, and real-time data access.

The migration is straightforward and the benefits significantly outweigh the minor drawbacks. The new system is more aligned with modern MCP server design patterns and will be easier to maintain and extend in the future.
