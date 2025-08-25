from __future__ import annotations
import requests
import os
import base64
import sys
from datetime import datetime
import os
from dotenv import load_dotenv
import pytz
from pytz import country_timezones
from countryinfo import CountryInfo

from mcp.server.fastmcp import FastMCP
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# Import the GoogleAdsAPI functions
from GoogleAdsAPI.create_customer import create_customer_main
from GoogleAdsAPI.add_campaigns import add_campaign_main
from GoogleAdsAPI.remove_campaign import remove_campaign_main
from GoogleAdsAPI.get_campaign import get_campaign_main
from GoogleAdsAPI.add_ad_group import add_ad_group_main
from GoogleAdsAPI.update_campaign import update_campaign_main

load_dotenv()

config_dict = {
    "developer_token": os.getenv("DEVELOPER_TOKEN"),
    "client_id": os.getenv("CLIENT_ID"),
    "client_secret": os.getenv("CLIENT_SECRET"),
    "refresh_token": os.getenv("REFRESH_TOKEN"),
    "login_customer_id": os.getenv("LOGIN_CUSTOMER_ID"),
    "use_proto_plus": True,
}

mcp = FastMCP("Google-Ads-Server")

def handle_googleads_exception(exception: GoogleAdsException) -> dict:
    status_code = exception.error.code().value
    status_name = exception.error.code().name
    if(status_name == "UNAUTHENTICATED"):
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

@mcp.tool() 
def create_customer(a: str):
    """Create a new Google Ads customer account.
    
    Args:
        a: Country name for the customer account
    """
    country = CountryInfo(a)
    try:
        currencies = country.currencies()
        currency = currencies[0] if currencies else "USD"
    except:
        currency = "USD"
    
    try:
        country_info = country.info()
        country_code = country_info.get('ISO2')
        if country_code is None:
            country_code = "US" 
    except:
        country_code = "US" 
        
    try:
        timezones = country_timezones.get(country_code, ["UTC"])
        timezone = timezones[0] if timezones else "UTC"
    except:
        timezone = "UTC"
    
    data = {"timezone": timezone, "currency": currency}
    
    googleads_client = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = create_customer_main(googleads_client, config_dict["login_customer_id"], data)
        return response
    except GoogleAdsException as ex:
        return handle_googleads_exception(ex)

@mcp.tool() 
def add_campaign(a: str):
    """Add a new campaign for a customer.
    
    Args:
        a: Customer ID for the campaign
    """
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = add_campaign_main(googleads_client, a)
        return response
    except GoogleAdsException as ex:
        return handle_googleads_exception(ex)

@mcp.tool() 
def remove_campaign(a: str, b: str):
    """Remove a campaign for a customer.
    
    Args:
        a: Customer ID
        b: Campaign ID to remove
    """
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = remove_campaign_main(googleads_client, a, b)
        return response
    except GoogleAdsException as ex:
        response = handle_googleads_exception(ex)
        return response

@mcp.tool()
def get_campaign(a: str):
    """Get campaign details for a customer.
    
    Args:
        a: Customer ID
    """
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = get_campaign_main(googleads_client, a)
        return response
    except GoogleAdsException as ex:
        response = handle_googleads_exception(ex)
        return response

@mcp.tool()
def add_ad_group(a: str, b: str):
    """Add an ad group to a campaign.
    
    Args:
        a: Ad group name
        b: Campaign ID
    """
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = add_ad_group_main(googleads_client, a, b)
        return response
    except GoogleAdsException as ex:
        response = handle_googleads_exception(ex)
        return response

@mcp.tool()
def update_campaign(a: str, b: str, c: str):
    """Update a campaign field.
    
    Args:
        a: Campaign ID
        b: Field to update (e.g., 'budget', 'name')
        c: New value for the field
    """
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_dict(config_dict, version="v21")
    try:
        response = update_campaign_main(googleads_client, a, b, c)
        return response
    except GoogleAdsException as ex:
        response = handle_googleads_exception(ex)
        return response

if __name__ == "__main__":
    # Uses stdio transport by default when launched by an MCP-capable client
    mcp.run()
