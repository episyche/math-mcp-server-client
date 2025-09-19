#!/usr/bin/env python3
"""
YouTube System Rules Demo - Direct function calls to server code
"""

import json
import re
import sys
import os
from datetime import datetime

# Add the current directory to the path so we can import the server functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the server functions directly
from youtube.youtube_mcp_minimal import list_videos, search_videos, get_channel_analytics

class YouTubeAssistant:
    """YouTube assistant that calls server functions directly."""
    
    def __init__(self):
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        
    def extract_user_id(self, query):
        """Extract user_id from query using multiple patterns."""
        user_id_patterns = [
            r"user_id\s*['\"]([^'\"]+)['\"]",  # user_id 'value'
            r"for\s+user_id\s*['\"]([^'\"]+)['\"]",  # for user_id 'value'
            r"user\s+(\w+)",  # user value
        ]
        
        for pattern in user_id_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def process_query(self, query):
        """Process a YouTube query following the system rules."""
        print(f"🎯 Processing query: '{query}'")
        print("=" * 60)
        
        # Rule 11: Extract user_id from the user's query
        user_id = self.extract_user_id(query)
        
        if not user_id:
            # Rule 12: If no user_id is provided, ask the user to provide one
            return {
                "error": "No user_id provided",
                "message": "Please provide a user_id in your query. Example: 'get my videos for user_id \"your-user-id\"'"
            }
        
        print(f"✅ Extracted user_id: '{user_id}'")
        
        try:
            # Determine which tool to call based on the query
            if "search" in query.lower():
                # Rule 5: When searching videos, provide a clear query string
                search_query = "tutorial" if "tutorial" in query else "general"
                print(f"🔍 Calling search_videos with query: '{search_query}'")
                result = search_videos(user_id, search_query)
            elif "analytics" in query.lower():
                # Rule 7: Channel analytics are available for the authenticated user's channel
                print("📊 Calling get_channel_analytics")
                result = get_channel_analytics(user_id)
            else:
                # Default to list_videos
                # Rule 9: For video listings, return comprehensive data including view counts, like counts, and thumbnails
                print("📹 Calling list_videos")
                result = list_videos(user_id)
            
            # Extract content from CallToolResult
            if hasattr(result, 'content') and result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            else:
                return {"error": "No content returned from server"}
            
        except Exception as e:
            return {"error": f"Tool call failed: {str(e)}"}

def main():
    """Main demo function."""
    print("🚀 YouTube System Rules Demo with Direct Server Calls")
    print("=" * 60)
    
    assistant = YouTubeAssistant()
    
    # Test queries
    test_queries = [
        "get all my videos in youtube for user_id '842a4951-5d0c-40c6-8488-732626d5a3c0'",
        "search videos about tutorial for user_id 'user-456'",
        "get channel analytics for user_id 'analytics-user-789'",
        "show me my videos",  # No user_id provided
        "list videos for user_id 'test-user-123'"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*20} TEST {i} {'='*20}")
        result = assistant.process_query(query)
        
        print("\n📋 Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + "="*60)
    
    print("\n✅ Demo Complete!")
    print("\n📋 System Rules Summary:")
    print("1. ✅ Extract user_id from queries using regex patterns")
    print("2. ✅ Pass user_id to appropriate YouTube tools")
    print("3. ✅ Ask for user_id if not provided")
    print("4. ✅ Return structured results from tools")
    print("5. ✅ Handle different query types (list, search, analytics)")
    print("6. ✅ Uses actual server functions for real tool calls")

if __name__ == "__main__":
    main()
