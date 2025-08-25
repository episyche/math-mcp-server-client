#!/usr/bin/env python
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This example illustrates how to get all campaigns.

To add campaigns, run add_campaigns.py.
"""


import argparse
import sys
from typing import Iterator, List

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v21.services.services.google_ads_service import (
    GoogleAdsServiceClient,
)
from google.ads.googleads.v21.services.types.google_ads_service import (
    SearchGoogleAdsStreamResponse,
    GoogleAdsRow,
)


def get_campaign_main(client: GoogleAdsClient, customer_id: str) -> dict:
    """Get all campaigns for a customer.
    
    Args:
        client: GoogleAdsClient instance
        customer_id: The customer ID
        
    Returns:
        dict: Response with status, message, and campaign data
    """
    try:
        ga_service: GoogleAdsServiceClient = client.get_service("GoogleAdsService")

        query: str = """
            SELECT
              campaign.id,
              campaign.name,
              campaign.status,
              campaign.advertising_channel_type
            FROM campaign
            ORDER BY campaign.id"""

        # Issues a search request using streaming.
        stream: Iterator[SearchGoogleAdsStreamResponse] = ga_service.search_stream(
            customer_id=customer_id, query=query
        )

        campaigns = []
        for batch in stream:
            rows: List[GoogleAdsRow] = batch.results
            for row in rows:
                campaign_info = {
                    "id": row.campaign.id,
                    "name": row.campaign.name,
                    "status": str(row.campaign.status),
                    "advertising_channel_type": str(row.campaign.advertising_channel_type)
                }
                campaigns.append(campaign_info)

        if campaigns:
            return {
                "status": 0,
                "message": f"Found {len(campaigns)} campaigns for customer {customer_id}",
                "campaigns": campaigns,
                "count": len(campaigns)
            }
        else:
            return {
                "status": 0,
                "message": f"No campaigns found for customer {customer_id}",
                "campaigns": [],
                "count": 0
            }
            
    except GoogleAdsException as ex:
        return {
            "status": 1,
            "error": f"Google Ads API error: {ex.error.code().name}",
            "request_id": ex.request_id,
            "message": f'Request with ID "{ex.request_id}" failed with status "{ex.error.code().name}".'
        }
    except Exception as e:
        return {
            "status": 1,
            "error": f"Unexpected error: {str(e)}"
        }


def main(client: GoogleAdsClient, customer_id: str) -> None:
    """Legacy main function for backward compatibility."""
    result = get_campaign_main(client, customer_id)
    if result["status"] == 0:
        print(result["message"])
        if result.get("campaigns"):
            for campaign in result["campaigns"]:
                print(f"Campaign with ID {campaign['id']} and name '{campaign['name']}' was found.")
    else:
        print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lists all campaigns for specified customer."
    )
    # The following argument(s) should be provided to run the example.
    parser.add_argument(
        "-c",
        "--customer_id",
        type=str,
        required=True,
        help="The Google Ads customer ID.",
    )
    args: argparse.Namespace = parser.parse_args()

    # GoogleAdsClient will read the google-ads.yaml configuration file in the
    # home directory if none is specified.
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_storage(
        version="v21"
    )

    try:
        main(googleads_client, args.customer_id)
    except GoogleAdsException as ex:
        print(
            f'Request with ID "{ex.request_id}" failed with status '
            f'"{ex.error.code().name}" and includes the following errors:'
        )
        for error in ex.failure.errors:
            print(f'\tError with message "{error.message}".')
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}")
        sys.exit(1)

      