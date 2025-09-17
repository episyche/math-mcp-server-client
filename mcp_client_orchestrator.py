#!/usr/bin/env python3
"""
YouTube MCP Client Orchestrator
Command-line tool to interact with YouTube API using MCP
Usage: python mcp_client_orchestrator.py -q "get all my videos" --user-id "123"
"""

import os
import sys
import json
import logging
import requests
import argparse
import uuid
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager
import re

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import common database utilities
from db_utils import (
    get_db_connection, 
    get_youtube_minion_credentials, 
    get_x_minion_credentials,
    get_google_ads_minion_credentials,
    get_facebook_minion_credentials,
    get_shopify_minion_credentials,
    update_youtube_token_in_db,
    update_youtube_tokens_in_db,
    update_x_tokens_in_db,
    update_google_ads_tokens_in_db,
    update_facebook_token_in_db,
    update_shopify_token_in_db
)

# ---------------------------
# YouTube Token Management Functions
# ---------------------------

def create_new_youtube_token(user_id: str) -> Optional[str]:
    """Create a new YouTube access token using client credentials from database."""
    try:
        creds = get_youtube_minion_credentials(user_id)
        if not creds:
            logger.error("No YouTube credentials found for user %s", user_id)
            return None
        
        client_id = creds.get('client_id')
        client_secret = creds.get('client_secret')
        # Use proper OAuth2 out-of-band redirect URI
        redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        # Validate required fields
        if not client_id:
            logger.error("YOUTUBE_CLIENT_ID is missing from database")
            return None
        if not client_secret:
            logger.error("YOUTUBE_CLIENT_SECRET is missing from database")
            return None
        
        print(f"🔑 Using Client ID: {client_id[:20]}...")
        print(f"🔑 Using Client Secret: {client_secret[:10]}...")
        
        # Step 1: Generate authorization URL
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&scope=https://www.googleapis.com/auth/youtube&response_type=code&access_type=offline&prompt=consent"
        
        print(f"\n🌐 Please visit this URL to authorize the application:")
        print(f"{auth_url}")
        print(f"\n📋 After authorization, you'll be redirected to: {redirect_uri}")
        print(f"📋 Copy the 'code' parameter from the URL and paste it below:")
        
        # Get authorization code from user
        auth_code = input("\n🔐 Enter the authorization code: ").strip()
        
        if not auth_code:
            print("❌ No authorization code provided")
            return None
        
        # Step 2: Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        print("🔄 Exchanging authorization code for tokens...")
        response = requests.post(token_url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if access_token:
                print("✅ Successfully created new YouTube access token!")
                
                # Update both access token and refresh token in database
                if update_youtube_tokens_in_db(user_id, access_token, refresh_token):
                    print("✅ Tokens updated in database successfully!")
                    return access_token
                else:
                    print("⚠️ Tokens created but failed to update database")
                    return access_token
            else:
                print("❌ No access token in response")
                return None
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"❌ Failed to create token (HTTP {response.status_code}): {error_data}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Token creation request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during token creation: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error creating token: {str(e)}")
        return None

def refresh_youtube_token(user_id: str) -> Optional[str]:
    """Refresh YouTube access token using refresh token from database."""
    url = "https://oauth2.googleapis.com/token"
    
    # Get credentials from database
    creds = get_youtube_minion_credentials(user_id)
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


def check_token_validity(user_id: str) -> Dict[str, Any]:
    """Check if the current access token is valid by making a test API call."""
    try:
        creds = get_youtube_minion_credentials(user_id)
        if not creds:
            return {"valid": False, "error": "No credentials found"}
        
        token = creds.get('youtube_access_token')
        if not token:
            return {"valid": False, "error": "No access token found"}
        
        # Make a simple API call to check token validity
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "snippet", "mine": "true"}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return {"valid": True, "message": "Token is valid"}
        elif response.status_code == 401:
            return {"valid": False, "error": "Token is expired or invalid"}
        else:
            return {"valid": False, "error": f"API error: {response.status_code}"}
            
    except Exception as e:
        return {"valid": False, "error": f"Error checking token: {str(e)}"}

# ---------------------------
# Question Analysis and Routing
# ---------------------------

def analyze_question(question: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze the user's question and determine the appropriate service and action."""
    question_lower = question.lower().strip()
    
    # X (Twitter) patterns
    x_keywords = [
        "x", "twitter", "tweet", "tweets", "post", "posts", "follow", "unfollow", 
        "like", "unlike", "retweet", "reply", "mention", "hashtag", "timeline"
    ]
    
    # YouTube patterns
    youtube_keywords = [
        "youtube", "video", "videos", "channel", "upload", "subscriber", "subscribers",
        "youtube.com", "youtu.be", "playlist", "watch"
    ]
    
    # Google Ads patterns
    google_ads_keywords = [
        "google ads", "googleads", "ads", "advertising", "campaign", "campaigns",
        "ad group", "adgroup", "advertisement", "adwords", "google adwords",
        "accounts", "customer", "customers", "manager", "client"
    ]
    
    # Facebook patterns
    facebook_keywords = [
        "facebook", "fb", "page", "pages", "post", "posts", "feed", "timeline",
        "facebook.com", "fb.com", "like", "likes", "comment", "comments",
        "share", "shares", "facebook page", "fb page", "facebook post", "fb post",
        "facebook ads", "fb ads", "facebook campaign", "fb campaign", "facebook account",
        "fb account", "facebook user", "fb user", "facebook details", "fb details"
    ]
    
    # Shopify patterns
    shopify_keywords = [
        "shopify", "store", "shop", "ecommerce", "products", "orders", "customers",
        "inventory", "analytics", "store details", "my store", "shopify store",
        "shopify.com", "myshopify.com", "admin", "dashboard", "sales", "revenue",
        "shopify api", "store api", "ecommerce store", "online store"
    ]
    
    # Check for X-related queries
    if any(keyword in question_lower for keyword in x_keywords):
        return analyze_x_question(question_lower)
    
    # Check for YouTube-related queries
    elif any(keyword in question_lower for keyword in youtube_keywords):
        return analyze_youtube_question(question_lower)
    
    # Check for Google Ads-related queries
    elif any(keyword in question_lower for keyword in google_ads_keywords):
        return analyze_google_ads_question(question_lower)
    
    # Check for Facebook-related queries
    elif any(keyword in question_lower for keyword in facebook_keywords):
        return analyze_facebook_question(question_lower)
    
    # Check for Shopify-related queries
    elif any(keyword in question_lower for keyword in shopify_keywords):
        return analyze_shopify_question(question_lower)
    
    # Default to YouTube search for backward compatibility
    else:
        return "youtube", "search_videos", {"query": question}

def analyze_x_question(question_lower: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze X (Twitter) specific questions."""
    
    # X user info patterns
    if any(keyword in question_lower for keyword in [
        "my user", "user details", "profile", "account info", "my info", "who am i"
    ]):
        return "x", "get_my_user_info", {}
    
    # X search patterns (check before post patterns)
    if any(keyword in question_lower for keyword in [
        "search", "find", "look for", "search for", "recent tweets", "tweets about"
    ]):
        search_query = extract_search_query(question_lower)
        return "x", "search_recent_tweets", {"query": search_query, "max_results": 10}
    
    # X post creation patterns
    if any(keyword in question_lower for keyword in [
        "post", "tweet", "create", "write", "send", "publish"
    ]):
        # Extract the text to post
        post_text = extract_post_text(question_lower)
        return "x", "create_post", {"text": post_text}
    
    # X user lookup patterns
    if any(keyword in question_lower for keyword in [
        "user", "username", "profile", "find user", "lookup user"
    ]):
        username = extract_username(question_lower)
        if username:
            return "x", "get_user_by_username", {"username": username}
    
    # Default X action
    return "x", "get_my_user_info", {}

def analyze_youtube_question(question_lower: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze YouTube specific questions."""
    
    # Video listing patterns
    if any(keyword in question_lower for keyword in [
        "list my videos", "show my videos", "my videos", "channel videos", "uploaded videos",
        "get all my videos", "get my videos", "fetch my videos"
    ]):
        return "youtube", "list_videos", {}
    
    # Video search patterns
    if any(keyword in question_lower for keyword in [
        "search", "find video", "look for", "video about", "search for"
    ]):
        search_query = extract_search_query(question_lower)
        return "youtube", "search_videos", {"query": search_query}
    
    # Video analytics patterns
    if any(keyword in question_lower for keyword in [
        "analytics", "stats", "statistics", "views", "subscribers", "performance"
    ]):
        if "video" in question_lower:
            video_id = extract_video_id(question_lower)
            return "youtube", "video_analytics", {"video_id": video_id} if video_id else {}
        else:
            return "youtube", "channel_analytics", {}
    
    # Default YouTube action
    return "youtube", "search_videos", {"query": question_lower}

def analyze_google_ads_question(question_lower: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze Google Ads specific questions."""
    
    # Google Ads account patterns
    if any(keyword in question_lower for keyword in [
        "get accounts", "list accounts", "all accounts", "show accounts", "account list"
    ]):
        customer_id = extract_customer_id(question_lower)
        return "google_ads", "get_all_accounts", {"customer_id": customer_id or "default"}
    
    # Google Ads campaign patterns
    if any(keyword in question_lower for keyword in [
        "get campaign", "list campaign", "show campaign", "campaign info"
    ]):
        customer_id = extract_customer_id(question_lower)
        return "google_ads", "get_campaign", {"customer_id": customer_id or "default"}
    
    # Google Ads create campaign patterns
    if any(keyword in question_lower for keyword in [
        "create campaign", "add campaign", "new campaign", "make campaign"
    ]):
        customer_id = extract_customer_id(question_lower)
        return "google_ads", "add_campaign", {"customer_id": customer_id or "default"}
    
    # Google Ads remove campaign patterns
    if any(keyword in question_lower for keyword in [
        "remove campaign", "delete campaign", "stop campaign"
    ]):
        customer_id, campaign_id = extract_customer_and_campaign_id(question_lower)
        return "google_ads", "remove_campaign", {
            "customer_id": customer_id or "default",
            "campaign_id": campaign_id or "default"
        }
    
    # Google Ads ad group patterns
    if any(keyword in question_lower for keyword in [
        "add ad group", "create ad group", "new ad group", "ad group"
    ]):
        customer_id, campaign_id = extract_customer_and_campaign_id(question_lower)
        return "google_ads", "add_ad_group", {
            "customer_id": customer_id or "default",
            "campaign_id": campaign_id or "default"
        }
    
    # Google Ads client account patterns
    if any(keyword in question_lower for keyword in [
        "client accounts", "get clients", "list clients", "show clients"
    ]):
        manager_id = extract_manager_id(question_lower)
        return "google_ads", "get_all_client_accounts", {"manager_id": manager_id or "default"}
    
    # Google Ads create customer patterns
    if any(keyword in question_lower for keyword in [
        "create customer", "new customer", "add customer"
    ]):
        manager_id, country = extract_customer_creation_params(question_lower)
        return "google_ads", "create_customer", {
            "manager_customer_id": manager_id or "default",
            "country_code": country or "US"
        }
    
    # Default Google Ads action
    return "google_ads", "get_all_accounts", {"customer_id": "default"}

def analyze_facebook_question(question_lower: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze Facebook specific questions."""
    
    # Facebook user info patterns
    if any(keyword in question_lower for keyword in [
        "user details", "user info", "my details", "my info", "profile", "account info",
        "facebook user", "fb user", "user information", "account details"
    ]):
        return "facebook", "get_user_info", {}
    
    # Facebook credentials patterns
    if any(keyword in question_lower for keyword in [
        "credentials", "token", "access token", "facebook credentials", "fb credentials"
    ]):
        return "facebook", "get_user_credentials", {}
    
    # Facebook pages patterns
    if any(keyword in question_lower for keyword in [
        "pages", "my pages", "facebook pages", "fb pages", "list pages", "show pages"
    ]):
        return "facebook", "get_pages", {}
    
    # Facebook ad accounts patterns
    if any(keyword in question_lower for keyword in [
        "ad accounts", "advertising accounts", "facebook ads", "fb ads", "ads account"
    ]):
        return "facebook", "get_ad_accounts", {}
    
    # Facebook campaigns patterns
    if any(keyword in question_lower for keyword in [
        "campaigns", "facebook campaigns", "fb campaigns", "ad campaigns", "my campaigns"
    ]):
        ad_account_id = extract_ad_account_id(question_lower)
        return "facebook", "get_campaigns", {"ad_account_id": ad_account_id or "default"}
    
    # Facebook page feed patterns
    if any(keyword in question_lower for keyword in [
        "feed", "posts", "timeline", "page feed", "facebook posts", "fb posts"
    ]):
        page_id = extract_page_id(question_lower)
        return "facebook", "get_page_feed", {"page_id": page_id} if page_id else {}
    
    # Facebook page insights patterns
    if any(keyword in question_lower for keyword in [
        "insights", "analytics", "stats", "statistics", "page insights", "facebook insights"
    ]):
        page_id = extract_page_id(question_lower)
        return "facebook", "get_page_insights", {"page_id": page_id} if page_id else {}
    
    # Default Facebook action
    return "facebook", "get_user_info", {}

def analyze_shopify_question(question_lower: str) -> Tuple[str, str, Dict[str, Any]]:
    """Analyze Shopify specific questions."""
    
    # Shopify credentials patterns
    if any(keyword in question_lower for keyword in [
        "credentials", "token", "access token", "shopify credentials", "store credentials"
    ]):
        return "shopify", "get_user_credentials", {}
    
    # Shopify store details patterns
    if any(keyword in question_lower for keyword in [
        "store details", "store info", "my store", "store information", "shop details",
        "shop info", "store settings", "shop settings", "store configuration"
    ]):
        return "shopify", "get_store_details", {}
    
    # Shopify analytics patterns
    if any(keyword in question_lower for keyword in [
        "analytics", "stats", "statistics", "store analytics", "shop analytics",
        "sales analytics", "revenue", "performance", "dashboard", "overview"
    ]):
        return "shopify", "get_store_analytics", {}
    
    # Shopify products patterns
    if any(keyword in question_lower for keyword in [
        "products", "product", "catalog", "inventory", "items", "goods"
    ]):
        return "shopify", "get_products", {}
    
    # Shopify orders patterns
    if any(keyword in question_lower for keyword in [
        "orders", "order", "purchases", "transactions", "sales"
    ]):
        return "shopify", "get_orders", {}
    
    # Shopify customers patterns
    if any(keyword in question_lower for keyword in [
        "customers", "customer", "buyers", "clients", "users"
    ]):
        return "shopify", "get_customers", {}
    
    # Shopify inventory patterns
    if any(keyword in question_lower for keyword in [
        "inventory", "stock", "warehouse", "supply", "quantity"
    ]):
        return "shopify", "get_inventory", {}
    
    # Default Shopify action - learn API first
    return "shopify", "learn_shopify_api", {"api": "admin"}

def extract_customer_id(question: str) -> Optional[str]:
    """Extract customer ID from question."""
    # Look for customer ID patterns
    import re
    customer_id_match = re.search(r'customer[_\s]*id[:\s]*(\d+)', question, re.IGNORECASE)
    if customer_id_match:
        return customer_id_match.group(1)
    
    # Look for just numbers that might be customer IDs
    numbers = re.findall(r'\d{10,}', question)
    if numbers:
        return numbers[0]
    
    return None

def extract_customer_and_campaign_id(question: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract customer ID and campaign ID from question."""
    customer_id = extract_customer_id(question)
    
    # Look for campaign ID patterns
    import re
    campaign_id_match = re.search(r'campaign[_\s]*id[:\s]*(\d+)', question, re.IGNORECASE)
    campaign_id = campaign_id_match.group(1) if campaign_id_match else None
    
    return customer_id, campaign_id

def extract_manager_id(question: str) -> Optional[str]:
    """Extract manager ID from question."""
    return extract_customer_id(question)  # Same logic for now

def extract_customer_creation_params(question: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract manager ID and country from customer creation question."""
    manager_id = extract_customer_id(question)
    
    # Look for country patterns
    import re
    country_match = re.search(r'country[:\s]*([A-Z]{2})', question, re.IGNORECASE)
    country = country_match.group(1) if country_match else None
    
    return manager_id, country

def extract_search_query(question: str) -> str:
    """Extract search query from question."""
    prefixes = ["search for", "find", "look for", "show me", "search", "tweets about", "recent tweets"]
    query = question.lower()
    for prefix in prefixes:
        if query.startswith(prefix):
            query = query[len(prefix):].strip()
            break
    return query

def extract_post_text(question: str) -> str:
    """Extract post text from question."""
    # Remove common prefixes
    prefixes = ["post", "tweet", "create", "write", "send", "publish"]
    text = question.lower()
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    
    # Remove quotes if present
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    elif text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    
    return text

def extract_username(question: str) -> Optional[str]:
    """Extract username from question."""
    # Look for @username pattern
    username_match = re.search(r'@(\w+)', question)
    if username_match:
        return username_match.group(1)
    
    # Look for "username" pattern
    username_match = re.search(r'username\s+(\w+)', question)
    if username_match:
        return username_match.group(1)
    
    # Look for "user" pattern
    username_match = re.search(r'user\s+(\w+)', question)
    if username_match:
        return username_match.group(1)
    
    return None

def extract_video_id(question: str) -> Optional[str]:
    """Extract YouTube video ID from question."""
    youtube_patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, question)
        if match:
            return match.group(1)
    
    id_pattern = r'"([a-zA-Z0-9_-]{11})"'
    match = re.search(id_pattern, question)
    if match:
        return match.group(1)
    
    return None

def extract_ad_account_id(question: str) -> Optional[str]:
    """Extract Facebook ad account ID from question."""
    import re
    # Look for ad account ID patterns like "act_123456789"
    ad_account_match = re.search(r'act_(\d+)', question, re.IGNORECASE)
    if ad_account_match:
        return f"act_{ad_account_match.group(1)}"
    
    # Look for account ID patterns
    account_id_match = re.search(r'account[_\s]*id[:\s]*(\d+)', question, re.IGNORECASE)
    if account_id_match:
        return f"act_{account_id_match.group(1)}"
    
    return None

def extract_page_id(question: str) -> Optional[str]:
    """Extract Facebook page ID from question."""
    import re
    # Look for page ID patterns
    page_id_match = re.search(r'page[_\s]*id[:\s]*(\d+)', question, re.IGNORECASE)
    if page_id_match:
        return page_id_match.group(1)
    
    return None

# ---------------------------
# YouTube API Functions
# ---------------------------

def call_youtube_mcp_server(tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Call YouTube MCP server tools."""
    try:
        # Import the YouTube MCP server functions
        from youtube_mcp_server import (
            get_user_credentials, list_videos, search_videos, 
            get_video_analytics, get_channel_analytics
        )
        
        # Map tool names to functions
        tool_functions = {
            "get_user_credentials": get_user_credentials,
            "list_videos": list_videos,
            "search_videos": search_videos,
            "get_video_analytics": get_video_analytics,
            "get_channel_analytics": get_channel_analytics
        }
        
        if tool_name not in tool_functions:
            raise ValueError(f"Unknown YouTube tool: {tool_name}")
        
        # Call the tool with user_id as first parameter
        result = tool_functions[tool_name](user_id, **kwargs)
        
        # Extract the text content from MCP result
        if hasattr(result, 'content') and result.content:
            text_content = result.content[0].text
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"message": text_content}
        else:
            return {"error": "No content returned from YouTube MCP server"}
            
    except Exception as e:
        logger.error(f"Error calling YouTube MCP server: {e}")
        return {"error": str(e)}

# ---------------------------
# Google Ads MCP Server Integration
# ---------------------------

def call_google_ads_mcp_server(tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Call Google Ads MCP server tools."""
    try:
        # Import the Google Ads MCP server functions
        from google_ads_mcp_server import (
            get_user_credentials, create_customer, add_campaign, remove_campaign,
            get_campaign, add_ad_group, get_all_accounts, get_all_client_accounts
        )
        
        # Map tool names to functions
        tool_functions = {
            "get_user_credentials": get_user_credentials,
            "create_customer": create_customer,
            "add_campaign": add_campaign,
            "remove_campaign": remove_campaign,
            "get_campaign": get_campaign,
            "add_ad_group": add_ad_group,
            "get_all_accounts": get_all_accounts,
            "get_all_client_accounts": get_all_client_accounts
        }
        
        if tool_name not in tool_functions:
            raise ValueError(f"Unknown Google Ads tool: {tool_name}")
        
        # Call the tool with user_id as first parameter
        result = tool_functions[tool_name](user_id, **kwargs)
        
        # Extract the text content from MCP result
        if hasattr(result, 'content') and result.content:
            text_content = result.content[0].text
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"message": text_content}
        else:
            return {"error": "No content returned from Google Ads MCP server"}
            
    except Exception as e:
        logger.error(f"Error calling Google Ads MCP server: {e}")
        return {"error": str(e)}

def google_ads_action(user_id: str, question: str) -> Dict[str, Any]:
    """
    Main Google Ads action orchestrator.
    Analyzes the question and performs the appropriate Google Ads action.
    """
    try:
        print(f"🎯 Processing: '{question}' for user {user_id}")
        
        # Get user's Google Ads minion credentials
        creds = get_google_ads_minion_credentials(user_id)
        if not creds:
            return {
                "error": "❌ No active Google Ads minion found for this user. Please ensure you have an active Google Ads minion configured.",
                "success": False
            }
        
        print(f"✅ Found Google Ads credentials for user {user_id}")
        print(f"   Minion: {creds.get('minion_name')}")
        print(f"   Has developer token: {bool(creds.get('google_ads_developer_token'))}")
        print(f"   Has client credentials: {bool(creds.get('google_ads_client_id'))}")
        
        # Analyze question and determine action
        service, action_type, params = analyze_question(question)
        print(f"🎯 Service: {service}, Action: {action_type}")
        
        # Execute the appropriate Google Ads action
        if action_type == "get_all_accounts":
            customer_id = params.get("customer_id", "default")
            print(f"📊 Getting all accounts for customer: {customer_id}")
            result = call_google_ads_mcp_server("get_all_accounts", user_id, customer_id=customer_id)
            return {
                "action": "get_all_accounts",
                "customer_id": customer_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_campaign":
            customer_id = params.get("customer_id", "default")
            print(f"📊 Getting campaign for customer: {customer_id}")
            result = call_google_ads_mcp_server("get_campaign", user_id, customer_id=customer_id)
            return {
                "action": "get_campaign",
                "customer_id": customer_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "add_campaign":
            customer_id = params.get("customer_id", "default")
            print(f"➕ Adding campaign for customer: {customer_id}")
            result = call_google_ads_mcp_server("add_campaign", user_id, customer_id=customer_id)
            return {
                "action": "add_campaign",
                "customer_id": customer_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "remove_campaign":
            customer_id = params.get("customer_id", "default")
            campaign_id = params.get("campaign_id", "default")
            print(f"➖ Removing campaign {campaign_id} for customer: {customer_id}")
            result = call_google_ads_mcp_server("remove_campaign", user_id, customer_id=customer_id, campaign_id=campaign_id)
            return {
                "action": "remove_campaign",
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "add_ad_group":
            customer_id = params.get("customer_id", "default")
            campaign_id = params.get("campaign_id", "default")
            print(f"➕ Adding ad group to campaign {campaign_id} for customer: {customer_id}")
            result = call_google_ads_mcp_server("add_ad_group", user_id, customer_id=customer_id, campaign_id=campaign_id)
            return {
                "action": "add_ad_group",
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_all_client_accounts":
            manager_id = params.get("manager_id", "default")
            print(f"👥 Getting client accounts for manager: {manager_id}")
            result = call_google_ads_mcp_server("get_all_client_accounts", user_id, manager_id=manager_id)
            return {
                "action": "get_all_client_accounts",
                "manager_id": manager_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "create_customer":
            manager_customer_id = params.get("manager_customer_id", "default")
            country_code = params.get("country_code", "US")
            print(f"👤 Creating customer for manager {manager_customer_id} in country {country_code}")
            result = call_google_ads_mcp_server("create_customer", user_id, manager_customer_id=manager_customer_id, country_code=country_code)
            return {
                "action": "create_customer",
                "manager_customer_id": manager_customer_id,
                "country_code": country_code,
                "result": result,
                "success": True
            }
            
        else:
            return {
                "error": f"❌ Google Ads action '{action_type}' not yet implemented or not recognized.",
                "success": False
            }
        
    except Exception as e:
        logger.error(f"Error in Google Ads action: {str(e)}")
        return {
            "error": f"❌ Error executing Google Ads action: {str(e)}",
            "success": False
        }

# ---------------------------
# X MCP Server Integration
# ---------------------------


def call_x_mcp_server(tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Call X MCP server tools."""
    try:
        # Import the X MCP server functions
        from x_mcp_server import (
            get_user_credentials, create_post, delete_post, get_post_by_id,
            get_my_user_info, get_user_by_username, search_recent_tweets
        )
        
        # Map tool names to functions
        tool_functions = {
            "get_user_credentials": get_user_credentials,
            "create_post": create_post,
            "delete_post": delete_post,
            "get_post_by_id": get_post_by_id,
            "get_my_user_info": get_my_user_info,
            "get_user_by_username": get_user_by_username,
            "search_recent_tweets": search_recent_tweets
        }
        
        if tool_name not in tool_functions:
            raise ValueError(f"Unknown X tool: {tool_name}")
        
        # Call the tool with user_id as first parameter
        result = tool_functions[tool_name](user_id, **kwargs)
        
        # Extract the text content from MCP result
        if hasattr(result, 'content') and result.content:
            text_content = result.content[0].text
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"message": text_content}
        else:
            return {"error": "No content returned from X MCP server"}
            
    except Exception as e:
        logger.error(f"Error calling X MCP server: {e}")
        return {"error": str(e)}

def call_facebook_mcp_server(tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Call Facebook MCP server tools."""
    try:
        # Import the Facebook MCP server functions
        from facebook_mcp_server import (
            get_user_credentials, get_user_info, get_ad_accounts, get_pages,
            get_campaigns, get_campaign_insights, create_campaign, get_adsets,
            get_ads, get_page_feed, post_to_page, get_page_insights, get_first_page_id
        )
        
        # Map tool names to functions
        tool_functions = {
            "get_user_credentials": get_user_credentials,
            "get_user_info": get_user_info,
            "get_ad_accounts": get_ad_accounts,
            "get_pages": get_pages,
            "get_campaigns": get_campaigns,
            "get_campaign_insights": get_campaign_insights,
            "create_campaign": create_campaign,
            "get_adsets": get_adsets,
            "get_ads": get_ads,
            "get_page_feed": get_page_feed,
            "post_to_page": post_to_page,
            "get_page_insights": get_page_insights,
            "get_first_page_id": get_first_page_id
        }
        
        if tool_name not in tool_functions:
            raise ValueError(f"Unknown Facebook tool: {tool_name}")
        
        # Call the tool with user_id as first parameter
        result = tool_functions[tool_name](user_id, **kwargs)
        
        # Extract the text content from MCP result
        if hasattr(result, 'content') and result.content:
            text_content = result.content[0].text
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"message": text_content}
        else:
            return {"error": "No content returned from Facebook MCP server"}
            
    except Exception as e:
        logger.error(f"Error calling Facebook MCP server: {e}")
        return {"error": str(e)}

def call_shopify_mcp_server(tool_name: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """Call Shopify MCP server tools."""
    try:
        # Import the Shopify MCP server functions
        from shopify_mcp_server import (
            get_user_credentials, learn_shopify_api, get_store_analytics, 
            get_customers, get_orders, get_products, get_inventory, get_store_details
        )
        
        # Map tool names to functions
        tool_functions = {
            "get_user_credentials": get_user_credentials,
            "learn_shopify_api": learn_shopify_api,
            "get_store_analytics": get_store_analytics,
            "get_customers": get_customers,
            "get_orders": get_orders,
            "get_products": get_products,
            "get_inventory": get_inventory,
            "get_store_details": get_store_details
        }
        
        if tool_name not in tool_functions:
            raise ValueError(f"Unknown Shopify tool: {tool_name}")
        
        # Call the tool with user_id as first parameter
        result = tool_functions[tool_name](user_id, **kwargs)
        
        # Extract the text content from MCP result
        if hasattr(result, 'content') and result.content:
            text_content = result.content[0].text
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return {"message": text_content}
        else:
            return {"error": "No content returned from Shopify MCP server"}
            
    except Exception as e:
        logger.error(f"Error calling Shopify MCP server: {e}")
        return {"error": str(e)}

def x_action(user_id: str, question: str) -> Dict[str, Any]:
    """
    Main X action orchestrator.
    Analyzes the question and performs the appropriate X action.
    """
    try:
        print(f"🐦 Processing: '{question}' for user {user_id}")
        
        # Get user's X minion credentials
        creds = get_x_minion_credentials(user_id)
        if not creds:
            return {
                "error": "❌ No active X minion found for this user. Please ensure you have an active X minion configured.",
                "success": False
            }
        
        print(f"✅ Found X credentials for user {user_id}")
        print(f"   Minion: {creds.get('minion_name')}")
        print(f"   Has token: {bool(creds.get('x_token'))}")
        print(f"   Has bearer token: {bool(creds.get('x_bearer_token'))}")
        
        # Analyze question and determine action
        service, action_type, params = analyze_question(question)
        print(f"🎯 Service: {service}, Action: {action_type}")
        
        # Execute the appropriate X action
        if action_type == "get_my_user_info":
            print("👤 Getting your X user info...")
            result = call_x_mcp_server("get_my_user_info", user_id)
            return {
                "action": "get_my_user_info",
                "result": result,
                "success": True
            }
            
        elif action_type == "create_post":
            text = params.get("text", question)
            print(f"📝 Creating post: '{text}'")
            result = call_x_mcp_server("create_post", user_id, text=text)
            return {
                "action": "create_post",
                "text": text,
                "result": result,
                "success": True
            }
            
        elif action_type == "search_recent_tweets":
            query = params.get("query", question)
            max_results = params.get("max_results", 10)
            print(f"🔍 Searching tweets: '{query}'")
            result = call_x_mcp_server("search_recent_tweets", user_id, query=query, max_results=max_results)
            return {
                "action": "search_recent_tweets",
                "query": query,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_user_by_username":
            username = params.get("username")
            if not username:
                return {
                    "error": "❌ Please provide a username to look up.",
                    "success": False
                }
            print(f"👤 Looking up user: @{username}")
            result = call_x_mcp_server("get_user_by_username", user_id, username=username)
            return {
                "action": "get_user_by_username",
                "username": username,
                "result": result,
                "success": True
            }
            
        else:
            return {
                "error": f"❌ X action '{action_type}' not yet implemented or not recognized.",
                "success": False
            }
        
    except Exception as e:
        logger.error(f"Error in X action: {str(e)}")
        return {
            "error": f"❌ Error executing X action: {str(e)}",
            "success": False
        }

# ---------------------------
# Main Orchestrator Function
# ---------------------------

def youtube_action(user_id: str, question: str) -> Dict[str, Any]:
    """
    Main YouTube action orchestrator.
    Analyzes the question and performs the appropriate YouTube action.
    """
    try:
        print(f"🎬 Processing: '{question}' for user {user_id}")
        
        # Get user's YouTube minion credentials
        creds = get_youtube_minion_credentials(user_id)
        if not creds:
            return {
                "error": "❌ No active YouTube minion found for this user. Please ensure you have an active YouTube minion configured.",
                "success": False
            }
        
        print(f"✅ Found YouTube credentials for user {user_id}")
        print(f"   Channel ID: {creds.get('youtube_channel_id')}")
        print(f"   Minion: {creds.get('minion_name')}")
        
        # Check token validity first
        token_check = check_token_validity(user_id)
        if not token_check.get("valid"):
            print(f"⚠️ Token is invalid: {token_check.get('error')}")
            print("🔄 Attempting to refresh token...")
            
            new_token = refresh_youtube_token(user_id)
            if new_token:
                if update_youtube_token_in_db(user_id, new_token):
                    print("✅ Token refreshed successfully!")
                else:
                    return {
                        "error": "❌ Token refreshed but failed to update database",
                        "success": False
                    }
            else:
                print("❌ Token refresh failed. Creating new token...")
                print("🔑 Using client credentials from database to create new token...")
                
                new_token = create_new_youtube_token(user_id)
                if new_token:
                    print("✅ New token created successfully!")
                else:
                    return {
                        "error": "❌ Failed to create new token. Please check your client credentials and try again.",
                        "success": False
                    }
        
        # Analyze question and determine action
        service, action_type, params = analyze_youtube_question(question.lower())
        print(f"🎯 Action: {action_type}")
        
        # Execute the appropriate action
        if action_type == "list_videos":
            print("📹 Fetching your videos...")
            result = call_youtube_mcp_server("list_videos", user_id)
            return {
                "action": "list_videos",
                "result": result,
                "success": True
            }
            
        elif action_type == "search_videos":
            query = params.get("query", question)
            print(f"🔍 Searching for: '{query}'")
            result = call_youtube_mcp_server("search_videos", user_id, query=query)
            return {
                "action": "search_videos",
                "query": query,
                "result": result,
                "success": True
            }
            
        elif action_type == "video_analytics":
            video_id = params.get("video_id")
            if not video_id:
                return {
                    "error": "❌ Please provide a video ID or YouTube URL for analytics.",
                    "success": False
                }
            print(f"📊 Getting analytics for video: {video_id}")
            result = call_youtube_mcp_server("get_video_analytics", user_id, video_id=video_id)
            return {
                "action": "video_analytics",
                "video_id": video_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "channel_analytics":
            print("📊 Getting channel analytics...")
            result = call_youtube_mcp_server("get_channel_analytics", user_id)
            return {
                "action": "channel_analytics",
                "result": result,
                "success": True
            }
            
        else:
            return {
                "error": f"❌ Action '{action_type}' not yet implemented or not recognized.",
                "success": False
            }
        
    except Exception as e:
        logger.error(f"Error in YouTube action: {str(e)}")
        return {
            "error": f"❌ Error executing YouTube action: {str(e)}",
            "success": False
        }

def facebook_action(user_id: str, question: str) -> Dict[str, Any]:
    """
    Main Facebook action orchestrator.
    Analyzes the question and performs the appropriate Facebook action.
    """
    try:
        print(f"📘 Processing: '{question}' for user {user_id}")
        
        # Get user's Facebook minion credentials
        creds = get_facebook_minion_credentials(user_id)
        if not creds:
            return {
                "error": "❌ No active Facebook minion found for this user. Please ensure you have an active Facebook minion configured.",
                "success": False
            }
        
        print(f"✅ Found Facebook credentials for user {user_id}")
        print(f"   App ID: {creds.get('app_id')}")
        print(f"   Minion: {creds.get('minion_name')}")
        
        # Analyze the question to determine action
        service, action_type, params = analyze_facebook_question(question.lower())
        
        print(f"🎯 Detected action: {action_type}")
        print(f"📋 Parameters: {params}")
        
        # Execute the appropriate action
        if action_type == "get_user_info":
            print("👤 Getting user information...")
            result = call_facebook_mcp_server("get_user_info", user_id)
            return {
                "action": "get_user_info",
                "result": result,
                "success": True
            }
            
        elif action_type == "get_user_credentials":
            print("🔑 Getting user credentials...")
            result = call_facebook_mcp_server("get_user_credentials", user_id)
            return {
                "action": "get_user_credentials",
                "result": result,
                "success": True
            }
            
        elif action_type == "get_pages":
            print("📄 Getting pages...")
            result = call_facebook_mcp_server("get_pages", user_id)
            return {
                "action": "get_pages",
                "result": result,
                "success": True
            }
            
        elif action_type == "get_ad_accounts":
            print("💰 Getting ad accounts...")
            result = call_facebook_mcp_server("get_ad_accounts", user_id)
            return {
                "action": "get_ad_accounts",
                "result": result,
                "success": True
            }
            
        elif action_type == "get_campaigns":
            ad_account_id = params.get("ad_account_id")
            print(f"📊 Getting campaigns for ad account: {ad_account_id}")
            result = call_facebook_mcp_server("get_campaigns", user_id, ad_account_id=ad_account_id)
            return {
                "action": "get_campaigns",
                "ad_account_id": ad_account_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_page_feed":
            page_id = params.get("page_id")
            print(f"📰 Getting page feed for page: {page_id or 'auto-detect'}")
            result = call_facebook_mcp_server("get_page_feed", user_id, page_id=page_id)
            return {
                "action": "get_page_feed",
                "page_id": page_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_page_insights":
            page_id = params.get("page_id")
            print(f"📈 Getting page insights for page: {page_id or 'auto-detect'}")
            result = call_facebook_mcp_server("get_page_insights", user_id, page_id=page_id)
            return {
                "action": "get_page_insights",
                "page_id": page_id,
                "result": result,
                "success": True
            }
            
        else:
            return {
                "error": f"❌ Action '{action_type}' not yet implemented or not recognized.",
                "success": False
            }
        
    except Exception as e:
        logger.error(f"Error in Facebook action: {str(e)}")
        return {
            "error": f"❌ Error executing Facebook action: {str(e)}",
            "success": False
        }

def shopify_action(user_id: str, question: str) -> Dict[str, Any]:
    """
    Main Shopify action orchestrator.
    Analyzes the question and performs the appropriate Shopify action.
    """
    try:
        print(f"🛍️ Processing: '{question}' for user {user_id}")
        
        # Get user's Shopify minion credentials
        creds = get_shopify_minion_credentials(user_id)
        if not creds:
            return {
                "error": "❌ No active Shopify minion found for this user. Please ensure you have an active Shopify minion configured.",
                "success": False
            }
        
        print(f"✅ Found Shopify credentials for user {user_id}")
        print(f"   Store Domain: {creds.get('shopify_store_domain')}")
        print(f"   Minion: {creds.get('minion_name')}")
        
        # Analyze the question to determine action
        service, action_type, params = analyze_shopify_question(question.lower())
        
        print(f"🎯 Detected action: {action_type}")
        print(f"📋 Parameters: {params}")
        
        # Generate conversation ID for Shopify tools
        conversation_id = str(uuid.uuid4())
        
        # Execute the appropriate action
        if action_type == "get_user_credentials":
            print("🔑 Getting user credentials...")
            result = call_shopify_mcp_server("get_user_credentials", user_id)
            return {
                "action": "get_user_credentials",
                "result": result,
                "success": True
            }
            
        elif action_type == "learn_shopify_api":
            api = params.get("api", "admin")
            print(f"📚 Learning Shopify {api} API...")
            result = call_shopify_mcp_server("learn_shopify_api", user_id, api=api, conversation_id=conversation_id)
            return {
                "action": "learn_shopify_api",
                "api": api,
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_store_details":
            print("🏪 Getting store details...")
            result = call_shopify_mcp_server("get_store_details", user_id, conversation_id=conversation_id)
            return {
                "action": "get_store_details",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_store_analytics":
            print("📊 Getting store analytics...")
            result = call_shopify_mcp_server("get_store_analytics", user_id, conversation_id=conversation_id)
            return {
                "action": "get_store_analytics",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_products":
            print("📦 Getting products...")
            result = call_shopify_mcp_server("get_products", user_id, conversation_id=conversation_id)
            return {
                "action": "get_products",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_orders":
            print("📋 Getting orders...")
            result = call_shopify_mcp_server("get_orders", user_id, conversation_id=conversation_id)
            return {
                "action": "get_orders",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_customers":
            print("👥 Getting customers...")
            result = call_shopify_mcp_server("get_customers", user_id, conversation_id=conversation_id)
            return {
                "action": "get_customers",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        elif action_type == "get_inventory":
            print("📦 Getting inventory...")
            result = call_shopify_mcp_server("get_inventory", user_id, conversation_id=conversation_id)
            return {
                "action": "get_inventory",
                "conversation_id": conversation_id,
                "result": result,
                "success": True
            }
            
        else:
            return {
                "error": f"❌ Action '{action_type}' not yet implemented or not recognized.",
                "success": False
            }
        
    except Exception as e:
        logger.error(f"Error in Shopify action: {str(e)}")
        return {
            "error": f"❌ Error executing Shopify action: {str(e)}",
            "success": False
        }

# ---------------------------
# Command Line Interface
# ---------------------------

def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(description="MCP Client Orchestrator (YouTube, X, Google Ads, Facebook & Shopify)")
    parser.add_argument("-q", "--question", help="Question or command to execute")
    parser.add_argument("--user-id", required=True, help="User ID to get credentials for")
    parser.add_argument("--check-token", action="store_true", help="Check YouTube token status only")
    parser.add_argument("--refresh-token", action="store_true", help="Refresh YouTube token only")
    parser.add_argument("--create-token", action="store_true", help="Create new YouTube token using OAuth2 flow")
    parser.add_argument("--service", choices=["youtube", "x", "google_ads", "facebook", "shopify", "auto"], default="auto", help="Specify service (auto detects by default)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    user_id = args.user_id
    
    try:
        if args.check_token:
            # Check YouTube token status
            token_check = check_token_validity(user_id)
            print(json.dumps({
                "user_id": user_id,
                "service": "youtube",
                "token_valid": token_check.get("valid", False),
                "error": token_check.get("error") if not token_check.get("valid") else None
            }, indent=2))
            return
        
        if args.refresh_token:
            # Refresh YouTube token
            new_token = refresh_youtube_token(user_id)
            if new_token:
                if update_youtube_token_in_db(user_id, new_token):
                    print("✅ YouTube token refreshed and updated successfully")
                else:
                    print("⚠️ Token refreshed but failed to update database")
            else:
                print("❌ Token refresh failed")
            return
        
        if args.create_token:
            # Create new YouTube token
            new_token = create_new_youtube_token(user_id)
            if new_token:
                print("✅ New YouTube token created and updated successfully")
            else:
                print("❌ Token creation failed")
            return
        
        # Execute action based on service detection or specified service
        if not args.question:
            print("❌ Error: Question is required")
            sys.exit(1)
        
        # Determine which service to use
        if args.service == "auto":
            service, action_type, params = analyze_question(args.question)
        elif args.service == "youtube":
            service = "youtube"
            _, action_type, params = analyze_youtube_question(args.question.lower())
        elif args.service == "x":
            service = "x"
            _, action_type, params = analyze_x_question(args.question.lower())
        elif args.service == "google_ads":
            service = "google_ads"
            _, action_type, params = analyze_google_ads_question(args.question.lower())
        elif args.service == "facebook":
            service = "facebook"
            _, action_type, params = analyze_facebook_question(args.question.lower())
        elif args.service == "shopify":
            service = "shopify"
            _, action_type, params = analyze_shopify_question(args.question.lower())
        else:
            print(f"❌ Error: Unknown service '{args.service}'")
            sys.exit(1)
        
        print(f"🎯 Detected service: {service}")
        
        # Execute the appropriate action
        if service == "youtube":
            result = youtube_action(user_id, args.question)
        elif service == "x":
            result = x_action(user_id, args.question)
        elif service == "google_ads":
            result = google_ads_action(user_id, args.question)
        elif service == "facebook":
            result = facebook_action(user_id, args.question)
        elif service == "shopify":
            result = shopify_action(user_id, args.question)
        else:
            print(f"❌ Error: Unknown service '{service}'")
            sys.exit(1)
        
        if result.get("success"):
            print("\n🎉 Success!")
            print("=" * 50)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
