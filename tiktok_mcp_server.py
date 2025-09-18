#!/usr/bin/env python3
"""
TikTok MCP Server with Database Credential Management
Provides TikTok API functionality with credentials stored in database
"""

from __future__ import annotations
import os
import requests
import logging
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Import database utilities
from db_utils import get_user_credentials, update_tokens_in_db, test_database_connection

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("TikTokServer")

mcp = FastMCP("TikTokServer")

# Global variables for API key management
USE_MOCK_DATA = True
TIKNEURON_MCP_API_KEY = None

def get_tiktok_api_key(user_id: str) -> Optional[str]:
    """Get TikTok API key from database for a specific user."""
    try:
        credentials = get_user_credentials(user_id, "tiktok")
        if credentials:
            api_key = credentials.get('tiktok_api_key')
            if api_key and api_key.strip():
                logger.info(f"Found TikTok API key for user {user_id}: {api_key[:10]}...")
                return api_key
            else:
                logger.warning(f"TikTok API key is empty or None for user {user_id}")
        else:
            logger.warning(f"No TikTok credentials found for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting TikTok API key for user {user_id}: {e}")
        return None

def update_tiktok_api_key(user_id: str, api_key: str) -> bool:
    """Update TikTok API key in database for a specific user."""
    try:
        return update_tokens_in_db(user_id, "tiktok", api_key)
    except Exception as e:
        logger.error(f"Error updating TikTok API key for user {user_id}: {e}")
        return False

def check_database_connection() -> bool:
    """Check if database connection is available."""
    try:
        return test_database_connection()
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

@mcp.tool()
def tiktok_search(query: str, user_id: str, cursor: Optional[str] = None, search_uid: Optional[str] = None) -> str:
    """
    Search for TikTok videos based on a query using user's stored credentials.
    
    Args:
        query: Search query for TikTok videos, e.g., 'funny cats', 'dance', 'cooking tutorial'
        user_id: User ID to retrieve stored TikTok API credentials
        cursor: Pagination cursor for getting more results (optional)
        search_uid: Search session identifier for pagination (optional)
    
    Returns:
        A list of videos matching the search criteria with their details
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Get API key from database
        api_key = get_tiktok_api_key(user_id)
        
        if not api_key:
            # Return mock data when API key is not available
            result = f"""MOCK TIKTOK SEARCH RESULTS for '{query}':
==================================================

Video 1:
Description: Amazing {query} video compilation
Video ID: 7234567890123456789
Creator: @tiktoker1
Hashtags: {query.replace(' ', '')}, viral, trending
Likes: 125.3K
Shares: 8.2K
Comments: 3.1K
Views: 2.1M
Bookmarks: 15.6K
Created at: 2024-01-15T10:30:00Z
Duration: 45 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 2:
Description: Best {query} moments you need to see
Video ID: 7234567890123456790
Creator: @creator_pro
Hashtags: {query.replace(' ', '')}, fyp, viral
Likes: 89.7K
Shares: 5.4K
Comments: 2.8K
Views: 1.5M
Bookmarks: 12.1K
Created at: 2024-01-14T15:45:00Z
Duration: 32 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 3:
Description: Incredible {query} compilation - must watch!
Video ID: 7234567890123456791
Creator: @viral_content
Hashtags: {query.replace(' ', '')}, amazing, mustwatch
Likes: 203.5K
Shares: 12.8K
Comments: 5.7K
Views: 3.2M
Bookmarks: 28.9K
Created at: 2024-01-13T09:20:00Z
Duration: 58 seconds
Available subtitles: English (auto-generated), Spanish (community)

Search Metadata:
Cursor: mock_cursor_{hash(query) % 10000}
Has more results: Yes
Search UID: mock_uid_{hash(query) % 10000}

NOTE: This is MOCK DATA for testing. To get real TikTok data:
1. Configure TikTok API key in database for user {user_id}
2. Use update_tiktok_credentials tool to set your API key"""
            
            return result
        
        # Use real API when key is available
        try:
            url = 'https://tikneuron.com/api/mcp/search'
            params = {'query': query}
            
            if cursor:
                params['cursor'] = cursor
            if search_uid:
                params['search_uid'] = search_uid

            response = requests.get(url, params=params, headers={
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'MCP-API-KEY': api_key,
            }, timeout=10)

            if not response.ok:
                logger.warning(f"TikNeuron API error: {response.status_code} {response.reason}. Falling back to mock data.")
                # Fall back to mock data when API fails
                return f"""MOCK TIKTOK SEARCH RESULTS for '{query}':
==================================================

Video 1:
Description: Amazing {query} video compilation
Video ID: 7234567890123456789
Creator: @tiktoker1
Hashtags: {query.replace(' ', '')}, viral, trending
Likes: 125.3K
Shares: 8.2K
Comments: 3.1K
Views: 2.1M
Bookmarks: 15.6K
Created at: 2024-01-15T10:30:00Z
Duration: 45 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 2:
Description: Best {query} moments you need to see
Video ID: 7234567890123456790
Creator: @creator_pro
Hashtags: {query.replace(' ', '')}, fyp, viral
Likes: 89.7K
Shares: 5.4K
Comments: 2.8K
Views: 1.5M
Bookmarks: 12.1K
Created at: 2024-01-14T15:45:00Z
Duration: 32 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 3:
Description: Incredible {query} compilation - must watch!
Video ID: 7234567890123456791
Creator: @viral_content
Hashtags: {query.replace(' ', '')}, amazing, mustwatch
Likes: 203.5K
Shares: 12.8K
Comments: 5.7K
Views: 3.2M
Bookmarks: 28.9K
Created at: 2024-01-13T09:20:00Z
Duration: 58 seconds
Available subtitles: English (auto-generated), Spanish (community)

Search Metadata:
Cursor: mock_cursor_{hash(query) % 10000}
Has more results: Yes
Search UID: mock_uid_{hash(query) % 10000}

NOTE: This is MOCK DATA due to API error. To get real TikTok data:
1. Check your TikTok API key in database for user {user_id}
2. Use update_tiktok_credentials tool to set a valid API key"""

            data = response.json()
        except Exception as api_error:
            logger.warning(f"TikNeuron API call failed: {api_error}. Falling back to mock data.")
            # Fall back to mock data when API call fails
            return f"""MOCK TIKTOK SEARCH RESULTS for '{query}':
==================================================

Video 1:
Description: Amazing {query} video compilation
Video ID: 7234567890123456789
Creator: @tiktoker1
Hashtags: {query.replace(' ', '')}, viral, trending
Likes: 125.3K
Shares: 8.2K
Comments: 3.1K
Views: 2.1M
Bookmarks: 15.6K
Created at: 2024-01-15T10:30:00Z
Duration: 45 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 2:
Description: Best {query} moments you need to see
Video ID: 7234567890123456790
Creator: @creator_pro
Hashtags: {query.replace(' ', '')}, fyp, viral
Likes: 89.7K
Shares: 5.4K
Comments: 2.8K
Views: 1.5M
Bookmarks: 12.1K
Created at: 2024-01-14T15:45:00Z
Duration: 32 seconds
Available subtitles: English (auto-generated), Spanish (community)

Video 3:
Description: Incredible {query} compilation - must watch!
Video ID: 7234567890123456791
Creator: @viral_content
Hashtags: {query.replace(' ', '')}, amazing, mustwatch
Likes: 203.5K
Shares: 12.8K
Comments: 5.7K
Views: 3.2M
Bookmarks: 28.9K
Created at: 2024-01-13T09:20:00Z
Duration: 58 seconds
Available subtitles: English (auto-generated), Spanish (community)

Search Metadata:
Cursor: mock_cursor_{hash(query) % 10000}
Has more results: Yes
Search UID: mock_uid_{hash(query) % 10000}

NOTE: This is MOCK DATA due to API error. To get real TikTok data:
1. Check your TikTok API key in database for user {user_id}
2. Use update_tiktok_credentials tool to set a valid API key"""
        
        if data.get('videos') and len(data['videos']) > 0:
            videos_list = []
            for i, video in enumerate(data['videos']):
                video_info = f"Video {i + 1}:\n"
                video_info += f"Description: {video.get('description', 'N/A')}\n"
                video_info += f"Video ID: {video.get('video_id', 'N/A')}\n"
                video_info += f"Creator: {video.get('creator', 'N/A')}\n"
                video_info += f"Hashtags: {', '.join(video.get('hashtags', [])) if video.get('hashtags') else 'N/A'}\n"
                video_info += f"Likes: {video.get('likes', '0')}\n"
                video_info += f"Shares: {video.get('shares', '0')}\n"
                video_info += f"Comments: {video.get('comments', '0')}\n"
                video_info += f"Views: {video.get('views', '0')}\n"
                video_info += f"Bookmarks: {video.get('bookmarks', '0')}\n"
                video_info += f"Created at: {video.get('created_at', 'N/A')}\n"
                video_info += f"Duration: {video.get('duration', 0)} seconds\n"
                
                available_subtitles = video.get('available_subtitles', [])
                if available_subtitles:
                    subtitle_info = []
                    for sub in available_subtitles:
                        subtitle_info.append(f"{sub.get('language', 'Unknown')} ({sub.get('source', 'Unknown source')})")
                    video_info += f"Available subtitles: {', '.join(subtitle_info)}\n"
                else:
                    video_info += "Available subtitles: None\n"
                
                videos_list.append(video_info)

            result = '\n\n'.join(videos_list)
            
            if data.get('metadata'):
                metadata = data['metadata']
                result += f"\n\nSearch Metadata:\n"
                result += f"Cursor: {metadata.get('cursor', 'N/A')}\n"
                result += f"Has more results: {'Yes' if metadata.get('has_more') else 'No'}\n"
                result += f"Search UID: {metadata.get('search_uid', 'N/A')}"
            
            return result
        else:
            return 'No videos found for the search query'
            
    except Exception as e:
        logger.error(f"Error in tiktok_search: {e}")
        return f"Error searching TikTok videos: {str(e)}"

@mcp.tool()
def tiktok_get_post_details(tiktok_url: str, user_id: str) -> str:
    """
    Get the details of a TikTok post using user's stored credentials.
    
    Args:
        tiktok_url: TikTok video URL, e.g., https://www.tiktok.com/@username/video/1234567890 
                   or https://vm.tiktok.com/1234567890, or just the video ID like 7409731702890827041
        user_id: User ID to retrieve stored TikTok API credentials
    
    Returns:
        The details of the video including description, creator, hashtags, engagement metrics, etc.
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Get API key from database
        api_key = get_tiktok_api_key(user_id)
        
        if not api_key:
            # Return mock data when API key is not available
            mock_id = tiktok_url.split('/')[-1] if '/' in tiktok_url else "mock_video_id"
            
            result = f"""MOCK POST DETAILS for {tiktok_url}:
========================================
Description: Amazing content from {mock_id}
Video ID: {mock_id}
Creator: @mock_creator
Hashtags: #viral, #trending, #fyp
Likes: 156.2K
Shares: 9.8K
Comments: 4.3K
Views: 2.8M
Bookmarks: 18.7K
Created at: 2024-01-15T12:00:00Z
Duration: 42 seconds
Available subtitles: English (auto-generated), Spanish (community)

NOTE: This is MOCK DATA for testing purposes.
Configure TikTok API key in database for user {user_id} for real data."""
            
            return result
        
        # Use real API when key is available
        url = 'https://tikneuron.com/api/mcp/post-detail'
        params = {'tiktok_url': tiktok_url}

        response = requests.get(url, params=params, headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'MCP-API-KEY': api_key,
        })

        if not response.ok:
            raise Exception(f"TikNeuron API error: {response.status_code} {response.reason}")

        data = response.json()
        
        if data.get('details'):
            details = data['details']
            result = f"Description: {details.get('description', 'N/A')}\n"
            result += f"Video ID: {details.get('video_id', 'N/A')}\n"
            result += f"Creator: {details.get('creator', 'N/A')}\n"
            result += f"Hashtags: {', '.join(details.get('hashtags', [])) if details.get('hashtags') else 'N/A'}\n"
            result += f"Likes: {details.get('likes', '0')}\n"
            result += f"Shares: {details.get('shares', '0')}\n"
            result += f"Comments: {details.get('comments', '0')}\n"
            result += f"Views: {details.get('views', '0')}\n"
            result += f"Bookmarks: {details.get('bookmarks', '0')}\n"
            result += f"Created at: {details.get('created_at', 'N/A')}\n"
            result += f"Duration: {details.get('duration', 0)} seconds\n"
            
            available_subtitles = details.get('available_subtitles', [])
            if available_subtitles:
                subtitle_info = []
                for sub in available_subtitles:
                    subtitle_info.append(f"{sub.get('language', 'Unknown')} ({sub.get('source', 'Unknown source')})")
                result += f"Available subtitles: {', '.join(subtitle_info)}"
            else:
                result += "Available subtitles: None"
            
            return result
        else:
            return 'No details available'
            
    except Exception as e:
        logger.error(f"Error in tiktok_get_post_details: {e}")
        return f"Error getting TikTok post details: {str(e)}"

@mcp.tool()
def tiktok_get_subtitle(tiktok_url: str, user_id: str, language_code: Optional[str] = None) -> str:
    """
    Get the subtitle (content) for a TikTok video using user's stored credentials.
    
    Args:
        tiktok_url: TikTok video URL, e.g., https://www.tiktok.com/@username/video/1234567890 
                   or https://vm.tiktok.com/1234567890, or just the video ID like 7409731702890827041
        user_id: User ID to retrieve stored TikTok API credentials
        language_code: Language code for the subtitle, e.g., en for English, es for Spanish, fr for French, etc.
    
    Returns:
        The subtitle for the video in the requested language and format
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Get API key from database
        api_key = get_tiktok_api_key(user_id)
        
        if not api_key:
            # Return mock data when API key is not available
            mock_id = tiktok_url.split('/')[-1] if '/' in tiktok_url else 'content'
            
            result = f"""MOCK SUBTITLE for {tiktok_url}:

Hello everyone! Welcome to this amazing video about {mock_id}. This is a mock subtitle for testing purposes.

Language: {language_code if language_code else 'English (default)'}

To get real subtitles, please configure TikTok API key in database for user {user_id}."""
            
            return result
        
        # Use real API when key is available
        url = 'https://tikneuron.com/api/mcp/get-subtitles'
        params = {'tiktok_url': tiktok_url}
        
        if language_code:
            params['language_code'] = language_code

        response = requests.get(url, params=params, headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'MCP-API-KEY': api_key,
        })

        if not response.ok:
            raise Exception(f"TikNeuron API error: {response.status_code} {response.reason}")

        data = response.json()
        return data.get('subtitle_content', 'No subtitle available')
        
    except Exception as e:
        logger.error(f"Error in tiktok_get_subtitle: {e}")
        return f"Error getting TikTok subtitle: {str(e)}"

@mcp.tool()
def update_tiktok_credentials(user_id: str, api_key: str) -> str:
    """
    Update TikTok API credentials in the database for a specific user.
    
    Args:
        user_id: User ID to update credentials for
        api_key: TikTok API key from TikNeuron
    
    Returns:
        Success or error message
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Validate API key format (basic validation)
        if not api_key or len(api_key) < 10:
            return "Error: Invalid API key format. Please provide a valid TikNeuron API key."
        
        # Update API key in database
        success = update_tiktok_api_key(user_id, api_key)
        
        if success:
            return f"Successfully updated TikTok API credentials for user {user_id}"
        else:
            return f"Error: Failed to update TikTok API credentials for user {user_id}. Please check if the user exists and has an active TikTok minion."
            
    except Exception as e:
        logger.error(f"Error updating TikTok credentials: {e}")
        return f"Error updating TikTok credentials: {str(e)}"

@mcp.tool()
def get_tiktok_credentials_status(user_id: str) -> str:
    """
    Check the status of TikTok credentials for a specific user.
    
    Args:
        user_id: User ID to check credentials for
    
    Returns:
        Status information about the user's TikTok credentials
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Get credentials from database
        credentials = get_user_credentials(user_id, "tiktok")
        
        if not credentials:
            return f"No TikTok minion found for user {user_id}. Please ensure the user has an active TikTok minion configured."
        
        api_key = credentials.get('tiktok_api_key')
        minion_name = credentials.get('minion_name', 'Unknown')
        agent_name = credentials.get('agent_masteragent_name', 'Unknown')
        
        if api_key:
            # Mask the API key for security
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            return f"""TikTok Credentials Status for User {user_id}:
==========================================
Status: ✅ Configured
Minion Name: {minion_name}
Agent Name: {agent_name}
API Key: {masked_key}
Database: Connected"""
        else:
            return f"""TikTok Credentials Status for User {user_id}:
==========================================
Status: ❌ Not Configured
Minion Name: {minion_name}
Agent Name: {agent_name}
API Key: Not set
Database: Connected

Use update_tiktok_credentials tool to set your API key."""
            
    except Exception as e:
        logger.error(f"Error checking TikTok credentials status: {e}")
        return f"Error checking TikTok credentials status: {str(e)}"

@mcp.tool()
def test_tiktok_connection(user_id: str) -> str:
    """
    Test the TikTok API connection using user's stored credentials.
    
    Args:
        user_id: User ID to test connection for
    
    Returns:
        Connection test results
    """
    try:
        # Check database connection
        if not check_database_connection():
            return "Error: Database connection unavailable. Please check your database configuration."
        
        # Get API key from database
        api_key = get_tiktok_api_key(user_id)
        
        if not api_key:
            return f"Error: No TikTok API key found for user {user_id}. Please configure your API key first."
        
        # Test API connection with a simple search
        url = 'https://tikneuron.com/api/mcp/search'
        params = {'query': 'test'}
        
        response = requests.get(url, params=params, headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'MCP-API-KEY': api_key,
        }, timeout=10)
        
        if response.ok:
            return f"✅ TikTok API connection successful for user {user_id}"
        else:
            return f"❌ TikTok API connection failed for user {user_id}. Status: {response.status_code} - {response.reason}"
            
    except requests.exceptions.Timeout:
        return f"❌ TikTok API connection timeout for user {user_id}. Please check your internet connection."
    except Exception as e:
        logger.error(f"Error testing TikTok connection: {e}")
        return f"Error testing TikTok connection: {str(e)}"

if __name__ == "__main__":
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()
