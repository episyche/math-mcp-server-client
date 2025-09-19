#!/usr/bin/env python3
"""
Test YouTube system rules and user_id extraction
"""

import re
from datetime import datetime

def test_user_id_extraction():
    """Test if we can extract user_id from various query formats."""
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Test queries
    test_queries = [
        "get all my videos in youtube for user_id '842a4951-5d0c-40c6-8488-732626d5a3c0'",
        "list videos for user_id 'test-user-123'",
        "search videos about tutorial for user_id 'user-456'",
        "get channel analytics for user_id 'analytics-user-789'",
        "show me my videos",  # No user_id provided
        "get videos for user 12345"  # Different format
    ]
    
    print("🧪 Testing YouTube System Rules and User ID Extraction")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        
        # Extract user_id using regex patterns
        user_id_patterns = [
            r"user_id\s*['\"]([^'\"]+)['\"]",  # user_id 'value'
            r"for\s+user_id\s*['\"]([^'\"]+)['\"]",  # for user_id 'value'
            r"user\s+(\w+)",  # user value
        ]
        
        user_id = None
        for pattern in user_id_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                break
        
        if user_id:
            print(f"   ✅ Extracted user_id: '{user_id}'")
            
            # Simulate what the YouTube tools would receive
            if "videos" in query.lower() and "search" not in query.lower():
                print(f"   📹 Would call: list_videos(user_id='{user_id}')")
            elif "search" in query.lower():
                search_query = "tutorial" if "tutorial" in query else "general"
                print(f"   🔍 Would call: search_videos(user_id='{user_id}', query='{search_query}')")
            elif "analytics" in query.lower():
                print(f"   📊 Would call: get_channel_analytics(user_id='{user_id}')")
        else:
            print(f"   ❌ No user_id found - would ask user to provide one")
    
    print("\n" + "=" * 60)
    print("✅ YouTube System Rules Test Complete!")
    print("\nSystem Rules Summary:")
    print("1. Extract user_id from queries using patterns like 'user_id \"value\"'")
    print("2. Pass user_id to appropriate YouTube tools")
    print("3. Ask for user_id if not provided")
    print("4. Return structured results from tools")

def test_youtube_system_rules():
    """Test the YouTube system rules format."""
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_rules = f"""
    You are a YouTube assistant with access to the 'YouTube MCP Server'.
    This server exposes tools to perform CRUD operations on the YouTube Data API v3

    Current Date: {current_date}

    Rules:
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
    """
    
    print("\n📋 YouTube System Rules:")
    print("=" * 40)
    print(system_rules)
    print("=" * 40)

if __name__ == "__main__":
    test_user_id_extraction()
    test_youtube_system_rules()
