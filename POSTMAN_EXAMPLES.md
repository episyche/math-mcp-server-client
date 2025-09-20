# MCP HTTP Server - Postman Examples

This document provides examples for testing the MCP HTTP Server endpoints using Postman.

## Server Setup

1. **Start the server:**
   ```bash
   python start_server.py
   ```
   or
   ```bash
   python mcp_http_server.py
   ```

2. **Server will be available at:** `http://localhost:8000`

## Environment Variables Required

Make sure you have the following environment variable set:
- `OPENAI_API_KEY`: Your OpenAI API key

## Available Endpoints

### 1. Health Check
- **Method:** GET
- **URL:** `http://localhost:8000/health`
- **Description:** Check if the server and MCP client are properly initialized

### 2. Root Endpoint
- **Method:** GET
- **URL:** `http://localhost:8000/`
- **Description:** Get server information and available endpoints

### 3. Query via POST (JSON Body)
- **Method:** POST
- **URL:** `http://localhost:8000/query`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "query": "get all my videos in youtube",
    "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0",
    "max_steps": 10
  }
  ```

### 4. Query via GET (Query Parameters)
- **Method:** GET
- **URL:** `http://localhost:8000/query?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0&max_steps=10`

### 5. Streaming Query (Server-Sent Events)
- **Method:** GET
- **URL:** `http://localhost:8000/query/stream?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0`
- **Description:** Returns streaming response with real-time updates

## Postman Collection Examples

### Example 1: YouTube Video Listing
```json
{
  "method": "POST",
  "url": "http://localhost:8000/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "get all my videos in youtube",
    "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0"
  }
}
```

### Example 2: Gmail Unread Emails
```json
{
  "method": "POST",
  "url": "http://localhost:8000/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "get my unread emails",
    "user_id": "your-gmail-user-id"
  }
}
```

### Example 3: X (Twitter) Post Creation
```json
{
  "method": "POST",
  "url": "http://localhost:8000/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "create a post saying 'Hello from MCP HTTP Server!'",
    "user_id": "your-x-user-id"
  }
}
```

### Example 4: Shopify Store Analytics
```json
{
  "method": "POST",
  "url": "http://localhost:8000/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "get my store analytics and statistics",
    "user_id": "your-shopify-user-id"
  }
}
```

### Example 5: Google Ads Campaign Listing
```json
{
  "method": "POST",
  "url": "http://localhost:8000/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "list all my advertising campaigns",
    "user_id": "your-google-ads-user-id"
  }
}
```

## Streaming Endpoint Usage

For the streaming endpoint (`/query/stream`), you can test it in Postman by:

1. **Set up the request:**
   - Method: GET
   - URL: `http://localhost:8000/query/stream?query=your-query&user_id=your-user-id`

2. **Expected Response Format:**
   ```
   data: {"type": "status", "message": "Starting MCP query...", "timestamp": "2025-01-17T..."}

   data: {"type": "result", "data": {...}, "timestamp": "2025-01-17T..."}

   data: {"type": "complete", "message": "Query completed successfully", "timestamp": "2025-01-17T..."}
   ```

## Response Format

### Success Response
```json
{
  "success": true,
  "result": "...",
  "timestamp": "2025-01-17T12:00:00.000Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message here",
  "timestamp": "2025-01-17T12:00:00.000Z"
}
```

## Testing Tips

1. **Start with Health Check:** Always test `/health` first to ensure the server is running properly.

2. **Use Valid User IDs:** Make sure you have valid user IDs for the platforms you're testing.

3. **Check API Documentation:** Visit `http://localhost:8000/docs` for interactive API documentation.

4. **Monitor Logs:** Watch the server console for detailed execution logs.

5. **Test Different Platforms:** Try queries for YouTube, X, Gmail, Google Ads, and Shopify to test all MCP servers.

## Troubleshooting

- **500 Error:** Check if MCP servers are properly configured and accessible
- **Authentication Errors:** Verify that user IDs are valid and authentication is set up
- **Timeout Errors:** Increase `max_steps` parameter for complex queries
- **Connection Errors:** Ensure all MCP server files are present and executable
