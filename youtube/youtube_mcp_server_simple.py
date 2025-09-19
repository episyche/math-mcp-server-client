#!/usr/bin/env python3
"""
YouTube MCP Server - Simplified version without database dependency
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List

# MCP imports
from mcp.server import Server
from mcp.types import CallToolResult, TextContent

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = Server("youtube-mcp-server-simple")

# Mock credentials for testing - replace with real values
MOCK_CREDENTIALS = {
    "youtube_access_token": "mock_access_token",
    "youtube_channel_id": "UCtest123",
    "client_id": "mock_client_id",
    "client_secret": "mock_client_secret"
}

def get_youtube_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get YouTube credentials for a user (mock implementation)."""
    logger.info(f"Getting credentials for user: {user_id}")
    return MOCK_CREDENTIALS

def list_videos_api(token: str, creds: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List videos from YouTube channel (mock implementation)."""
    logger.info(f"Listing videos for channel: {creds.get('youtube_channel_id')}")
    
    # Mock video data
    mock_videos = [
        {
            "video_id": "video_001",
            "title": "Sample Video 1",
            "description": "This is a sample video description",
            "published_at": "2024-01-15T10:00:00Z",
            "thumbnail": "https://via.placeholder.com/120x90",
            "view_count": "1500",
            "like_count": "45"
        },
        {
            "video_id": "video_002", 
            "title": "Sample Video 2",
            "description": "Another sample video",
            "published_at": "2024-01-20T14:30:00Z",
            "thumbnail": "https://via.placeholder.com/120x90",
            "view_count": "2300",
            "like_count": "67"
        }
    ]
    
    return mock_videos

def search_videos_api(token: str, creds: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Search videos in YouTube channel (mock implementation)."""
    logger.info(f"Searching videos with query: '{query}' for channel: {creds.get('youtube_channel_id')}")
    
    # Mock search results
    mock_videos = [
        {
            "video_id": "video_003",
            "title": f"Video about {query}",
            "description": f"This video discusses {query} in detail",
            "published_at": "2024-01-25T09:15:00Z",
            "thumbnail": "https://via.placeholder.com/120x90"
        }
    ]
    
    return mock_videos

def get_video_details(token: str, video_id: str) -> Dict[str, Any]:
    """Get detailed information about a video (mock implementation)."""
    logger.info(f"Getting details for video: {video_id}")
    
    return {
        "view_count": "5000",
        "like_count": "120",
        "comment_count": "25"
    }

def video_analytics_api(token: str, creds: Dict[str, Any], video_id: str) -> Dict[str, Any]:
    """Get analytics for a specific video (mock implementation)."""
    logger.info(f"Getting analytics for video: {video_id}")
    
    return {
        "video_id": video_id,
        "title": f"Video {video_id}",
        "published_at": "2024-01-15T10:00:00Z",
        "channel_title": "Test Channel",
        "statistics": {
            "viewCount": "5000",
            "likeCount": "120",
            "commentCount": "25"
        },
        "duration": "PT5M30S",
        "description": f"Description for video {video_id}"
    }

def channel_analytics_api(token: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Get analytics for the channel (mock implementation)."""
    logger.info(f"Getting channel analytics for: {creds.get('youtube_channel_id')}")
    
    return {
        "channel_id": creds.get('youtube_channel_id'),
        "channel_title": "Test Channel",
        "subscriber_count": "10000",
        "total_views": "500000",
        "total_videos": "150"
    }

@mcp.call_tool()
def get_user_credentials(user_id: str):
    """Get YouTube credentials for a user."""
    try:
        creds = get_youtube_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No YouTube credentials found for this user."
                )]
            )
        
        safe_info = {
            "user_id": user_id,
            "channel_id": creds.get("youtube_channel_id"),
            "has_access_token": bool(creds.get("youtube_access_token")),
            "has_refresh_token": bool(creds.get("youtube_refresh_token")),
            "has_client_credentials": bool(creds.get("client_id"))
        }
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(safe_info, indent=2, ensure_ascii=False)
            )]
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

@mcp.call_tool()
def list_videos(user_id: str):
    """List videos from the user's YouTube channel."""
    try:
        creds = get_youtube_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No YouTube credentials found for this user."
                )]
            )
        
        videos = list_videos_api(creds.get('youtube_access_token'), creds)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "list_videos",
                    "user_id": user_id,
                    "count": len(videos),
                    "videos": videos
                }, indent=2, ensure_ascii=False)
            )]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

@mcp.call_tool()
def search_videos(user_id: str, query: str):
    """Search videos in the user's YouTube channel."""
    try:
        creds = get_youtube_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No YouTube credentials found for this user."
                )]
            )
        
        videos = search_videos_api(creds.get('youtube_access_token'), creds, query)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "search_videos",
                    "user_id": user_id,
                    "query": query,
                    "count": len(videos),
                    "videos": videos
                }, indent=2, ensure_ascii=False)
            )]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

@mcp.call_tool()
def get_video_analytics(user_id: str, video_id: str):
    """Get analytics for a specific video."""
    try:
        creds = get_youtube_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No YouTube credentials found for this user."
                )]
            )
        
        analytics = video_analytics_api(creds.get('youtube_access_token'), creds, video_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "video_analytics",
                    "user_id": user_id,
                    "video_id": video_id,
                    "analytics": analytics
                }, indent=2, ensure_ascii=False)
            )]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

@mcp.call_tool()
def get_channel_analytics(user_id: str):
    """Get analytics for the user's YouTube channel."""
    try:
        creds = get_youtube_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No YouTube credentials found for this user."
                )]
            )
        
        analytics = channel_analytics_api(creds.get('youtube_access_token'), creds)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "channel_analytics",
                    "user_id": user_id,
                    "analytics": analytics
                }, indent=2, ensure_ascii=False)
            )]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await mcp.run(read_stream, write_stream, None)
    
    asyncio.run(main())
