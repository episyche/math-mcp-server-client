#!/usr/bin/env python3
"""
Google Ads MCP Server - Database credentials version
"""

import os
import json
import logging
import requests
import base64
import sys
import pytz
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from pytz import country_timezones
from countryinfo import CountryInfo

# MCP imports
from mcp.server import Server
from mcp.types import CallToolResult, TextContent

# Google Ads imports
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Import common database utilities
from db_utils import get_google_ads_minion_credentials, update_google_ads_tokens_in_db

# Load .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = Server("google-ads-mcp-server")

def get_google_ads_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Get Google Ads credentials for a user."""
    return get_google_ads_minion_credentials(user_id)

def get_access_token(refresh_token: str, client_id: str, client_secret: str) -> Optional[str]:
    """Get Google Ads access token using refresh token."""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url=url, data=payload)
        response.raise_for_status()
        token = response.json()["access_token"]
        return token
    except Exception as e:
        logger.error(f"Failed to get access token: {e}")
        return None

def create_google_ads_client(user_id: str) -> Optional[GoogleAdsClient]:
    """Create Google Ads client using credentials from database."""
    try:
        creds = get_google_ads_credentials(user_id)
        if not creds:
            logger.error(f"No Google Ads credentials found for user {user_id}")
            return None
        
        # Get access token
        access_token = get_access_token(
            creds.get('google_ads_refresh_token'),
            creds.get('google_ads_client_id'),
            creds.get('google_ads_client_secret')
        )
        
        if not access_token:
            logger.error("Failed to get access token")
            return None
        
        config_dict = {
            "developer_token": creds.get('google_ads_developer_token'),
            "client_id": creds.get('google_ads_client_id'),
            "client_secret": creds.get('google_ads_client_secret'),
            "refresh_token": creds.get('google_ads_refresh_token'),
            "login_customer_id": creds.get('google_ads_login_customer_id'),
            "use_proto_plus": True,
        }
        
        return GoogleAdsClient.load_from_dict(config_dict, version="v21")
        
    except Exception as e:
        logger.error(f"Error creating Google Ads client: {e}")
        return None

def handle_googleads_exception(exception: GoogleAdsException) -> Dict[str, Any]:
    """Handle Google Ads API exceptions."""
    status_code = exception.error.code().value
    status_name = exception.error.code().name
    
    if status_name == "UNAUTHENTICATED":
        message = (f'Request with ID "{exception.request_id}" failed with status '
                   f'"{status_name}"')
        return {
            "status": status_code,
            "name": status_name,
            "message": message
        }
    
    error_messages = []
    for error in exception.failure.errors:
        msg = f'Error with message "{error.message}".'
        error_messages.append(msg)
        if error.location:
            for field_path_element in error.location.field_path_elements:
                error_messages.append(f"On field: {field_path_element.field_name}")

    return {
        "status": status_code,
        "name": status_name,
        "message": f'Request with ID "{exception.request_id}" failed with status "{status_name}".',
        "errors": error_messages
    }

# Google Ads API helper functions
def list_accessible_customer(client):
    """Get list of accessible customer IDs."""
    try:
        customer_service = client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()
        return [customer.split('/')[-1] for customer in accessible_customers.resource_names]
    except Exception as e:
        logger.error(f"Error getting accessible customers: {e}")
        return []

def create_customer_main(client, manager_id, data):
    """Create a new customer under a manager account."""
    try:
        customer_service = client.get_service("CustomerService")
        customer = client.get_type("Customer")
        
        now = datetime.today().strftime("%Y%m%d %H:%M:%S")
        customer.descriptive_name = f"Account created with CustomerService on {now}"
        customer.currency_code = data["currency"]
        customer.time_zone = data["timezone"]
        customer.tracking_url_template = "{lpurl}?device={device}"
        customer.final_url_suffix = "keyword={keyword}&matchtype={matchtype}&adgroupid={adgroupid}"

        response = customer_service.create_customer_client(
            customer_id=manager_id, customer_client=customer
        )
        
        return {
            "status": "success",
            "message": f'Customer created with resource name "{response.resource_name}" under manager account with ID "{manager_id}".',
            "resource_name": response.resource_name
        }
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        return {"status": "error", "message": str(e)}

def add_campaign_main(client, customer_id):
    """Add a new campaign."""
    try:
        campaign_service = client.get_service("CampaignService")
        campaign_operation = client.get_type("CampaignOperation")
        
        campaign = campaign_operation.create
        campaign.name = f"Campaign #{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.campaign_budget = f"customers/{customer_id}/campaignBudgets/1"
        
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_operation]
        )
        
        return {
            "status": "success",
            "message": f"Campaign created successfully",
            "resource_name": response.results[0].resource_name
        }
    except Exception as e:
        logger.error(f"Error adding campaign: {e}")
        return {"status": "error", "message": str(e)}

def remove_campaign_main(client, customer_id, campaign_id):
    """Remove a campaign."""
    try:
        campaign_service = client.get_service("CampaignService")
        campaign_operation = client.get_type("CampaignOperation")
        campaign_operation.remove = f"customers/{customer_id}/campaigns/{campaign_id}"
        
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[campaign_operation]
        )
        
        return {
            "status": "success",
            "message": f"Campaign {campaign_id} removed successfully"
        }
    except Exception as e:
        logger.error(f"Error removing campaign: {e}")
        return {"status": "error", "message": str(e)}

def get_campaign_main(client, customer_id):
    """Get campaign information."""
    try:
        googleads_service = client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type
            FROM campaign
            ORDER BY campaign.id
        """
        
        campaigns = []
        response = googleads_service.search(customer_id=customer_id, query=query)
        
        for row in response:
            campaign_info = {
                "id": row.campaign.id,
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "advertising_channel_type": row.campaign.advertising_channel_type.name
            }
            campaigns.append(campaign_info)
        
        return {
            "status": "success",
            "campaigns": campaigns,
            "count": len(campaigns)
        }
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        return {"status": "error", "message": str(e)}

def add_ad_group_main(client, customer_id, campaign_id):
    """Add an ad group to a campaign."""
    try:
        ad_group_service = client.get_service("AdGroupService")
        ad_group_operation = client.get_type("AdGroupOperation")
        
        ad_group = ad_group_operation.create
        ad_group.name = f"Ad Group #{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        ad_group.cpc_bid_micros = 1000000  # $1.00
        
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id, operations=[ad_group_operation]
        )
        
        return {
            "status": "success",
            "message": f"Ad group created successfully for campaign {campaign_id}",
            "resource_name": response.results[0].resource_name
        }
    except Exception as e:
        logger.error(f"Error adding ad group: {e}")
        return {"status": "error", "message": str(e)}

@mcp.call_tool()
def get_user_credentials(user_id: str):
    """Get Google Ads credentials for a user."""
    try:
        creds = get_google_ads_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No Google Ads credentials found for this user."
                )]
            )
        
        safe_info = {
            "user_id": user_id,
            "has_developer_token": bool(creds.get("google_ads_developer_token")),
            "has_client_id": bool(creds.get("google_ads_client_id")),
            "has_client_secret": bool(creds.get("google_ads_client_secret")),
            "has_refresh_token": bool(creds.get("google_ads_refresh_token")),
            "has_login_customer_id": bool(creds.get("google_ads_login_customer_id")),
            "minion_name": creds.get("minion_name")
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
def create_customer(user_id: str, manager_customer_id: str, country_code: str):
    """Create a new customer under a manager account."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        # Get country information
        country = CountryInfo(country_code)
        
        try:
            currencies = country.currencies()
            currency = currencies[0] if currencies else "USD"
        except:
            currency = "USD"
        
        try:
            country_code_iso = country.info()['ISO']['alpha2']
            timezones = pytz.country_timezones[country_code_iso]
            timezone = timezones[0]
        except:
            timezone = "UTC"
        
        data = {"timezone": timezone, "currency": currency}
        
        try:
            response = create_customer_main(googleads_client, manager_customer_id, data)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "create_customer",
                        "manager_customer_id": manager_customer_id,
                        "country_code": country_code,
                        "currency": currency,
                        "timezone": timezone,
                        "result": response
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "create_customer",
                        "error": error_response
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

@mcp.call_tool()
def add_campaign(user_id: str, customer_id: str):
    """Add a new campaign."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        try:
            response = add_campaign_main(googleads_client, customer_id)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "add_campaign",
                        "customer_id": customer_id,
                        "result": response
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "add_campaign",
                        "error": error_response
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

@mcp.call_tool()
def remove_campaign(user_id: str, customer_id: str, campaign_id: str):
    """Remove a campaign."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        try:
            response = remove_campaign_main(googleads_client, customer_id, campaign_id)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "remove_campaign",
                        "customer_id": customer_id,
                        "campaign_id": campaign_id,
                        "result": response
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "remove_campaign",
                        "error": error_response
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

@mcp.call_tool()
def get_campaign(user_id: str, customer_id: str):
    """Get campaign information."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        try:
            response = get_campaign_main(googleads_client, customer_id)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "get_campaign",
                        "customer_id": customer_id,
                        "result": response
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "get_campaign",
                        "error": error_response
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

@mcp.call_tool()
def add_ad_group(user_id: str, customer_id: str, campaign_id: str):
    """Add an ad group to a campaign."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        try:
            response = add_ad_group_main(googleads_client, customer_id, campaign_id)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "add_ad_group",
                        "customer_id": customer_id,
                        "campaign_id": campaign_id,
                        "result": response
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "add_ad_group",
                        "error": error_response
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

@mcp.call_tool()
def get_all_accounts(user_id: str, customer_id: str):
    """Get all accessible accounts."""
    try:
        googleads_client = create_google_ads_client(user_id)
        if not googleads_client:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to create Google Ads client. Check credentials."
                )]
            )
        
        try:
            googleads_service = googleads_client.get_service("GoogleAdsService")
            query = """
               SELECT
                 customer.id,
                 customer.descriptive_name,
                 customer.manager
               FROM customer
               """
            
            account_info = []
            user_accessible_accounts = list_accessible_customer(googleads_client)
            for id in user_accessible_accounts:
                response = googleads_service.search(customer_id=id, query=query)
                for row in response:
                    account_details = {
                         "customer_id": row.customer.id,
                         "name": row.customer.descriptive_name,
                         "is_manager": row.customer.manager
                    }
                    account_info.append(account_details)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "get_all_accounts",
                        "customer_id": customer_id,
                        "accounts": account_info
                    }, indent=2, ensure_ascii=False)
                )]
            )
        except GoogleAdsException as ex:
            error_response = handle_googleads_exception(ex)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "action": "get_all_accounts",
                        "error": error_response
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

@mcp.call_tool()
def get_all_client_accounts(user_id: str, manager_id: str):
    """Get all client accounts under a manager."""
    try:
        creds = get_google_ads_credentials(user_id)
        if not creds:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ No Google Ads credentials found for this user."
                )]
            )
        
        # Get access token
        access_token = get_access_token(
            creds.get('google_ads_refresh_token'),
            creds.get('google_ads_client_id'),
            creds.get('google_ads_client_secret')
        )
        
        if not access_token:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ Failed to get access token."
                )]
            )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": creds.get('google_ads_developer_token'),
            "Content-Type": "application/json"
        }
        
        url = f"https://googleads.googleapis.com/v21/customers/{manager_id}/googleAds:search"
        payload = {
            "query": "SELECT customer_client.id, customer_client.level, customer_client.hidden FROM customer_client",
            "searchSettings": {
                "omitResults": False,
                "returnSummaryRow": False,
                "returnTotalResultsCount": True
            }
        }
        
        response = requests.post(url=url, json=payload, headers=headers)
        response.raise_for_status()
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "action": "get_all_client_accounts",
                    "manager_id": manager_id,
                    "result": response.json()
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
    mcp.run()
