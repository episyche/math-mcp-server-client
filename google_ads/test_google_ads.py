#!/usr/bin/env python3
"""
Test script for Google Ads MCP Server integration.
This script tests the basic functionality without requiring actual Google Ads API credentials.
"""

import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test MCP server import
        from google_ads.google_ads_mcp_server import mcp
        print("✅ MCP server imported successfully")
        
        # Test GoogleAdsAPI imports
        from google_ads.GoogleAdsAPI.create_customer import create_customer_main
        print("✅ create_customer imported successfully")
        
        from google_ads.GoogleAdsAPI.add_campaigns import add_campaign_main
        print("✅ add_campaigns imported successfully")
        
        from google_ads.GoogleAdsAPI.remove_campaign import remove_campaign_main
        print("✅ remove_campaign imported successfully")
        
        from google_ads.GoogleAdsAPI.get_campaign import get_campaign_main
        print("✅ get_campaign imported successfully")
        
        from google_ads.GoogleAdsAPI.add_ad_group import add_ad_group_main
        print("✅ add_ad_group imported successfully")
        
        from google_ads.GoogleAdsAPI.update_campaign import update_campaign_main
        print("✅ update_campaign imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_mcp_server():
    """Test that the MCP server can be initialized."""
    try:
        print("\nTesting MCP server initialization...")
        
        from google_ads.google_ads_mcp_server import mcp
        
        # Check if the server has the expected tools
        expected_tools = [
            'create_customer',
            'add_campaign', 
            'remove_campaign',
            'get_campaign',
            'add_ad_group',
            'update_campaign'
        ]
        
        available_tools = [tool.name for tool in mcp._tools]
        print(f"Available tools: {available_tools}")
        
        for tool_name in expected_tools:
            if tool_name in available_tools:
                print(f"✅ {tool_name} tool found")
            else:
                print(f"❌ {tool_name} tool missing")
                return False
        
        print("✅ MCP server initialized successfully with all expected tools")
        return True
        
    except Exception as e:
        print(f"❌ MCP server initialization failed: {e}")
        return False

def test_client_import():
    """Test that the client can be imported."""
    try:
        print("\nTesting client import...")
        
        from google_ads.google_ads_client import (
            get_server_script_path,
            normalize_operation,
            llm_route_question
        )
        print("✅ Client functions imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Client import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Google Ads MCP Server Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("MCP Server Test", test_mcp_server),
        ("Client Import Test", test_client_import)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
