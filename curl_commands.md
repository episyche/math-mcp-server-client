# Curl Commands for MCP HTTP Server Streaming

## Quick Reference

**Server URL:** `http://localhost:8001`

## 1. Basic Streaming Test

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8001/query/stream?query=Hello, this is a test query&user_id=test-user-123&max_steps=5"
```

## 2. YouTube Video Listing (Streaming)

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8001/query/stream?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0&max_steps=10"
```

## 3. Gmail Unread Emails (Streaming)

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8001/query/stream?query=get my unread emails&user_id=your-gmail-user-id&max_steps=8"
```

## 4. X (Twitter) Post Creation (Streaming)

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8001/query/stream?query=create a post saying 'Hello from MCP HTTP Server!'&user_id=your-x-user-id&max_steps=6"
```

## 5. Shopify Store Analytics (Streaming)

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8001/query/stream?query=get my store analytics and statistics&user_id=your-shopify-user-id&max_steps=10"
```

## 6. Health Check

```bash
curl "http://localhost:8001/health"
```

## 7. Server Info

```bash
curl "http://localhost:8001/"
```

## 8. Non-Streaming POST Request

```bash
curl -X POST "http://localhost:8001/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "get all my videos in youtube",
    "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0",
    "max_steps": 10
  }'
```

## 9. Non-Streaming GET Request

```bash
curl "http://localhost:8001/query?query=get all my videos in youtube&user_id=842a4951-5d0c-40c6-8488-732626d5a3c0&max_steps=10"
```

## Curl Options Explained

- `-N`: Disable buffering (important for streaming)
- `-H "Accept: text/event-stream"`: Set proper headers for SSE
- `-X POST`: Specify HTTP method
- `-H "Content-Type: application/json"`: Set content type for JSON body
- `-d '{...}'`: Send JSON data in request body

## Expected Streaming Response Format

```
data: {"type": "status", "message": "Starting MCP query...", "timestamp": "2025-01-17T12:00:00.000Z"}

data: {"type": "result", "data": {...}, "timestamp": "2025-01-17T12:00:00.000Z"}

data: {"type": "complete", "message": "Query completed successfully", "timestamp": "2025-01-17T12:00:00.000Z"}
```

## Error Response Format

```
data: {"type": "error", "message": "Error details here", "timestamp": "2025-01-17T12:00:00.000Z"}
```

## Tips

1. **Use Ctrl+C** to stop streaming responses
2. **Replace user IDs** with actual ones for real testing
3. **Check server logs** for detailed execution information
4. **URL encode** special characters in query parameters
5. **Increase max_steps** for complex queries that might need more processing time
