#!/usr/bin/env python
# Copyright 2018 Google LLC
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
"""This example updates a campaign.

To get campaigns, run get_campaigns.py.
"""


import argparse
import sys
from typing import List

from google.api_core import protobuf_helpers

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v21.resources.types.campaign import Campaign
from google.ads.googleads.v21.services.services.campaign_service import (
    CampaignServiceClient,
)
from google.ads.googleads.v21.services.types.campaign_service import (
    CampaignOperation,
    MutateCampaignsResponse,
)


def update_campaign_main(client: GoogleAdsClient, campaign_id: str, field_name: str, new_value: str) -> dict:
    """Update a specific campaign field.
    
    Args:
        client: GoogleAdsClient instance
        campaign_id: The campaign ID to update
        field_name: The field name to update (e.g., 'budget', 'name', 'status')
        new_value: The new value for the field
        
    Returns:
        dict: Response with status and message
    """
    try:
        # Extract customer ID from campaign ID if it contains underscore
        if '_' in campaign_id:
            customer_id, actual_campaign_id = campaign_id.split('_', 1)
        else:
            # Assume the campaign_id is just the campaign ID, use login_customer_id
            customer_id = None
            actual_campaign_id = campaign_id
            
        campaign_service: CampaignServiceClient = client.get_service(
            "CampaignService"
        )
        
        # Create campaign operation.
        campaign_operation: CampaignOperation = client.get_type("CampaignOperation")
        campaign: Campaign = campaign_operation.update

        if customer_id:
            campaign.resource_name = campaign_service.campaign_path(
                customer_id, actual_campaign_id
            )
        else:
            # Use the campaign_id directly if it's a resource name
            campaign.resource_name = campaign_id

        # Update specific fields based on field_name
        if field_name.lower() == 'status':
            if new_value.lower() == 'paused':
                campaign.status = client.enums.CampaignStatusEnum.PAUSED
            elif new_value.lower() == 'enabled':
                campaign.status = client.enums.CampaignStatusEnum.ENABLED
            elif new_value.lower() == 'removed':
                campaign.status = client.enums.CampaignStatusEnum.REMOVED
        elif field_name.lower() == 'name':
            campaign.name = new_value
        elif field_name.lower() == 'budget':
            # Convert to micros (Google Ads uses micros for currency amounts)
            try:
                budget_micros = int(float(new_value) * 1000000)
                campaign.campaign_budget = f"customers/{customer_id}/campaignBudgets/{budget_micros}"
            except ValueError:
                return {"status": 1, "error": "Invalid budget value. Must be a number."}
        else:
            return {"status": 1, "error": f"Unsupported field: {field_name}"}

        # Retrieve a FieldMask for the fields configured in the campaign.
        client.copy_from(
            campaign_operation.update_mask,
            protobuf_helpers.field_mask(None, campaign._pb),
        )

        operations: List[CampaignOperation] = [campaign_operation]

        campaign_response: MutateCampaignsResponse = (
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=operations,
            )
        )

        return {
            "status": 0,
            "message": f"Updated campaign {campaign_response.results[0].resource_name}.",
            "campaign_id": actual_campaign_id,
            "field_updated": field_name,
            "new_value": new_value
        }
        
    except GoogleAdsException as ex:
        return {
            "status": 1,
            "error": f"Google Ads API error: {ex.error.code().name}",
            "request_id": ex.request_id
        }
    except Exception as e:
        return {
            "status": 1,
            "error": f"Unexpected error: {str(e)}"
        }


def main(client: GoogleAdsClient, customer_id: str, campaign_id: str) -> None:
    """Legacy main function for backward compatibility."""
    result = update_campaign_main(client, campaign_id, "status", "paused")
    if result["status"] == 0:
        print(result["message"])
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Updates the given campaign for the specified customer."
    )
    # The following argument(s) should be provided to run the example.
    parser.add_argument(
        "-c",
        "--customer_id",
        type=str,
        required=True,
        help="The Google Ads customer ID.",
    )
    parser.add_argument(
        "-i", "--campaign_id", type=str, required=True, help="The campaign ID."
    )
    args: argparse.Namespace = parser.parse_args()

    # GoogleAdsClient will read the google-ads.yaml configuration file in the
    # home directory if none is specified.
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_storage(
        version="v21"
    )

    try:
        main(googleads_client, args.customer_id, args.campaign_id)
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

      