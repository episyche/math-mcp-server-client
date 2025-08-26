#!/usr/bin/env python3
"""
Shopify MCP Server

This server provides Python interfaces to Shopify functionality including:
- Product management
- Customer management  
- Order management
- Store analytics
"""

import json
import logging
import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger = logging.getLogger(__name__)
    logger.info("Loaded .env file successfully")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv not installed. Install with: pip install python-dotenv")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Shopify API configuration - now reads from .env file
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")

# Create FastMCP server
mcp = FastMCP("ShopifyServer")

def make_shopify_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the Shopify API"""
    if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
        raise Exception("Shopify credentials not configured. Set SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN in your .env file.")
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}/{endpoint}.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        import requests
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except ImportError:
        raise Exception("requests library not installed. Install with: pip install requests")
    except requests.exceptions.RequestException as e:
        logger.error(f"Shopify API request failed: {e}")
        raise Exception(f"Failed to fetch data from Shopify: {e}")

@mcp.tool()
def get_products(limit: int = 10, status: str = "any", vendor: str = "", product_type: str = "", tag: str = "", query: str = "", cursor: str = "", include_variants: bool = True, include_images: bool = True, include_inventory: bool = False) -> str:
    """Retrieve products from Shopify store with filtering and pagination"""
    try:
        if SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN:
            # Use real Shopify API
            params = {"limit": min(limit, 250)}
            if status and status != "any":
                params["status"] = status
            if vendor:
                params["vendor"] = vendor
            if product_type:
                params["product_type"] = product_type
            if tag:
                params["tag"] = tag
            if query:
                params["query"] = query
            
            result = make_shopify_request("products", params)
            products = result.get("products", [])
            
            return f"Retrieved {len(products)} products from your Shopify store:\n{json.dumps(result, indent=2)}"
        else:
            # Fallback to mock data
            products = [
                {
                    "id": "gid://shopify/Product/123456789",
                    "title": "Sample Product",
                    "handle": "sample-product",
                    "status": "active",
                    "vendor": "Sample Vendor",
                    "productType": "Sample Type",
                    "tags": ["sample", "demo"],
                    "priceRange": {
                        "minVariantPrice": {"amount": "19.99", "currencyCode": "USD"},
                        "maxVariantPrice": {"amount": "29.99", "currencyCode": "USD"}
                    }
                }
            ] * min(limit, 5)
            
            result = {
                "products": products,
                "total": len(products),
                "filters": {
                    "status": status,
                    "query": query,
                    "limit": limit
                }
            }
            
            return f"⚠️ Using mock data (no Shopify credentials in .env file). Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real data.\n\nRetrieved {len(products)} sample products:\n{json.dumps(result, indent=2)}"
        
    except Exception as e:
        return f"Error retrieving products: {str(e)}"

@mcp.tool()
def get_customers(limit: int = 10, query: str = "", cursor: str = "", include_addresses: bool = True, include_orders: bool = False) -> str:
    """Retrieve customers from Shopify store with filtering and pagination"""
    try:
        if SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN:
            # Use real Shopify API
            params = {"limit": min(limit, 250)}
            if query:
                params["query"] = query
            
            result = make_shopify_request("customers", params)
            customers = result.get("customers", [])
            
            return f"Retrieved {len(customers)} customers from your Shopify store:\n{json.dumps(result, indent=2)}"
        else:
            # Fallback to mock data
            customers = [
                {
                    "id": "gid://shopify/Customer/123456789",
                    "firstName": "Sample",
                    "lastName": "Customer",
                    "email": "sample@example.com",
                    "phone": "+1234567890",
                    "ordersCount": 0,
                    "totalSpent": {"amount": "0.00", "currencyCode": "USD"}
                }
            ] * min(limit, 3)
            
            result = {
                "customers": customers,
                "total": len(customers),
                "filters": {"query": query, "limit": limit},
                "options": {"include_addresses": include_addresses, "include_orders": include_orders}
            }
            
            return f"⚠️ Using mock data (no Shopify credentials in .env file). Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real data.\n\nRetrieved {len(customers)} sample customers:\n{json.dumps(result, indent=2)}"
        
    except Exception as e:
        return f"Error retrieving customers: {str(e)}"

@mcp.tool()
def get_orders(limit: int = 10, status: str = "any", financial_status: str = "any", fulfillment_status: str = "any", created_at_min: str = "", created_at_max: str = "", query: str = "", cursor: str = "") -> str:
    """Retrieve orders from Shopify store with filtering and pagination"""
    try:
        if SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN:
            # Use real Shopify API
            params = {"limit": min(limit, 250)}
            if status and status != "any":
                params["status"] = status
            if financial_status and financial_status != "any":
                params["financial_status"] = financial_status
            if fulfillment_status and fulfillment_status != "any":
                params["fulfillment_status"] = fulfillment_status
            if created_at_min:
                params["created_at_min"] = created_at_min
            if created_at_max:
                params["created_at_max"] = created_at_max
            if query:
                params["query"] = query
            
            result = make_shopify_request("orders", params)
            orders = result.get("orders", [])
            
            return f"Retrieved {len(orders)} orders from your Shopify store:\n{json.dumps(result, indent=2)}"
        else:
            # Fallback to mock data
            orders = [
                {
                    "id": "gid://shopify/Order/123456789",
                    "name": "#1001",
                    "createdAt": "2024-01-15T10:30:00Z",
                    "displayFinancialStatus": "paid",
                    "displayFulfillmentStatus": "fulfilled",
                    "totalPriceSet": {
                        "shopMoney": {"amount": "59.99", "currencyCode": "USD"}
                    },
                    "customer": {
                        "firstName": "Sample",
                        "lastName": "Customer",
                        "email": "sample@example.com"
                    }
                }
            ] * min(limit, 4)
            
            result = {
                "orders": orders,
                "total": len(orders),
                "filters": {"status": status, "limit": limit}
            }
            
            return f"⚠️ Using mock data (no Shopify credentials in .env file). Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real data.\n\nRetrieved {len(orders)} sample orders:\n{json.dumps(result, indent=2)}"
        
    except Exception as e:
        return f"Error retrieving orders: {str(e)}"

@mcp.tool()
def get_store_info() -> str:
    """Get basic store information and settings"""
    try:
        if SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN:
            # Use real Shopify API
            result = make_shopify_request("shop")
            shop_info = result.get("shop", {})
            
            return f"Your Shopify store information:\n{json.dumps(result, indent=2)}"
        else:
            # Fallback to mock data
            store_info = {
                "name": "Your Store (configure credentials in .env)",
                "domain": "your-store.myshopify.com",
                "email": "support@your-store.com",
                "phone": "+1234567890",
                "address": {
                    "address1": "Your Address",
                    "city": "Your City",
                    "province": "Your State",
                    "zip": "12345",
                    "country": "Your Country"
                },
                "currency": "USD",
                "timezone": "America/New_York",
                "plan_name": "Your Plan",
                "created_at": "2023-01-01T00:00:00Z"
            }
            
            return f"⚠️ Using mock data (no Shopify credentials in .env file). Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real data.\n\nSample store information:\n{json.dumps(store_info, indent=2)}"
        
    except Exception as e:
        return f"Error retrieving store info: {str(e)}"

@mcp.tool()
def get_analytics(metric: str = "sales", date_range: str = "last_30_days") -> str:
    """Get store analytics and metrics"""
    try:
        if SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN:
            # Use real Shopify API for analytics
            # Note: Shopify Admin API has limited analytics, you might need Shopify Analytics API
            return f"⚠️ Shopify Admin API has limited analytics. For detailed analytics, consider using Shopify Analytics API or Shopify Plus features.\n\nRequested metric: {metric}, Date range: {date_range}"
        else:
            # Fallback to mock data
            analytics = {
                "metric": metric,
                "date_range": date_range,
                "current_period": {
                    "value": 0.00,
                    "currency": "USD",
                    "change_percentage": 0.0
                },
                "previous_period": {
                    "value": 0.00,
                    "currency": "USD"
                },
                "trend": "no data",
                "note": "Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real analytics data"
            }
            
            return f"⚠️ Using mock data (no Shopify credentials in .env file). Add SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN to your .env file for real data.\n\nSample analytics for {metric} ({date_range}):\n{json.dumps(analytics, indent=2)}"
        
    except Exception as e:
        return f"Error retrieving analytics: {str(e)}"

if __name__ == "__main__":
    # Check if required environment variables are set
    if not SHOPIFY_STORE_URL:
        logger.warning("SHOPIFY_STORE_URL not found in .env file - using mock data")
    if not SHOPIFY_ACCESS_TOKEN:
        logger.warning("SHOPIFY_ACCESS_TOKEN not found in .env file - using mock data")
    
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()
