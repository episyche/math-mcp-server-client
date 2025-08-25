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
"""This example removes an existing campaign."""


import argparse
import sys
from typing import List

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v21.services.services.campaign_service import (
    CampaignServiceClient,
)
from google.ads.googleads.v21.services.types.campaign_service import (
    CampaignOperation,
    MutateCampaignsResponse,
)


def remove_campaign_main(client: GoogleAdsClient, customer_id: str, campaign_id: str) -> dict:
    """Remove an existing campaign.
    
    Args:
        client: GoogleAdsClient instance
        customer_id: The customer ID
        campaign_id: The campaign ID to remove
        
    Returns:
        dict: Response with status and message
    """
    try:
        campaign_service: CampaignServiceClient = client.get_service(
            "CampaignService"
        )
        campaign_operation: CampaignOperation = client.get_type("CampaignOperation")

        resource_name: str = campaign_service.campaign_path(
            customer_id, campaign_id
        )
        campaign_operation.remove = resource_name

        operations: List[CampaignOperation] = [campaign_operation]

        campaign_response: MutateCampaignsResponse = (
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=operations,
            )
        )

        return {
            "status": 0,
            "message": f"Removed campaign {campaign_response.results[0].resource_name}.",
            "campaign_id": campaign_response.results[0].resource_name,
            "customer_id": customer_id
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


def main(client: GoogleAdsClient, customer_id: str, campaign_id: str) -> None:
    """Legacy main function for backward compatibility."""
    result = remove_campaign_main(client, customer_id, campaign_id)
    if result["status"] == 0:
        print(result["message"])
    else:
        print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=("Removes given campaign for the specified customer.")
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