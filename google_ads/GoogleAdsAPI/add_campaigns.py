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
"""This example illustrates how to add a campaign.

To get campaigns, run get_campaigns.py.
"""


import argparse
import datetime
import sys
from typing import List
import uuid

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v21.services.services.campaign_budget_service import (
    CampaignBudgetServiceClient,
)
from google.ads.googleads.v21.services.types.campaign_budget_service import (
    CampaignBudgetOperation,
    MutateCampaignBudgetsResponse,
)
from google.ads.googleads.v21.services.services.campaign_service import (
    CampaignServiceClient,
)
from google.ads.googleads.v21.services.types.campaign_service import (
    CampaignOperation,
    MutateCampaignsResponse,
)
from google.ads.googleads.v21.resources.types.campaign_budget import (
    CampaignBudget,
)
from google.ads.googleads.v21.resources.types.campaign import Campaign


_DATE_FORMAT: str = "%Y%m%d"


def handle_googleads_exception(exception: GoogleAdsException) -> dict:
    """Handle Google Ads API exceptions and return formatted error response."""
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


def add_campaign_main(client: GoogleAdsClient, customer_id: str) -> dict:
    """Add a new campaign for the specified customer.
    
    Args:
        client: GoogleAdsClient instance
        customer_id: The customer ID to add the campaign to
        
    Returns:
        dict: Response with status and message
    """
    try:
        campaign_budget_service: CampaignBudgetServiceClient = client.get_service(
            "CampaignBudgetService"
        )
        campaign_service: CampaignServiceClient = client.get_service(
            "CampaignService"
        )

        # [START add_campaigns]
        # Create a budget, which can be shared by multiple campaigns.
        campaign_budget_operation: CampaignBudgetOperation = client.get_type(
            "CampaignBudgetOperation"
        )
        campaign_budget: CampaignBudget = campaign_budget_operation.create
        campaign_budget.name = f"Interplanetary Budget {uuid.uuid4()}"
        campaign_budget.delivery_method = (
            client.enums.BudgetDeliveryMethodEnum.STANDARD
        )
        campaign_budget.amount_micros = 500000

        # Add budget.
        campaign_budget_response: MutateCampaignBudgetsResponse
        try:
            budget_operations: List[CampaignBudgetOperation] = [
                campaign_budget_operation
            ]
            campaign_budget_response = (
                campaign_budget_service.mutate_campaign_budgets(
                    customer_id=customer_id,
                    operations=budget_operations,
                )
            )
        except GoogleAdsException as ex:
            return handle_googleads_exception(ex)

        # [START add_campaigns_1]
        # Create campaign.
        campaign_operation: CampaignOperation = client.get_type("CampaignOperation")
        campaign: Campaign = campaign_operation.create
        campaign.name = f"Interplanetary Cruise {uuid.uuid4()}"
        campaign.advertising_channel_type = (
            client.enums.AdvertisingChannelTypeEnum.SEARCH
        )

        # Recommendation: Set the campaign to PAUSED when creating it to prevent
        # the ads from immediately serving. Set to ENABLED once you're ready to
        # add ads.
        campaign.status = client.enums.CampaignStatusEnum.PAUSED

        # Set the bidding strategy and budget.
        campaign.manual_cpc = client.get_type("ManualCpc")
        campaign.campaign_budget = campaign_budget_response.results[0].resource_name

        # Set the campaign network options.
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_partner_search_network = False
        # Enable Display Expansion on Search campaigns. For more details see:
        # https://support.google.com/google-ads/answer/7193800
        campaign.network_settings.target_content_network = True

        # Declare whether or not this campaign serves political ads targeting the
        # EU. Valid values are:
        #   CONTAINS_EU_POLITICAL_ADVERTISING
        #   DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        campaign.contains_eu_political_advertising = (
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        )

        # Optional: Set the start date.
        start_time: datetime.date = datetime.date.today() + datetime.timedelta(
            days=1
        )
        campaign.start_date = datetime.date.strftime(start_time, _DATE_FORMAT)

        # Optional: Set the end date.
        end_time: datetime.date = start_time + datetime.timedelta(weeks=4)
        campaign.end_date = datetime.date.strftime(end_time, _DATE_FORMAT)
        # [END add_campaigns_1]

        # Add the campaign.
        campaign_response: MutateCampaignsResponse
        try:
            campaign_operations: List[CampaignOperation] = [campaign_operation]
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id, operations=campaign_operations
            )
            message = f"Created campaign {campaign_response.results[0].resource_name}."
            return {
                "status": 0,  
                "message": message,
                "campaign_id": campaign_response.results[0].resource_name,
                "budget_id": campaign_budget_response.results[0].resource_name
            }
            
        except GoogleAdsException as ex:
            return handle_googleads_exception(ex)
            
    except Exception as e:
        return {
            "status": 1,
            "error": f"Unexpected error: {str(e)}"
        }


def main(client: GoogleAdsClient, customer_id: str) -> None:
    """Legacy main function for backward compatibility."""
    result = add_campaign_main(client, customer_id)
    if result["status"] == 0:
        print(result["message"])
    else:
        print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Adds a campaign for specified customer."
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