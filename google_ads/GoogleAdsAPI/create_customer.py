
"""This example illustrates how to create a new customer under a given
manager account.

Note: this example must be run using the credentials of a Google Ads manager
account. By default, the new account will only be accessible via the manager
account.
"""


import argparse
import sys
from datetime import datetime
import os
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v21.resources.types.customer import Customer
from google.ads.googleads.v21.services.services.customer_service.client import (
    CustomerServiceClient,
)
from google.ads.googleads.v21.services.types.customer_service import (
    CreateCustomerClientResponse,
)

load_dotenv()

config_dict = {
    "developer_token": os.getenv("DEVELOPER_TOKEN"),
    "client_id": os.getenv("CLIENT_ID"),
    "client_secret": os.getenv("CLIENT_SECRET"),
    "refresh_token": os.getenv("REFRESH_TOKEN"),
    "login_customer_id": os.getenv("LOGIN_CUSTOMER_ID"),
    "use_proto_plus": True,
}


def create_customer_main(client: GoogleAdsClient, manager_customer_id: str, data: dict) -> dict:
    """Create a new customer under a manager account.
    
    Args:
        client: an initialized GoogleAdsClient instance.
        manager_customer_id: a manager client customer ID.
        data: dictionary containing timezone and currency information
        
    Returns:
        dict: Response with status and message
    """
    try:
        customer_service: CustomerServiceClient = client.get_service("CustomerService")
        customer: Customer = client.get_type("Customer")
        now: str = datetime.today().strftime("%Y%m%d %H:%M:%S")
        customer.descriptive_name = f"Account created with CustomerService on {now}"
        
        # For a list of valid currency codes and time zones see this documentation:
        # https://developers.google.com/google-ads/api/reference/data/codes-formats
        
        customer.currency_code = data["currency"]
        customer.time_zone = data["timezone"]
        
        # The below values are optional. For more information about URL
        # options see: https://support.google.com/google-ads/answer/6305348
        
        customer.tracking_url_template = "{lpurl}?device={device}"
        customer.final_url_suffix = (
            "keyword={keyword}&matchtype={matchtype}&adgroupid={adgroupid}"
        )

        response: CreateCustomerClientResponse = (
            customer_service.create_customer_client(
                customer_id=manager_customer_id, customer_client=customer
            )
        )
        message = (
            f'Customer created with resource name "{response.resource_name}" '
            f'under manager account with ID "{manager_customer_id}".'
        )

        return {
            "status": 0,
            "message": message,
            "customer_id": response.resource_name,
            "manager_customer_id": manager_customer_id,
            "currency": data["currency"],
            "timezone": data["timezone"]
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


def main(client: GoogleAdsClient, manager_customer_id: str, data: dict) -> None:
    """Legacy main function for backward compatibility."""
    result = create_customer_main(client, manager_customer_id, data)
    if result["status"] == 0:
        print(result["message"])
    else:
        print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates a new customer under a manager account."
    )
    # The following argument(s) should be provided to run the example.
    parser.add_argument(
        "-c",
        "--customer_id",
        type=str,
        required=True,
        help="The Google Ads manager customer ID.",
    )
    args: argparse.Namespace = parser.parse_args()

    # GoogleAdsClient will read the google-ads.yaml configuration file in the
    # home directory if none is specified.
    googleads_client: GoogleAdsClient = GoogleAdsClient.load_from_storage(
        version="v21"
    )

    try:
        # Create sample data for testing
        test_data = {"timezone": "America/New_York", "currency": "USD"}
        main(googleads_client, args.customer_id, test_data)
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
