#!/usr/bin/env python3
"""
Minimal YouTube MCP Server for testing
"""

import json
import logging
from typing import Dict, Any

# MCP imports
from mcp.server import Server
from mcp.types import CallToolResult, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = Server("youtube-mcp-minimal")

@mcp.call_tool()
def list_videos(user_id: str):
    """
    Fetch the user's YouTube channel videos with comprehensive details from the YouTube Data API.

    Args:
        user_id (str): The unique identifier for the user whose videos to retrieve.
            This should be a valid user ID that exists in the system.

    Returns:
        dict: A dictionary containing video listing data if successful.
            Example structure:
            {
                "action": "list_videos",
                "user_id": "842a4951-5d0c-40c6-8488-732626d5a3c0",
                "count": 2,
                "videos": [
                    {
                        "video_id": "video_001",
                        "title": "Sample Video 1",
                        "description": "This is a sample video description",
                        "published_at": "2024-01-15T10:00:00Z",
                        "thumbnail": "https://via.placeholder.com/120x90",
                        "view_count": "1500",
                        "like_count": "45"
                    }
                ]
            }
    """
    try:
        user_id = '842a4951-5d0c-40c6-8488-732626d5a3c0'
        videos = call_youtube_api(list_videos_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "list_videos",
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
    """
    Search for videos in the user's YouTube channel using a specific query from the YouTube Data API.

    Args:
        user_id (str): The unique identifier for the user whose channel to search.
            This should be a valid user ID that exists in the system.
        query (str): The search query string to match against video titles and descriptions.
            Examples: "tutorial", "python programming", "cooking tips"

    Returns:
        dict: A dictionary containing search results if successful.
            Example structure:
            {
                "action": "search_videos",
                "user_id": "user-456",
                "query": "tutorial",
                "count": 1,
                "videos": [
                    {
                        "video_id": "video_003",
                        "title": "Video about tutorial",
                        "description": "This video discusses tutorial in detail",
                        "published_at": "2024-01-25T09:15:00Z",
                        "thumbnail": "https://via.placeholder.com/120x90"
                    }
                ]
            }
    """
    try:
        logger.info(f"Searching videos for user: {user_id}, query: {query}")
        
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
        
        result = {
            "action": "search_videos",
            "user_id": user_id,
            "query": query,
            "count": len(mock_videos),
            "videos": mock_videos
        }
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        )
        
    except Exception as e:
        logger.error(f"Error in search_videos: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

@mcp.call_tool()
def get_channel_analytics(user_id: str):
    """
    Retrieve comprehensive analytics and statistics for the user's YouTube channel from the YouTube Data API.

    Args:
        user_id (str): The unique identifier for the user whose channel analytics to retrieve.
            This should be a valid user ID that exists in the system.

    Returns:
        dict: A dictionary containing channel analytics data if successful.
            Example structure:
            {
                "action": "channel_analytics",
                "user_id": "analytics-user-789",
                "analytics": {
                    "channel_id": "UCtest123",
                    "channel_title": "Test Channel",
                    "subscriber_count": "10000",
                    "total_views": "500000",
                    "total_videos": "150"
                }
            }
    """
    try:
        logger.info(f"Getting channel analytics for user: {user_id}")
        
        result = {
            "action": "channel_analytics",
            "user_id": user_id,
            "analytics": {
                "channel_id": "UCtest123",
                "channel_title": "Test Channel",
                "subscriber_count": "10000",
                "total_views": "500000",
                "total_videos": "150"
            }
        }
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        )
        
    except Exception as e:
        logger.error(f"Error in get_channel_analytics: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

if __name__ == "__main__":
    list_videos("842a4951-5d0c-40c6-8488-732626d5a3c0")
    # mcp.run()
