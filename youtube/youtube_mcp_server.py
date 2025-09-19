#!/usr/bin/env python3
"""
YouTube MCP Server - Simple version
"""
import asyncio
import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

# MCP imports
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import common database utilities
import sys
import os
# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from db_utils import get_youtube_minion_credentials, update_youtube_token_in_db, update_youtube_tokens_in_db

# Initialize MCP server
mcp = FastMCP("youtube-mcp-server")

def get_youtube_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get YouTube credentials for a user."""
    return get_youtube_minion_credentials(user_id)

def refresh_youtube_token(user_id: str) -> Optional[str]:
    """Refresh YouTube access token using refresh token from database."""
    url = "https://oauth2.googleapis.com/token"
    
    # Get credentials from database
    creds = get_youtube_credentials(user_id)
    if not creds:
        logger.error("❌ No YouTube credentials found in database")
        return None
    
    # Extract credentials from the database structure
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    refresh_token_val = creds.get("youtube_refresh_token")
    
    # Validate required fields
    if not client_id:
        logger.error("❌ YOUTUBE_CLIENT_ID is missing from database")
        return None
    if not client_secret:
        logger.error("❌ YOUTUBE_CLIENT_SECRET is missing from database")
        return None
    if not refresh_token_val:
        logger.error("❌ YOUTUBE_REFRESH_TOKEN is missing from database")
        return None
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token_val,
        "grant_type": "refresh_token",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(url, data=data, headers=headers, timeout=30)
    if response.status_code == 200:
        new_token = response.json().get("access_token")
        
        # Update in database
        if update_youtube_token_in_db(user_id, new_token):
            logger.info("✅ Refreshed token and updated database")
        else:
            logger.warning("Could not update database with new token")
        
        return new_token
    else:
        error_response = response.json()
        logger.error("❌ Failed to refresh token: %s", error_response)
        
        # If refresh token is invalid, we need to create a new one
        if error_response.get("error") == "invalid_grant":
            logger.warning("🔄 Refresh token is invalid, will need to create new token")
            return None
        
        return None

def call_youtube_api(api_func, user_id: str):
    """Wrapper to call YouTube API with automatic token refresh if needed."""
    creds = get_youtube_credentials(user_id)
    print(creds, '==========')
    if not creds:
        raise RuntimeError(f"No active YouTube minion found for user {user_id}")
    
    token = creds.get('youtube_access_token')
    if not token:
        raise RuntimeError("No YouTube access token available")
    
    try:
        return api_func(token, creds)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token expired, try to refresh
            new_token = refresh_youtube_token(user_id)
            if new_token:
                # Update the token in the database
                if update_youtube_token_in_db(user_id, new_token):
                    # Update the token in the credentials for this session
                    creds['youtube_access_token'] = new_token
                    # Try the API call again with the new token
                    return api_func(new_token, creds)
                else:
                    raise RuntimeError("Token refreshed but failed to update database")
            else:
                raise RuntimeError("Token expired and refresh failed. User needs to re-authenticate.")
        elif e.response.status_code == 403:
            # Forbidden - might be quota exceeded or insufficient permissions
            error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
            error_reason = error_data.get('error', {}).get('message', 'Unknown error')
            raise RuntimeError(f"YouTube API access forbidden: {error_reason}")
        elif e.response.status_code == 429:
            # Rate limit exceeded
            raise RuntimeError("YouTube API rate limit exceeded. Please try again later.")
        else:
            raise e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling YouTube API: {str(e)}")
    except Exception as e:
        raise e

def list_videos_api(token: str, creds: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List videos from YouTube channel."""
    channel_id = creds.get('youtube_channel_id')
    if not channel_id:
        raise RuntimeError("No YouTube channel ID found")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": 50
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    videos = []
    
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        
        # Get additional video details
        video_details = get_video_details(token, video_id)
        
        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "description": snippet["description"],
            "published_at": snippet["publishedAt"],
            "thumbnail": snippet["thumbnails"]["default"]["url"],
            "view_count": video_details.get("view_count", "N/A"),
            "like_count": video_details.get("like_count", "N/A")
        })
    
    return videos

def search_videos_api(token: str, creds: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Search videos in YouTube channel."""
    channel_id = creds.get('youtube_channel_id')
    if not channel_id:
        raise RuntimeError("No YouTube channel ID found")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "q": query,
        "type": "video",
        "order": "relevance",
        "maxResults": 20
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    videos = []
    
    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        
        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "description": snippet["description"],
            "published_at": snippet["publishedAt"],
            "thumbnail": snippet["thumbnails"]["default"]["url"]
        })
    
    return videos

def get_video_details(token: str, video_id: str) -> Dict[str, Any]:
    """Get detailed information about a video."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics",
        "id": video_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("items"):
            stats = data["items"][0].get("statistics", {})
            return {
                "view_count": stats.get("viewCount", "0"),
                "like_count": stats.get("likeCount", "0"),
                "comment_count": stats.get("commentCount", "0")
            }
    except Exception as e:
        logger.warning(f"Could not fetch video details for {video_id}: {e}")
    
    return {"view_count": "N/A", "like_count": "N/A", "comment_count": "N/A"}

def video_analytics_api(token: str, creds: Dict[str, Any], video_id: str) -> Dict[str, Any]:
    """Get analytics for a specific video."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    if not data.get("items"):
        raise RuntimeError(f"Video {video_id} not found")
    
    item = data["items"][0]
    return {
        "video_id": video_id,
        "title": item["snippet"]["title"],
        "published_at": item["snippet"]["publishedAt"],
        "channel_title": item["snippet"]["channelTitle"],
        "statistics": item.get("statistics", {}),
        "duration": item.get("contentDetails", {}).get("duration", ""),
        "description": item["snippet"]["description"]
    }

def channel_analytics_api(token: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Get analytics for the channel."""
    channel_id = creds.get('youtube_channel_id')
    if not channel_id:
        raise RuntimeError("No YouTube channel ID found")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics",
        "id": channel_id
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    if not data.get("items"):
        raise RuntimeError(f"Channel {channel_id} not found")
    
    item = data["items"][0]
    return {
        "channel_id": channel_id,
        "channel_title": item["snippet"]["title"],
        "subscriber_count": item["statistics"].get("subscriberCount", "0"),
        "total_views": item["statistics"].get("viewCount", "0"),
        "total_videos": item["statistics"].get("videoCount", "0")
    }

@mcp.tool()
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

@mcp.tool()
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
        videos = call_youtube_api(list_videos_api, user_id)
        print(videos, '==========')
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

@mcp.tool()
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
        videos = call_youtube_api(lambda token, creds: search_videos_api(token, creds, query), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "search_videos",
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

@mcp.tool()
def get_video_analytics(user_id: str, video_id: str):
    """
    Retrieve detailed analytics and statistics for a specific video from the YouTube Data API.

    Args:
        user_id (str): The unique identifier for the user whose video analytics to retrieve.
            This should be a valid user ID that exists in the system.
        video_id (str): The unique identifier of the video to get analytics for.
            This should be a valid YouTube video ID.

    Returns:
        dict: A dictionary containing video analytics data if successful.
            Example structure:
            {
                "action": "video_analytics",
                "user_id": "user-123",
                "video_id": "video_001",
                "analytics": {
                    "video_id": "video_001",
                    "title": "Sample Video 1",
                    "published_at": "2024-01-15T10:00:00Z",
                    "channel_title": "Test Channel",
                    "statistics": {
                        "viewCount": "5000",
                        "likeCount": "120",
                        "commentCount": "25"
                    },
                    "duration": "PT5M30S",
                    "description": "Description for video 001"
                }
            }
    """
    try:
        analytics = call_youtube_api(lambda token, creds: video_analytics_api(token, creds, video_id), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "video_analytics",
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

@mcp.tool()
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
        analytics = call_youtube_api(channel_analytics_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "channel_analytics",
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
    asyncio.run(mcp.run())
