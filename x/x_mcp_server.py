#!/usr/bin/env python3
"""
X (Twitter) MCP Server - Database credentials version
"""

import os
import json
import logging
import requests
import base64
from typing import Dict, Any, Optional
from contextlib import contextmanager

# MCP imports
from mcp.server import Server
from mcp.types import CallToolResult, TextContent

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import common database utilities
from db_utils import get_db_connection, get_x_minion_credentials, update_x_tokens_in_db

# Default to public Twitter API base if not provided
BASE_URL = os.getenv("X_BASE_URL") or "https://api.twitter.com"
API_VERSION = "2"

# Initialize MCP server
mcp = Server("x-mcp-server")


def get_x_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get X (Twitter) credentials for a user."""
    return get_x_minion_credentials(user_id)

def refresh_authorization(user_id: str) -> Optional[Dict[str, str]]:
    """Refresh X authorization token using credentials from database."""
    creds = get_x_credentials(user_id)
    if not creds:
        logger.error(f"No X credentials found for user {user_id}")
        return None
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    refresh_token = creds.get('x_refresh_token')
    
    if not all([client_id, client_secret, refresh_token]):
        logger.error("Missing required credentials for token refresh")
        return None
    
    credentials = f"{client_id}:{client_secret}"
    credentials_bytes = credentials.encode("utf-8")
    b64_credentials = base64.b64encode(credentials_bytes).decode()
    
    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(_url("/oauth2/token"), data=data, headers=headers)
    if response.status_code == 200:
        authentication_data = response.json()
        
        new_access = authentication_data["access_token"]
        new_refresh = authentication_data.get("refresh_token", refresh_token)
        
        # Update tokens in database
        if update_x_tokens_in_db(user_id, new_access, new_refresh):
            logger.info("Successfully refreshed and updated X tokens")
            return {"access_token": new_access, "refresh_token": new_refresh}
        else:
            logger.warning("Token refreshed but failed to update database")
            return {"access_token": new_access, "refresh_token": new_refresh}
    else:
        logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
        return None


def _url(path):
    return f"{BASE_URL}/{API_VERSION}{path}"

@mcp.call_tool()
def get_user_credentials(user_id: str):
    """Get X (Twitter) credentials for a user."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X (Twitter) credentials found for this user."
                )]
            )
        
        safe_info = {
            "user_id": user_id,
            "has_access_token": bool(creds.get("x_token")),
            "has_refresh_token": bool(creds.get("x_refresh_token")),
            "has_bearer_token": bool(creds.get("x_bearer_token")),
            "has_client_credentials": bool(creds.get("client_id")),
            "connection_details": creds.get("connection_details")
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
def create_post(user_id: str, text: str):
    """Create a new post on X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        token = creds.get('x_token')
        if not token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No access token available for this user."
                )]
            )
        
        data = {"text": text}
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(_url("/tweets"), json=data, headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.post(_url("/tweets"), json=data, headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        try:
            response.raise_for_status()
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(response.json(), indent=2, ensure_ascii=False)
                )]
            )
        except Exception:
            try:
                error_data = response.json()
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ Error {response.status_code}: {json.dumps(error_data, indent=2)}"
                    )]
                )
            except Exception:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ Error {response.status_code}: {response.text}"
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
def delete_post(user_id: str, tweet_id: str):
    """Delete a post on X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        token = creds.get('x_token')
        if not token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No access token available for this user."
                )]
            )
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(_url(f"/tweets/{tweet_id}"), headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.delete(_url(f"/tweets/{tweet_id}"), headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        response.raise_for_status()
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
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
def get_post_by_id(user_id: str, tweet_id: str):
    """Get a specific post by ID from X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        bearer_token = creds.get('x_bearer_token')
        if not bearer_token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No bearer token available for this user."
                )]
            )
        
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(_url(f"/tweets/{tweet_id}"), headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.get(_url(f"/tweets/{tweet_id}"), headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        response.raise_for_status()
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
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
def get_my_user_info(user_id: str):
    """Get current user information from X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        token = creds.get('x_token')
        if not token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No access token available for this user."
                )]
            )
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(_url("/users/me"), headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.get(_url("/users/me"), headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        response.raise_for_status()
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
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
def get_user_by_username(user_id: str, username: str):
    """Get user information by username from X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        bearer_token = creds.get('x_bearer_token')
        if not bearer_token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No bearer token available for this user."
                )]
            )
        
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(_url(f"/users/by/username/{username}"), headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.get(_url(f"/users/by/username/{username}"), headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        response.raise_for_status()
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
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
def search_recent_tweets(user_id: str, query: str, max_results: int = 10):
    """Search for recent tweets on X (Twitter)."""
    try:
        creds = get_x_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No X credentials found for this user."
                )]
            )
        
        bearer_token = creds.get('x_bearer_token')
        if not bearer_token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No bearer token available for this user."
                )]
            )
        
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(_url(f"/tweets/search/recent?max_results={max_results}&query={query}"), headers=headers)
        
        if response.status_code == 401:
            # Try to refresh token
            new_tokens = refresh_authorization(user_id)
            if new_tokens:
                headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
                response = requests.get(_url(f"/tweets/search/recent?max_results={max_results}&query={query}"), headers=headers)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ Token expired and refresh failed."
                    )]
                )
        
        response.raise_for_status()
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
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
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()


    