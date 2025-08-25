"""
Google Ads MCP Server Package

This package provides MCP (Model Context Protocol) server functionality for Google Ads API operations.
It includes tools for campaign management, ad group creation, customer operations, and more.

Available tools:
- create_customer: Create new Google Ads customer accounts
- add_campaign: Create new campaigns
- remove_campaign: Delete campaigns
- get_campaign: Fetch campaign details
- add_ad_group: Create ad groups
- update_campaign: Modify campaign fields

Usage:
    python google_ads_client.py --question "Create a campaign for customer 123456789"
"""

__version__ = "1.0.0"
__author__ = "Google Ads MCP Team"

from .google_ads_mcp_server import mcp

__all__ = ["mcp"]
