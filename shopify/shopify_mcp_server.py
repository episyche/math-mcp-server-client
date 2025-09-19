#!/usr/bin/env python3
"""
Shopify MCP Server - Database credentials version
Converts the TypeScript Shopify MCP tools to Python with database credential management
"""

import asyncio
import os
import json
import logging
import requests
import uuid
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime, timedelta

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


# Import common database utilities
from db_utils import get_shopify_minion_credentials, update_shopify_token_in_db

# Initialize MCP server
mcp = FastMCP("shopify-mcp-server")

def get_shopify_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Shopify credentials for a user."""
    return get_shopify_minion_credentials(user_id)

def call_shopify_api(api_func, user_id: str, *args, **kwargs):
    """Wrapper to call Shopify API with automatic token refresh if needed."""
    creds = get_shopify_credentials(user_id)
    if not creds:
        raise RuntimeError(f"No active Shopify minion found for user {user_id}")
    
    access_token = creds.get('shopify_access_token')
    store_domain = creds.get('shopify_store_domain')
    api_version = creds.get('shopify_api_version', '2025-01')
    
    if not access_token or not store_domain:
        raise RuntimeError("No Shopify access token or store domain available")
    
    try:
        return api_func(access_token, store_domain, api_version, *args, **kwargs)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            # Token expired, try to refresh
            logger.warning("Shopify token expired, attempting refresh...")
            # For now, we'll just raise an error as Shopify token refresh requires user interaction
            raise RuntimeError("Token expired. User needs to re-authenticate with Shopify.")
        elif e.response.status_code == 403:
            # Forbidden - might be insufficient permissions
            error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
            error_reason = error_data.get('errors', [{}])[0].get('message', 'Unknown error')
            raise RuntimeError(f"Shopify API access forbidden: {error_reason}")
        elif e.response.status_code == 429:
            # Rate limit exceeded
            raise RuntimeError("Shopify API rate limit exceeded. Please try again later.")
        else:
            raise e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling Shopify API: {str(e)}")
    except Exception as e:
        raise e

# Shopify GraphQL API helper functions
def execute_graphql_query(access_token: str, store_domain: str, api_version: str, query: str, variables: Dict = None) -> Dict[str, Any]:
    """Execute a GraphQL query against Shopify Admin API."""
    # Ensure store domain has proper format
    normalized_domain = store_domain.replace('https://', '').replace('http://', '').rstrip('/')
    graphql_endpoint = f"https://{normalized_domain}/admin/api/{api_version}/graphql.json"
    
    headers = {
        'X-Shopify-Access-Token': access_token,
        'Content-Type': 'application/json',
    }
    
    payload = {
        'query': query,
        'variables': variables or {}
    }
    
    response = requests.post(graphql_endpoint, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    
    # Check for GraphQL errors
    if 'errors' in result:
        error_messages = [error.get('message', 'Unknown error') for error in result['errors']]
        raise RuntimeError(f"GraphQL errors: {'; '.join(error_messages)}")
    
    return result

def build_date_filter(date_range: str) -> str:
    """Build date filter string for GraphQL queries."""
    now = datetime.now()
    
    if date_range == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_range == "yesterday":
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_range == "last_7_days":
        start_date = now - timedelta(days=7)
    elif date_range == "last_30_days":
        start_date = now - timedelta(days=30)
    elif date_range == "last_90_days":
        start_date = now - timedelta(days=90)
    else:  # all_time
        return ""
    
    return f"created_at:>='{start_date.isoformat()}'"

def generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    return str(uuid.uuid4())

# MCP Tool Functions
@mcp.tool()
def get_user_credentials(user_id: str):
    """Get Shopify credentials for a user."""
    try:
        creds = get_shopify_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No Shopify credentials found for this user."
                )]
            )
        
        safe_info = {
            "user_id": user_id,
            "has_access_token": bool(creds.get("shopify_access_token")),
            "store_domain": creds.get("shopify_store_domain"),
            "api_version": creds.get("shopify_api_version"),
            "has_client_credentials": bool(creds.get("shopify_client_id")),
            "minion_name": creds.get("minion_name"),
            "capabilities": creds.get("capabilities")
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
def learn_shopify_api(user_id: str, api: str, conversation_id: str = None):
    """Learn about Shopify APIs - MANDATORY FIRST STEP for all other tools."""
    try:
        current_conversation_id = conversation_id or generate_conversation_id()
        
        # This is a simplified version - in a real implementation, you'd fetch from Shopify's API docs
        api_info = {
            "admin": "Shopify Admin API for managing store data, products, orders, customers, etc.",
            "functions": "Shopify Functions for extending checkout and other store functionality",
            "polaris": "Polaris design system components for building Shopify admin interfaces",
            "webhooks": "Shopify Webhooks for real-time notifications of store events",
            "partners": "Shopify Partners API for managing partner accounts and apps"
        }
        
        if api not in api_info:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Unknown API: {api}. Available APIs: {', '.join(api_info.keys())}"
                )]
            )
        
        response_text = f"""🔗 **IMPORTANT - SAVE THIS CONVERSATION ID:** {current_conversation_id}
⚠️  CRITICAL: You MUST use this exact conversationId in ALL subsequent Shopify tool calls in this conversation.
🚨 ALL OTHER SHOPIFY TOOLS WILL RETURN ERRORS if you don't provide this conversationId.
---
# Shopify {api.title()} API

{api_info[api]}

## Getting Started
This tool provides access to the Shopify {api.title()} API. Use the conversationId above in all subsequent tool calls.

## Available Tools
- get_store_analytics: Get store analytics and statistics
- get_customers: Get customer information
- get_orders: Get order information  
- get_products: Get product information
- get_inventory: Get inventory information
- get_store_details: Get comprehensive store details

*Remember to always pass the conversationId: {current_conversation_id}*"""
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_store_analytics(user_id: str, conversation_id: str, include_orders: bool = True, 
                       include_products: bool = True, include_customers: bool = True, 
                       include_inventory: bool = False, date_range: str = "all_time", 
                       limit: int = 10):
    """Get store analytics and statistics from Shopify Admin API."""
    try:
        # Build the GraphQL query
        query = """
        query GetStoreAnalytics($orderQuery: String, $productQuery: String, $customerQuery: String, $limit: Int!) {
            shop {
                id
                name
                email
                currencyCode
                primaryDomain {
                    url
                    host
                }
                plan {
                    displayName
                    partnerDevelopment
                    shopifyPlus
                }
                createdAt
                updatedAt
            }
            """ + ("""
            orders(first: $limit, query: $orderQuery) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        displayFinancialStatus
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
            """ if include_orders else "") + ("""
            products(first: $limit, query: $productQuery) {
                edges {
                    node {
                        id
                        title
                        status
                        totalInventory
                        createdAt
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
            """ if include_products else "") + ("""
            customers(first: $limit, query: $customerQuery) {
                edges {
                    node {
                        id
                        firstName
                        lastName
                        email
                        createdAt
                        amountSpent {
                            amount
                            currencyCode
                        }
                        numberOfOrders
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
            """ if include_customers else "") + """
        }
        """
        
        date_filter = build_date_filter(date_range)
        
        variables = {
            "orderQuery": date_filter,
            "productQuery": date_filter,
            "customerQuery": date_filter,
            "limit": min(max(limit, 1), 50)
        }
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query, variables)
        
        data = call_shopify_api(execute_query, user_id)
        shop_data = data['data']
        
        # Format the response
        shop = shop_data['shop']
        response_text = f"""# Store Analytics - {shop['name']}

**Date Range:** {date_range.replace('_', ' ').title()}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Store Information

**Store Name:** {shop['name']}
**Store Email:** {shop['email']}
**Currency:** {shop['currencyCode']}
**Domain:** {shop['primaryDomain']['url']}
**Plan:** {shop['plan']['displayName']}
**Shopify Plus:** {'Yes' if shop['plan']['shopifyPlus'] else 'No'}
**Created:** {datetime.fromisoformat(shop['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')}
**Last Updated:** {datetime.fromisoformat(shop['updatedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')}

"""
        
        # Orders Analytics
        if include_orders and 'orders' in shop_data:
            orders = shop_data['orders']['edges']
            total_orders = len(orders)
            total_revenue = 0
            paid_orders = 0
            pending_orders = 0
            refunded_orders = 0
            
            for edge in orders:
                order = edge['node']
                amount = float(order['totalPriceSet']['shopMoney']['amount'])
                total_revenue += amount
                
                status = order['displayFinancialStatus'].lower()
                if status == 'paid':
                    paid_orders += 1
                elif status == 'pending':
                    pending_orders += 1
                elif status == 'refunded':
                    refunded_orders += 1
            
            avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0.00
            paid_pct = (paid_orders / total_orders * 100) if total_orders > 0 else 0
            pending_pct = (pending_orders / total_orders * 100) if total_orders > 0 else 0
            refunded_pct = (refunded_orders / total_orders * 100) if total_orders > 0 else 0
            
            response_text += f"""## Orders Analytics ({total_orders} orders)

**Total Orders:** {total_orders}
**Total Revenue:** {total_revenue:.2f} {shop['currencyCode']}
**Average Order Value:** {avg_order_value:.2f} {shop['currencyCode']}

**Order Status Breakdown:**
- Paid: {paid_orders} ({paid_pct:.1f}%)
- Pending: {pending_orders} ({pending_pct:.1f}%)
- Refunded: {refunded_orders} ({refunded_pct:.1f}%)

"""
        
        # Products Analytics
        if include_products and 'products' in shop_data:
            products = shop_data['products']['edges']
            total_products = len(products)
            active_products = 0
            draft_products = 0
            archived_products = 0
            total_inventory = 0
            
            for edge in products:
                product = edge['node']
                total_inventory += product['totalInventory']
                
                status = product['status'].lower()
                if status == 'active':
                    active_products += 1
                elif status == 'draft':
                    draft_products += 1
                elif status == 'archived':
                    archived_products += 1
            
            avg_inventory = (total_inventory / total_products) if total_products > 0 else 0
            active_pct = (active_products / total_products * 100) if total_products > 0 else 0
            draft_pct = (draft_products / total_products * 100) if total_products > 0 else 0
            archived_pct = (archived_products / total_products * 100) if total_products > 0 else 0
            
            response_text += f"""## Products Analytics ({total_products} products)

**Total Products:** {total_products}
**Total Inventory:** {total_inventory} units
**Average Inventory per Product:** {avg_inventory:.1f} units

**Product Status Breakdown:**
- Active: {active_products} ({active_pct:.1f}%)
- Draft: {draft_products} ({draft_pct:.1f}%)
- Archived: {archived_products} ({archived_pct:.1f}%)

"""
        
        # Customers Analytics
        if include_customers and 'customers' in shop_data:
            customers = shop_data['customers']['edges']
            total_customers = len(customers)
            total_customer_spent = 0
            total_customer_orders = 0
            
            for edge in customers:
                customer = edge['node']
                total_customer_spent += float(customer['amountSpent']['amount'])
                total_customer_orders += customer['numberOfOrders']
            
            avg_customer_spend = (total_customer_spent / total_customers) if total_customers > 0 else 0.00
            avg_orders_per_customer = (total_customer_orders / total_customers) if total_customers > 0 else 0
            
            response_text += f"""## Customers Analytics ({total_customers} customers)

**Total Customers:** {total_customers}
**Total Customer Spend:** {total_customer_spent:.2f} {shop['currencyCode']}
**Total Customer Orders:** {total_customer_orders}
**Average Customer Spend:** {avg_customer_spend:.2f} {shop['currencyCode']}
**Average Orders per Customer:** {avg_orders_per_customer:.1f}

"""
        
        # Inventory Analytics (if requested)
        if include_inventory:
            response_text += """## Inventory Analytics

*Note: Detailed inventory analytics would require additional API calls to inventory endpoints.*

**Recommendation:** Use the `get_inventory` tool for detailed inventory analysis including:
- Low stock items
- Out of stock items
- Inventory by location
- Stock levels by product/variant

"""
        
        response_text += "---\n*Analytics generated from Shopify Admin API data*"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_customers(user_id: str, conversation_id: str, limit: int = 10, query: str = None, 
                 cursor: str = None, include_addresses: bool = True, include_orders: bool = False):
    """Get customers from Shopify Admin API with filtering and pagination."""
    try:
        # Build the GraphQL query
        query_str = """
        query GetCustomers($first: Int!, $after: String, $query: String) {
            customers(first: $first, after: $after, query: $query) {
                edges {
                    node {
                        id
                        firstName
                        lastName
                        email
                        phone
                        createdAt
                        updatedAt
                        tags
                        acceptsMarketing
                        acceptsMarketingUpdatedAt
                        state
                        totalSpent {
                            amount
                            currencyCode
                        }
                        ordersCount
                        """ + ("""
                        defaultAddress {
                            address1
                            address2
                            city
                            provinceCode
                            zip
                            country
                            phone
                        }
                        addresses {
                            address1
                            address2
                            city
                            provinceCode
                            zip
                            country
                            phone
                        }
                        """ if include_addresses else "") + ("""
                        orders(first: 5) {
                            edges {
                                node {
                                    id
                                    name
                                    createdAt
                                    displayFinancialStatus
                                    totalPriceSet {
                                        shopMoney {
                                            amount
                                            currencyCode
                                        }
                                    }
                                }
                            }
                        }
                        """ if include_orders else "") + """
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        
        variables = {
            "first": min(max(limit, 1), 50),
            "after": cursor,
            "query": query
        }
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query_str, variables)
        
        data = call_shopify_api(execute_query, user_id)
        customers_data = data['data']['customers']
        customers = customers_data['edges']
        customer_count = len(customers)
        
        response_text = f"""## Customers ({customer_count} found)

**Search Query:** {query or "All customers"}
**Include Addresses:** {'Yes' if include_addresses else 'No'}
**Include Orders:** {'Yes' if include_orders else 'No'}

"""
        
        if customer_count == 0:
            response_text += "**No customers found matching the specified criteria.**\n\n"
        else:
            response_text += "## Customer Details\n\n"
            
            for index, edge in enumerate(customers):
                customer = edge['node']
                response_text += f"### {index + 1}. {customer['firstName']} {customer['lastName']}\n\n"
                response_text += f"**Customer ID:** {customer['id']}\n"
                response_text += f"**Email:** {customer['email']}\n"
                response_text += f"**Phone:** {customer.get('phone', 'Not provided')}\n"
                response_text += f"**Created:** {datetime.fromisoformat(customer['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**Updated:** {datetime.fromisoformat(customer['updatedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**State:** {customer['state']}\n"
                response_text += f"**Accepts Marketing:** {'Yes' if customer['acceptsMarketing'] else 'No'}\n"
                response_text += f"**Total Spent:** {customer['totalSpent']['amount']} {customer['totalSpent']['currencyCode']}\n"
                response_text += f"**Orders Count:** {customer['ordersCount']}\n\n"
                
                if customer.get('tags'):
                    response_text += f"**Tags:** {', '.join(customer['tags'])}\n\n"
                
                if include_addresses and customer.get('defaultAddress'):
                    addr = customer['defaultAddress']
                    response_text += "**Default Address:**\n"
                    response_text += f"  {addr['address1']}\n"
                    if addr.get('address2'):
                        response_text += f"  {addr['address2']}\n"
                    response_text += f"  {addr['city']}, {addr['provinceCode']} {addr['zip']}\n"
                    response_text += f"  {addr['country']}\n"
                    if addr.get('phone'):
                        response_text += f"  Phone: {addr['phone']}\n"
                    response_text += "\n"
                
                if include_orders and customer.get('orders', {}).get('edges'):
                    orders = customer['orders']['edges']
                    response_text += f"**Recent Orders ({len(orders)}):**\n"
                    for order_index, order_edge in enumerate(orders):
                        order = order_edge['node']
                        response_text += f"  {order_index + 1}. {order['name']} - {order['displayFinancialStatus']} - {order['totalPriceSet']['shopMoney']['amount']} {order['totalPriceSet']['shopMoney']['currencyCode']}\n"
                    response_text += "\n"
                
                response_text += "---\n\n"
        
        # Add pagination info
        if customers_data['pageInfo']['hasNextPage']:
            response_text += f"**Next Page Available:** Use cursor `{customers_data['pageInfo']['endCursor']}` to get more customers\n\n"
        
        response_text += "*Query executed successfully against Shopify Admin API*"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_orders(user_id: str, conversation_id: str, limit: int = 10, status: str = "any", 
               financial_status: str = "any", fulfillment_status: str = "any", 
               created_at_min: str = None, created_at_max: str = None, query: str = None, 
               cursor: str = None):
    """Get orders from Shopify Admin API with filtering and pagination."""
    try:
        # Build query filters
        filters = []
        if status != "any":
            filters.append(f"status:{status.upper()}")
        if financial_status != "any":
            filters.append(f"financial_status:{financial_status.upper()}")
        if fulfillment_status != "any":
            filters.append(f"fulfillment_status:{fulfillment_status.upper()}")
        if created_at_min:
            filters.append(f"created_at:>='{created_at_min}'")
        if created_at_max:
            filters.append(f"created_at:<='{created_at_max}'")
        if query:
            filters.append(f'query:"{query}"')
        
        query_filter = " AND ".join(filters) if filters else None
        
        # Build the GraphQL query
        query_str = """
        query GetOrders($first: Int!, $after: String, $query: String) {
            orders(first: $first, after: $after, query: $query) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        displayFinancialStatus
                        displayFulfillmentStatus
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        subtotalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalShippingPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        totalTaxSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        customer {
                            id
                            firstName
                            lastName
                            email
                            phone
                        }
                        shippingAddress {
                            address1
                            address2
                            city
                            provinceCode
                            zip
                            country
                            phone
                        }
                        lineItems(first: 10) {
                            edges {
                                node {
                                    id
                                    title
                                    quantity
                                    originalTotalSet {
                                        shopMoney {
                                            amount
                                            currencyCode
                                        }
                                    }
                                    variant {
                                        id
                                        title
                                        sku
                                    }
                                }
                            }
                        }
                        tags
                        note
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        
        variables = {
            "first": min(max(limit, 1), 50),
            "after": cursor,
            "query": query_filter
        }
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query_str, variables)
        
        data = call_shopify_api(execute_query, user_id)
        orders_data = data['data']['orders']
        orders = orders_data['edges']
        order_count = len(orders)
        
        response_text = f"""## Orders ({order_count} found)

**Filters Applied:**
- Status: {status}
- Financial Status: {financial_status}
- Fulfillment Status: {fulfillment_status}
{f"- Created After: {created_at_min}" if created_at_min else ""}
{f"- Created Before: {created_at_max}" if created_at_max else ""}
{f"- Search Query: {query}" if query else ""}

"""
        
        if order_count == 0:
            response_text += "**No orders found matching the specified criteria.**\n\n"
        else:
            response_text += "## Order Details\n\n"
            
            for index, edge in enumerate(orders):
                order = edge['node']
                response_text += f"### {index + 1}. Order {order['name']}\n\n"
                response_text += f"**Order ID:** {order['id']}\n"
                response_text += f"**Created:** {datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**Financial Status:** {order['displayFinancialStatus']}\n"
                response_text += f"**Fulfillment Status:** {order['displayFulfillmentStatus']}\n\n"
                
                response_text += f"**Total Price:** {order['totalPriceSet']['shopMoney']['amount']} {order['totalPriceSet']['shopMoney']['currencyCode']}\n"
                response_text += f"**Subtotal:** {order['subtotalPriceSet']['shopMoney']['amount']} {order['subtotalPriceSet']['shopMoney']['currencyCode']}\n"
                response_text += f"**Shipping:** {order['totalShippingPriceSet']['shopMoney']['amount']} {order['totalShippingPriceSet']['shopMoney']['currencyCode']}\n"
                response_text += f"**Tax:** {order['totalTaxSet']['shopMoney']['amount']} {order['totalTaxSet']['shopMoney']['currencyCode']}\n\n"
                
                if order.get('customer'):
                    response_text += f"**Customer:** {order['customer']['firstName']} {order['customer']['lastName']} ({order['customer']['email']})\n\n"
                
                if order.get('lineItems', {}).get('edges'):
                    response_text += "**Line Items:**\n"
                    for item_index, item_edge in enumerate(order['lineItems']['edges']):
                        item = item_edge['node']
                        response_text += f"  {item_index + 1}. {item['title']} (Qty: {item['quantity']}) - {item['originalTotalSet']['shopMoney']['amount']} {item['originalTotalSet']['shopMoney']['currencyCode']}\n"
                    response_text += "\n"
                
                response_text += f"**Tags:** {', '.join(order.get('tags', [])) if order.get('tags') else 'None'}\n"
                if order.get('note'):
                    response_text += f"**Note:** {order['note']}\n"
                response_text += "\n---\n\n"
        
        # Add pagination info
        if orders_data['pageInfo']['hasNextPage']:
            response_text += f"**Next Page Available:** Use cursor `{orders_data['pageInfo']['endCursor']}` to get more orders\n\n"
        
        response_text += "*Query executed successfully against Shopify Admin API*"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_products(user_id: str, conversation_id: str, limit: int = 10, status: str = "any", 
                vendor: str = None, product_type: str = None, tag: str = None, 
                query: str = None, cursor: str = None, include_variants: bool = True, 
                include_images: bool = True, include_inventory: bool = False):
    """Get products from Shopify Admin API with filtering and pagination."""
    try:
        # Build query filters
        filters = []
        if status != "any":
            filters.append(f"status:{status.upper()}")
        if vendor:
            filters.append(f'vendor:"{vendor}"')
        if product_type:
            filters.append(f'product_type:"{product_type}"')
        if tag:
            filters.append(f'tag:"{tag}"')
        if query:
            filters.append(f'query:"{query}"')
        
        query_filter = " AND ".join(filters) if filters else None
        
        # Build the GraphQL query
        query_str = """
        query GetProducts($first: Int!, $after: String, $query: String) {
            products(first: $first, after: $after, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        vendor
                        productType
                        status
                        tags
                        createdAt
                        updatedAt
                        publishedAt
                        totalInventory
                        priceRangeV2 {
                            minVariantPrice {
                                amount
                                currencyCode
                            }
                            maxVariantPrice {
                                amount
                                currencyCode
                            }
                        }
                        """ + ("""
                        images(first: 5) {
                            edges {
                                node {
                                    id
                                    url
                                    altText
                                    width
                                    height
                                }
                            }
                        }
                        """ if include_images else "") + ("""
                        variants(first: 50) {
                            edges {
                                node {
                                    id
                                    title
                                    sku
                                    barcode
                                    price
                                    compareAtPrice
                                    """ + ("""
                                    inventoryQuantity
                                    inventoryPolicy
                                    """ if include_inventory else "") + """
                                    taxable
                                }
                            }
                        }
                        """ if include_variants else "") + """
                        options {
                            id
                            name
                            values
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        
        variables = {
            "first": min(max(limit, 1), 50),
            "after": cursor,
            "query": query_filter
        }
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query_str, variables)
        
        data = call_shopify_api(execute_query, user_id)
        products_data = data['data']['products']
        products = products_data['edges']
        product_count = len(products)
        
        response_text = f"""## Products ({product_count} found)

**Filters Applied:**
- Status: {status}
{f"- Vendor: {vendor}" if vendor else ""}
{f"- Product Type: {product_type}" if product_type else ""}
{f"- Tag: {tag}" if tag else ""}
{f"- Search Query: {query}" if query else ""}

"""
        
        if product_count == 0:
            response_text += "**No products found matching the specified criteria.**\n\n"
        else:
            response_text += "## Product Details\n\n"
            
            for index, edge in enumerate(products):
                product = edge['node']
                response_text += f"### {index + 1}. {product['title']}\n\n"
                response_text += f"**Product ID:** {product['id']}\n"
                response_text += f"**Handle:** {product['handle']}\n"
                response_text += f"**Status:** {product['status']}\n"
                response_text += f"**Vendor:** {product['vendor']}\n"
                response_text += f"**Product Type:** {product['productType']}\n"
                response_text += f"**Created:** {datetime.fromisoformat(product['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**Updated:** {datetime.fromisoformat(product['updatedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                if product.get('publishedAt'):
                    response_text += f"**Published:** {datetime.fromisoformat(product['publishedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**Total Inventory:** {product['totalInventory']}\n\n"
                
                response_text += f"**Price Range:** {product['priceRangeV2']['minVariantPrice']['amount']} - {product['priceRangeV2']['maxVariantPrice']['amount']} {product['priceRangeV2']['minVariantPrice']['currencyCode']}\n\n"
                
                if product.get('description'):
                    desc = product['description'][:200] + "..." if len(product['description']) > 200 else product['description']
                    response_text += f"**Description:** {desc}\n\n"
                
                if product.get('tags'):
                    response_text += f"**Tags:** {', '.join(product['tags'])}\n\n"
                
                if include_images and product.get('images', {}).get('edges'):
                    images = product['images']['edges']
                    response_text += f"**Images ({len(images)}):**\n"
                    for img_index, img_edge in enumerate(images):
                        img = img_edge['node']
                        alt_text = f" - {img['altText']}" if img.get('altText') else ""
                        response_text += f"  {img_index + 1}. {img['url']} ({img['width']}x{img['height']}){alt_text}\n"
                    response_text += "\n"
                
                if include_variants and product.get('variants', {}).get('edges'):
                    variants = product['variants']['edges']
                    response_text += f"**Variants ({len(variants)}):**\n"
                    for var_index, var_edge in enumerate(variants):
                        variant = var_edge['node']
                        response_text += f"  {var_index + 1}. {variant['title']}\n"
                        response_text += f"     - SKU: {variant.get('sku', 'N/A')}\n"
                        response_text += f"     - Price: {variant['price']}\n"
                        if variant.get('compareAtPrice'):
                            response_text += f"     - Compare at Price: {variant['compareAtPrice']}\n"
                        if include_inventory and variant.get('inventoryQuantity') is not None:
                            response_text += f"     - Inventory: {variant['inventoryQuantity']}\n"
                            response_text += f"     - Policy: {variant.get('inventoryPolicy', 'N/A')}\n"
                        response_text += f"     - Taxable: {'Yes' if variant['taxable'] else 'No'}\n"
                    response_text += "\n"
                
                if product.get('options'):
                    response_text += "**Options:**\n"
                    for opt_index, option in enumerate(product['options']):
                        response_text += f"  {opt_index + 1}. {option['name']}: {', '.join(option['values'])}\n"
                    response_text += "\n"
                
                response_text += "---\n\n"
        
        # Add pagination info
        if products_data['pageInfo']['hasNextPage']:
            response_text += f"**Next Page Available:** Use cursor `{products_data['pageInfo']['endCursor']}` to get more products\n\n"
        
        response_text += "*Query executed successfully against Shopify Admin API*"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_inventory(user_id: str, conversation_id: str, limit: int = 10, location_id: str = None, 
                 product_id: str = None, variant_id: str = None, low_stock: bool = False, 
                 out_of_stock: bool = False, cursor: str = None):
    """Get inventory information from Shopify Admin API with filtering and pagination."""
    try:
        # Build query filters
        filters = []
        if location_id:
            filters.append(f"location_id:{location_id}")
        if product_id:
            filters.append(f"product_id:{product_id}")
        if variant_id:
            filters.append(f"variant_id:{variant_id}")
        if low_stock:
            filters.append("available:<=10")
        if out_of_stock:
            filters.append("available:0")
        
        query_filter = " AND ".join(filters) if filters else None
        
        # Build the GraphQL query
        query_str = """
        query GetInventory($first: Int!, $after: String, $query: String) {
            inventoryItems(first: $first, after: $after, query: $query) {
                edges {
                    node {
                        id
                        sku
                        tracked
                        createdAt
                        updatedAt
                        variant {
                            id
                            title
                            sku
                            barcode
                            price
                            product {
                                id
                                title
                                handle
                            }
                        }
                        inventoryLevels(first: 10) {
                            edges {
                                node {
                                    id
                                    available
                                    location {
                                        id
                                        name
                                        address {
                                            address1
                                            address2
                                            city
                                            provinceCode
                                            zip
                                            country
                                        }
                                    }
                                }
                            }
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        
        variables = {
            "first": min(max(limit, 1), 50),
            "after": cursor,
            "query": query_filter
        }
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query_str, variables)
        
        data = call_shopify_api(execute_query, user_id)
        inventory_data = data['data']['inventoryItems']
        items = inventory_data['edges']
        item_count = len(items)
        
        response_text = f"""## Inventory Items ({item_count} found)

**Filters Applied:**
{f"- Location ID: {location_id}" if location_id else ""}
{f"- Product ID: {product_id}" if product_id else ""}
{f"- Variant ID: {variant_id}" if variant_id else ""}
{f"- Low Stock Only (≤10)" if low_stock else ""}
{f"- Out of Stock Only" if out_of_stock else ""}

"""
        
        if item_count == 0:
            response_text += "**No inventory items found matching the specified criteria.**\n\n"
        else:
            response_text += "## Inventory Details\n\n"
            
            for index, edge in enumerate(items):
                item = edge['node']
                variant = item['variant']
                product = variant['product']
                
                response_text += f"### {index + 1}. {product['title']} - {variant['title']}\n\n"
                response_text += f"**Inventory Item ID:** {item['id']}\n"
                response_text += f"**Product ID:** {product['id']}\n"
                response_text += f"**Variant ID:** {variant['id']}\n"
                response_text += f"**SKU:** {item.get('sku') or variant.get('sku') or 'N/A'}\n"
                response_text += f"**Barcode:** {variant.get('barcode') or 'N/A'}\n"
                response_text += f"**Price:** {variant['price']}\n"
                response_text += f"**Tracked:** {'Yes' if item['tracked'] else 'No'}\n"
                response_text += f"**Created:** {datetime.fromisoformat(item['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += f"**Updated:** {datetime.fromisoformat(item['updatedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                if item.get('inventoryLevels', {}).get('edges'):
                    levels = item['inventoryLevels']['edges']
                    response_text += f"**Inventory Levels ({len(levels)} locations):**\n"
                    total_available = 0
                    
                    for level_index, level_edge in enumerate(levels):
                        level = level_edge['node']
                        location = level['location']
                        total_available += level['available']
                        
                        response_text += f"  {level_index + 1}. {location['name']}\n"
                        response_text += f"     - Available: {level['available']}\n"
                        response_text += f"     - Location ID: {location['id']}\n"
                        response_text += f"     - Address: {location['address']['address1']}"
                        if location['address'].get('address2'):
                            response_text += f", {location['address']['address2']}"
                        response_text += f", {location['address']['city']}, {location['address']['provinceCode']} {location['address']['zip']}, {location['address']['country']}\n"
                    
                    response_text += f"\n**Total Available:** {total_available}\n"
                    
                    # Add stock status indicators
                    if total_available == 0:
                        response_text += "**Status:** 🔴 Out of Stock\n"
                    elif total_available <= 10:
                        response_text += "**Status:** 🟡 Low Stock\n"
                    else:
                        response_text += "**Status:** 🟢 In Stock\n"
                else:
                    response_text += "**Inventory Levels:** No inventory levels found\n"
                
                response_text += "\n---\n\n"
        
        # Add pagination info
        if inventory_data['pageInfo']['hasNextPage']:
            response_text += f"**Next Page Available:** Use cursor `{inventory_data['pageInfo']['endCursor']}` to get more inventory items\n\n"
        
        response_text += "*Query executed successfully against Shopify Admin API*"
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
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
def get_store_details(user_id: str, conversation_id: str):
    """Get comprehensive store details from Shopify Admin API."""
    try:
        # Build the GraphQL query
        query_str = """
        query GetStoreDetails {
            shop {
                id
                name
                myshopifyDomain
                primaryDomain {
                    host
                    url
                    sslEnabled
                }
                email
                contactEmail
                currencyCode
                currencyFormats {
                    moneyFormat
                    moneyWithCurrencyFormat
                }
                ianaTimezone
                timezoneAbbreviation
                timezoneOffset
                weightUnit
                unitSystem
                checkoutApiSupported
                taxesIncluded
                taxShipping
                customerAccounts
                plan {
                    displayName
                    shopifyPlus
                    partnerDevelopment
                }
                billingAddress {
                    address1
                    address2
                    city
                    company
                    country
                    countryCodeV2
                    province
                    provinceCode
                    zip
                    phone
                }
                description
                createdAt
                updatedAt
                url
            }
        }
        """
        
        # Execute the query
        def execute_query(access_token, store_domain, api_version):
            return execute_graphql_query(access_token, store_domain, api_version, query_str)
        
        data = call_shopify_api(execute_query, user_id)
        shop = data['data']['shop']
        
        response_text = f"""# Store Details - {shop['name']}

## Basic Information
**Store Name:** {shop['name']}
**Store ID:** {shop['id']}
**Domain:** {shop['myshopifyDomain']}
**Primary Domain:** {shop['primaryDomain']['url']}
**SSL Enabled:** {'Yes' if shop['primaryDomain']['sslEnabled'] else 'No'}
**Store URL:** {shop['url']}

## Contact Information
**Email:** {shop['email']}
**Contact Email:** {shop.get('contactEmail', 'Not provided')}

## Store Settings
**Currency:** {shop['currencyCode']}
**Money Format:** {shop['currencyFormats']['moneyFormat']}
**Money with Currency Format:** {shop['currencyFormats']['moneyWithCurrencyFormat']}
**Timezone:** {shop['ianaTimezone']} ({shop['timezoneAbbreviation']})
**Weight Unit:** {shop['weightUnit']}
**Unit System:** {shop['unitSystem']}

## Features
**Checkout API Supported:** {'Yes' if shop['checkoutApiSupported'] else 'No'}
**Taxes Included:** {'Yes' if shop['taxesIncluded'] else 'No'}
**Tax Shipping:** {'Yes' if shop['taxShipping'] else 'No'}
**Customer Accounts:** {shop['customerAccounts']}

## Plan Information
**Plan:** {shop['plan']['displayName']}
**Shopify Plus:** {'Yes' if shop['plan']['shopifyPlus'] else 'No'}
**Partner Development:** {'Yes' if shop['plan']['partnerDevelopment'] else 'No'}

## Billing Address
**Company:** {shop['billingAddress'].get('company', 'Not provided')}
**Address:** {shop['billingAddress']['address1']}
{f"**Address 2:** {shop['billingAddress']['address2']}" if shop['billingAddress'].get('address2') else ""}
**City:** {shop['billingAddress']['city']}
**Province:** {shop['billingAddress']['province']} ({shop['billingAddress']['provinceCode']})
**Country:** {shop['billingAddress']['country']} ({shop['billingAddress']['countryCodeV2']})
**ZIP:** {shop['billingAddress']['zip']}
**Phone:** {shop['billingAddress'].get('phone', 'Not provided')}

## Store Description
{shop.get('description', 'No description provided')}

## Timestamps
**Created:** {datetime.fromisoformat(shop['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.fromisoformat(shop['updatedAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}

---
*Store details retrieved from Shopify Admin API*"""
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=response_text
            )]
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ Error: {str(e)}"
            )]
        )

# ---------------------------
# System Prompt for Shopify MCP Server
# ---------------------------

def get_shopify_system_prompt() -> str:
    """Get the system prompt for Shopify MCP Server operations."""
    return """
    You are a Shopify assistant with access to the 'Shopify MCP Server'.
    This server provides tools to perform Shopify store operations using the Shopify Admin API.

    ## Shopify Server Rules:
    1. Only use tools provided by MCP discovery.
    2. Never invent tool names — only use tools provided by MCP discovery.
    3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
    4. For Shopify operations, always require a user_id parameter for authentication.
    5. When analyzing store data, provide comprehensive analytics and insights.
    6. For product/order/customer operations, specify appropriate filters and limits.
    7. Shopify operations include: store analytics, customer management, order processing, product catalog, and inventory management.
    8. Handle authentication errors gracefully - inform users if re-authentication is needed.
    9. For data listings, return comprehensive information including IDs, names, dates, and relevant metrics.
    10. When users ask about "my store" or "my products", use the appropriate tools with their user_id.
    11. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    12. If no user_id is provided in the query, ask the user to provide one.
    13. For Shopify operations, always specify which action you're performing (get, analyze, search, etc.).
    14. When analyzing data, provide meaningful insights and trends.
    15. For inventory operations, highlight low stock and out-of-stock items.
    16. Always use conversation_id for all Shopify operations after the initial learn_shopify_api call.

    ## Available Shopify Operations:
    - get_user_credentials: Check Shopify credentials status
    - learn_shopify_api: MANDATORY FIRST STEP - Learn about Shopify APIs and get conversation_id
    - get_store_analytics: Get comprehensive store analytics and statistics
    - get_customers: Retrieve customer information with filtering
    - get_orders: Get order information with status filtering
    - get_products: Retrieve product catalog with search and filtering
    - get_inventory: Get inventory levels and stock information
    - get_store_details: Get comprehensive store configuration details

    ## Authentication:
    - All operations require valid Shopify credentials stored in the database
    - User_id is used to retrieve the appropriate credentials
    - If authentication fails, inform the user to check their credentials
    - Shopify API requires access token, store domain, and API version

    ## Data Analysis:
    - Store analytics include orders, products, customers, and revenue metrics
    - Date ranges can be filtered (today, yesterday, last_7_days, last_30_days, last_90_days, all_time)
    - Inventory analysis highlights stock levels and availability
    - Customer analysis includes spending patterns and order history

    ## Conversation Management:
    - ALWAYS call learn_shopify_api first to get conversation_id
    - Use the returned conversation_id in ALL subsequent Shopify operations
    - Without conversation_id, all other Shopify tools will return errors

    ## Error Handling:
    - Handle API rate limits gracefully
    - Provide clear error messages for authentication failures
    - Suggest re-authentication when tokens are expired
    - Inform users about Shopify API limitations and quotas
    - Handle store permission errors appropriately
    - Guide users through the conversation_id requirement
    """

if __name__ == "__main__":
    asyncio.run(mcp.run())
