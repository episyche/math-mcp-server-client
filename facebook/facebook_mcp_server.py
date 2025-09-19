#!/usr/bin/env python3
"""
Facebook MCP Server - Database credentials version
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Sequence
from datetime import datetime

# MCP imports
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import common database utilities
from db_utils import get_facebook_minion_credentials, update_facebook_token_in_db

# Initialize MCP server
mcp = FastMCP("facebook-mcp-server")

def get_facebook_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Facebook credentials for a user."""
    return get_facebook_minion_credentials(user_id)

def call_facebook_api(api_func, user_id: str):
    """Wrapper to call Facebook API with automatic token refresh if needed."""
    creds = get_facebook_credentials(user_id)
    if not creds:
        raise RuntimeError(f"No active Facebook minion found for user {user_id}")
    
    token = creds.get('facebook_access_token')
    if not token:
        raise RuntimeError("No Facebook access token available")
    
    try:
        return api_func(token, creds)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token expired, try to refresh
            logger.warning("Facebook token expired, attempting refresh...")
            # For now, we'll just raise an error as Facebook token refresh requires user interaction
            raise RuntimeError("Token expired. User needs to re-authenticate with Facebook.")
        elif e.response.status_code == 403:
            # Forbidden - might be insufficient permissions
            error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
            error_reason = error_data.get('error', {}).get('message', 'Unknown error')
            raise RuntimeError(f"Facebook API access forbidden: {error_reason}")
        elif e.response.status_code == 429:
            # Rate limit exceeded
            raise RuntimeError("Facebook API rate limit exceeded. Please try again later.")
        else:
            raise e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling Facebook API: {str(e)}")
    except Exception as e:
        raise e

# Facebook API helper functions
def get_user_info_api(token: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Get user information from Facebook."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.facebook.com/v23.0/me"
    params = {"fields": "id,name,email"}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_ad_accounts_api(token: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Get ad accounts for the user."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.facebook.com/v23.0/me/adaccounts"
    params = {"fields": "id,name,account_id,account_status,currency,timezone_name"}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_pages_api(token: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Get pages for the user."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.facebook.com/v23.0/me/accounts"
    params = {"fields": "id,name,access_token,category,connected_instagram_account"}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_campaigns_api(token: str, creds: Dict[str, Any], ad_account_id: str, fields: List[str] = None) -> Dict[str, Any]:
    """Get campaigns for an ad account."""
    if fields is None:
        fields = ["name", "id", "account_id", "created_time", "start_time", "stop_time", "status", "objective", "buying_type"]
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{ad_account_id}/campaigns"
    params = {"fields": ",".join(fields)}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_campaign_insights_api(token: str, creds: Dict[str, Any], campaign_id: str, fields: List[str] = None, date_preset: str = None, time_range: Dict = None) -> Dict[str, Any]:
    """Get insights for a campaign."""
    if fields is None:
        fields = ["impressions", "reach", "spend", "cpc", "clicks"]
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{campaign_id}/insights"
    params = {"fields": ",".join(fields)}
    
    if date_preset:
        params["date_preset"] = date_preset
    if time_range:
        params["time_range"] = json.dumps(time_range)
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def create_campaign_api(token: str, creds: Dict[str, Any], ad_account_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new campaign."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{ad_account_id}/campaigns"
    
    response = requests.post(url, headers=headers, json=campaign_data)
    response.raise_for_status()
    return response.json()

def get_adsets_api(token: str, creds: Dict[str, Any], ad_account_id: str, fields: List[str] = None) -> Dict[str, Any]:
    """Get ad sets for an ad account."""
    if fields is None:
        fields = ["name", "id", "start_time", "status", "end_time", "campaign{name,id}", "billing_event", "optimization_goal", "targeting", "daily_budget"]
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{ad_account_id}/adsets"
    params = {"fields": ",".join(fields)}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_ads_api(token: str, creds: Dict[str, Any], ad_account_id: str, fields: List[str] = None) -> Dict[str, Any]:
    """Get ads for an ad account."""
    if fields is None:
        fields = ["name", "id", "adset{name,id}", "campaign{name,id}", "creative{name,id}", "created_time", "status"]
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{ad_account_id}/ads"
    params = {"fields": ",".join(fields)}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_page_feed_api(token: str, creds: Dict[str, Any], page_id: str, fields: List[str] = None) -> Dict[str, Any]:
    """Get page feed posts."""
    if fields is None:
        fields = ["id", "message", "created_time", "permalink_url", "attachments{media_type,media,url}"]
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{page_id}/feed"
    params = {"fields": ",".join(fields)}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def post_to_page_api(token: str, creds: Dict[str, Any], page_id: str, post_data: Dict[str, Any]) -> Dict[str, Any]:
    """Post to page feed."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{page_id}/feed"
    
    response = requests.post(url, headers=headers, json=post_data)
    response.raise_for_status()
    return response.json()

def get_page_insights_api(token: str, creds: Dict[str, Any], page_id: str, metrics: List[str]) -> Dict[str, Any]:
    """Get page insights."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.facebook.com/v23.0/{page_id}/insights"
    params = {"metric": ",".join(metrics)}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_first_page_id_api(token: str, creds: Dict[str, Any]) -> str:
    """Get the first available page ID for the user."""
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.facebook.com/v23.0/me/accounts"
    params = {"fields": "id,name,access_token"}
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    data = response.json()
    if data.get("data") and len(data["data"]) > 0:
        return data["data"][0]["id"]
    else:
        raise RuntimeError("No pages found for this user")

# MCP Tool Functions
@mcp.tool()
def get_user_credentials(user_id: str):
    """Get Facebook credentials for a user."""
    try:
        creds = get_facebook_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No Facebook credentials found for this user."
                )]
            )
        
        safe_info = {
            "user_id": user_id,
            "has_access_token": bool(creds.get("facebook_access_token")),
            "app_id": creds.get("app_id"),
            "has_app_secret": bool(creds.get("app_secret")),
            "has_client_credentials": bool(creds.get("client_id")),
            "minion_name": creds.get("minion_name"),
            "capabilities": creds.get("capabilities"),
            "webhook_verification": creds.get("webhook_verification"),
            "subscribe_to_events": creds.get("subscribe_to_events")
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
def get_user_info(user_id: str):
    """Get user information from Facebook."""
    try:
        user_info = call_facebook_api(get_user_info_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_user_info",
                    "user_info": user_info
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
def get_ad_accounts(user_id: str):
    """Get ad accounts for the user."""
    try:
        ad_accounts = call_facebook_api(get_ad_accounts_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_ad_accounts",
                    "ad_accounts": ad_accounts
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
def get_pages(user_id: str):
    """Get pages for the user."""
    try:
        pages = call_facebook_api(get_pages_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_pages",
                    "pages": pages
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
def get_campaigns(user_id: str, ad_account_id: str, fields: List[str] = None):
    """Get campaigns for an ad account."""
    try:
        campaigns = call_facebook_api(lambda token, creds: get_campaigns_api(token, creds, ad_account_id, fields), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_campaigns",
                    "ad_account_id": ad_account_id,
                    "campaigns": campaigns
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
def get_campaign_insights(user_id: str, campaign_id: str, fields: List[str] = None, date_preset: str = None, time_range: Dict = None):
    """Get insights for a campaign."""
    try:
        insights = call_facebook_api(lambda token, creds: get_campaign_insights_api(token, creds, campaign_id, fields, date_preset, time_range), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_campaign_insights",
                    "campaign_id": campaign_id,
                    "insights": insights
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
def create_campaign(user_id: str, ad_account_id: str, name: str, objective: str, status: str = "PAUSED", special_ad_categories: List[str] = None, buying_type: str = "AUCTION"):
    """Create a new campaign."""
    try:
        campaign_data = {
            "name": name,
            "objective": objective,
            "status": status,
            "buying_type": buying_type
        }
        
        if special_ad_categories:
            campaign_data["special_ad_categories"] = special_ad_categories
        
        result = call_facebook_api(lambda token, creds: create_campaign_api(token, creds, ad_account_id, campaign_data), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "create_campaign",
                    "ad_account_id": ad_account_id,
                    "campaign_data": campaign_data,
                    "result": result
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
def get_adsets(user_id: str, ad_account_id: str, fields: List[str] = None):
    """Get ad sets for an ad account."""
    try:
        adsets = call_facebook_api(lambda token, creds: get_adsets_api(token, creds, ad_account_id, fields), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_adsets",
                    "ad_account_id": ad_account_id,
                    "adsets": adsets
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
def get_ads(user_id: str, ad_account_id: str, fields: List[str] = None):
    """Get ads for an ad account."""
    try:
        ads = call_facebook_api(lambda token, creds: get_ads_api(token, creds, ad_account_id, fields), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_ads",
                    "ad_account_id": ad_account_id,
                    "ads": ads
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
def get_page_feed(user_id: str, page_id: str = None, fields: List[str] = None):
    """Get page feed posts."""
    try:
        # If no page_id provided, get the first available page
        if not page_id:
            page_id = call_facebook_api(get_first_page_id_api, user_id)
        
        feed = call_facebook_api(lambda token, creds: get_page_feed_api(token, creds, page_id, fields), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_page_feed",
                    "page_id": page_id,
                    "feed": feed
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
def post_to_page(user_id: str, message: str, page_id: str = None, link: str = None):
    """Post to page feed."""
    try:
        # If no page_id provided, get the first available page
        if not page_id:
            page_id = call_facebook_api(get_first_page_id_api, user_id)
        
        post_data = {"message": message}
        if link:
            post_data["link"] = link
        
        result = call_facebook_api(lambda token, creds: post_to_page_api(token, creds, page_id, post_data), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "post_to_page",
                    "page_id": page_id,
                    "post_data": post_data,
                    "result": result
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
def get_first_page_id(user_id: str):
    """Get the first available page ID for the user."""
    try:
        page_id = call_facebook_api(get_first_page_id_api, user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_first_page_id",
                    "page_id": page_id
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
def get_page_insights(user_id: str, page_id: str = None, metrics: List[str] = None):
    """Get page insights."""
    try:
        if metrics is None:
            metrics = ["page_impressions", "page_impressions_paid", "page_actions_post_reactions_total", "page_fans"]
        
        # If no page_id provided, get the first available page
        if not page_id:
            page_id = call_facebook_api(get_first_page_id_api, user_id)
        
        insights = call_facebook_api(lambda token, creds: get_page_insights_api(token, creds, page_id, metrics), user_id)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_page_insights",
                    "page_id": page_id,
                    "metrics": metrics,
                    "insights": insights
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
