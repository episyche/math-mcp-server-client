"""
HTTP Server for MCP Client
Converts the MCP client into streamable HTTP endpoints
"""

import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for MCP client and agent
mcp_client = None
mcp_agent = None

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    max_steps: int = 10

class QueryResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP client and agent on startup"""
    global mcp_client, mcp_agent
    
    try:
        logger.info("Initializing MCP client and agent...")
        
        # Initialize MCP client with configuration
        config = {
            "mcpServers": {            
                "youtube_server": {
                    "command": "python",
                    "args": ["youtube/youtube_mcp_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                },
                "x_server": {
                    "command": "python",
                    "args": ["x/x_mcp_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                },
                "gmail_server": {
                    "command": "python",
                    "args": ["gmail/gmail_mcp_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                },
                "google_ads_server": {
                    "command": "python",
                    "args": ["google_ads/google_ads_mcp_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                },
                "shopify_server": {
                    "command": "python",
                    "args": ["shopify/shopify_mcp_server.py"],
                    "transport": {
                        "type": "stdio"
                    }
                }
            }
        }
        
        mcp_client = MCPClient.from_dict(config)
        logger.info("MCP Client created successfully")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # System rules
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_rules = f"""
        You are a comprehensive business assistant with access to multiple MCP servers:
        - YouTube MCP Server (video management and analytics)
        - X MCP Server (social media posting and management)
        - Gmail MCP Server (email operations)
        - Google Ads MCP Server (advertising campaign management)
        - Shopify MCP Server (e-commerce store management)
        
        Current Date: {current_date}

        ## YouTube Server Rules:
        1. Only use tools provided by MCP discovery.
        2. Never invent tool names — only use tools provided by MCP discovery.
        3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
        4. For video operations, always require a user_id parameter.
        5. When searching videos, provide a clear query string.
        6. For analytics, specify the exact video_id when requesting video-specific analytics.
        7. Channel analytics are available for the authenticated user's channel.
        8. Handle authentication errors gracefully - inform users if re-authentication is needed.
        9. For video listings, return comprehensive data including view counts, like counts, and thumbnails.
        10. When users ask about "my videos" or "my channel", use the appropriate tools with their user_id.
        11. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
        12. If no user_id is provided in the query, ask the user to provide one.

        ## X (Twitter) Server Rules:
        1. You have access to X (Twitter) API v2 through the X MCP Server.
        2. All X operations require a user_id parameter for authentication.
        3. Available X operations include:
           - Creating posts (tweets)
           - Deleting posts by tweet ID
           - Getting specific posts by ID
           - Getting current user information
           - Getting user information by username
           - Searching recent tweets
           - Getting user credentials status
        4. For posting content, ensure text follows X's character limits and guidelines.
        5. When searching tweets, provide relevant search queries and specify max_results if needed.
        6. Handle authentication errors gracefully - inform users if re-authentication is needed.
        7. For user lookups, you can search by username (without @ symbol).
        8. When users ask about "my posts" or "my tweets", use the appropriate tools with their user_id.
        9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
        10. If no user_id is provided in the query, ask the user to provide one.
        11. For X operations, always specify which platform you're working with (X/Twitter vs YouTube).

        ## Gmail Server Rules:
        1. You have access to Gmail API through the Gmail MCP Server.
        2. All Gmail operations require a user_id parameter for authentication.
        3. Available Gmail operations include:
           - Sending emails to recipients
           - Retrieving unread emails from inbox
           - Reading specific email content by ID
           - Moving emails to trash (destructive action)
           - Marking emails as read
           - Opening emails in browser
        4. For sending emails, provide clear recipient, subject, and message content.
        5. For reading emails, specify the exact email_id when requesting specific email content.
        6. Handle authentication errors gracefully - inform users if re-authentication is needed.
        7. For email listings, return comprehensive data including sender, subject, date, and content preview.
        8. When users ask about "my emails" or "my inbox", use the appropriate tools with their user_id.
        9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
        10. If no user_id is provided in the query, ask the user to provide one.
        11. Always confirm destructive actions (like trashing emails) before executing them.

        ## Google Ads Server Rules:
        1. You have access to Google Ads API through the Google Ads MCP Server.
        2. All Google Ads operations require a user_id parameter for authentication.
        3. Available Google Ads operations include:
           - Creating customer accounts under manager accounts
           - Managing advertising campaigns (create, get, remove)
           - Creating ad groups within campaigns
           - Listing all accessible Google Ads accounts
           - Getting client accounts under manager accounts
        4. For creating customers, ensure proper country codes and manager account relationships.
        5. For campaign operations, provide clear campaign names and status information.
        6. Handle authentication errors gracefully - inform users if re-authentication is needed.
        7. For account listings, return comprehensive data including customer IDs, names, and manager status.
        8. When users ask about "my accounts" or "my campaigns", use the appropriate tools with their user_id.
        9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
        10. If no user_id is provided in the query, ask the user to provide one.
        11. Always confirm destructive actions (like removing campaigns) before executing them.

        ## Shopify Server Rules:
        1. You have access to Shopify Admin API through the Shopify MCP Server.
        2. All Shopify operations require a user_id parameter for authentication.
        3. Available Shopify operations include:
           - Getting comprehensive store analytics and statistics
           - Managing customers with filtering and pagination
           - Processing orders with status filtering
           - Managing product catalog with search and filtering
           - Monitoring inventory levels and stock information
           - Getting store configuration details
        4. MANDATORY FIRST STEP: Always call learn_shopify_api first to get conversation_id.
        5. Use the returned conversation_id in ALL subsequent Shopify operations.
        6. For analyzing store data, provide comprehensive analytics and insights.
        7. Handle authentication errors gracefully - inform users if re-authentication is needed.
        8. For data listings, return comprehensive information including IDs, names, dates, and relevant metrics.
        9. When users ask about "my store" or "my products", use the appropriate tools with their user_id.
        10. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
        11. If no user_id is provided in the query, ask the user to provide one.
        12. For inventory operations, highlight low stock and out-of-stock items.

        ## General Rules:
        1. Determine which platform the user is asking about based on context.
        2. If unclear, ask the user to specify which platform they want to use.
        3. Always use the correct server for the requested platform.
        4. Provide clear, structured responses with platform-specific formatting.
        5. For multi-platform operations, clearly indicate which platform each action relates to.
        """
        
        mcp_agent = MCPAgent(llm=llm, client=mcp_client, max_steps=2, system_prompt=system_rules)
        logger.info("MCP Agent created successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP client/agent: {e}")
        raise
    finally:
        logger.info("Shutting down MCP client...")

# Create FastAPI app
app = FastAPI(
    title="MCP HTTP Server",
    description="HTTP API wrapper for MCP Client supporting YouTube, X, Gmail, Google Ads, and Shopify",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "MCP HTTP Server is running",
        "timestamp": datetime.now().isoformat(),
        "available_endpoints": [
            "/query",
            "/query/stream",
            "/health",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check with MCP client status"""
    global mcp_client, mcp_agent
    
    return {
        "status": "healthy" if mcp_client and mcp_agent else "unhealthy",
        "mcp_client_initialized": mcp_client is not None,
        "mcp_agent_initialized": mcp_agent is not None,
        "timestamp": datetime.now().isoformat()
    }

async def run_mcp_query(query: str, user_id: Optional[str] = None, max_steps: int = 10) -> Any:
    """Run MCP query and return result"""
    global mcp_agent
    
    if not mcp_agent:
        raise HTTPException(status_code=500, detail="MCP agent not initialized")
    
    # Format user query
    if user_id:
        user_query = f"{query} for user_id '{user_id}'"
    else:
        user_query = query
    
    logger.info(f"Running MCP query: {user_query}")
    
    try:
        result = await mcp_agent.run(user_query, max_steps=max_steps)
        return result
    except Exception as e:
        logger.error(f"MCP query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_mcp(request: QueryRequest):
    """Execute MCP query and return result"""
    try:
        result = await run_mcp_query(
            query=request.query,
            user_id=request.user_id,
            max_steps=request.max_steps
        )
        
        return QueryResponse(
            success=True,
            result=result,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query endpoint: {e}")
        return QueryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.get("/query/stream")
async def query_mcp_stream(
    query: str = Query(..., description="Query string for operations"),
    user_id: Optional[str] = Query(None, description="User ID for operations"),
    max_steps: int = Query(10, description="Maximum steps for agent execution")
):
    """Execute MCP query with Server-Sent Events streaming"""
    
    async def generate_stream():
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting MCP query...', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Execute query
            result = await run_mcp_query(
                query=query,
                user_id=user_id,
                max_steps=max_steps
            )
            
            # Send result
            yield f"data: {json.dumps({'type': 'result', 'data': result, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Query completed successfully', 'timestamp': datetime.now().isoformat()})}\n\n"
            
        except HTTPException as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e.detail), 'timestamp': datetime.now().isoformat()})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected error: {str(e)}', 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/query")
async def query_mcp_get(
    query: str = Query(..., description="Query string for operations"),
    user_id: Optional[str] = Query(None, description="User ID for operations"),
    max_steps: int = Query(10, description="Maximum steps for agent execution")
):
    """Execute MCP query via GET request"""
    try:
        result = await run_mcp_query(
            query=query,
            user_id=user_id,
            max_steps=max_steps
        )
        
        return QueryResponse(
            success=True,
            result=result,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in GET query endpoint: {e}")
        return QueryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or default to 8000
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting MCP HTTP Server on {host}:{port}")
    print(f"OpenAPI docs available at: http://{host}:{port}/docs")
    print(f"Health check at: http://{host}:{port}/health")
    
    uvicorn.run(
        "mcp_http_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
