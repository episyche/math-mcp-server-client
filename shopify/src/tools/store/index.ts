import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for get-store-details
const GetStoreDetailsInputSchema = z.object({
  conversationId: z.string().describe("The conversation ID for tracking"),
});

type GetStoreDetailsInput = z.infer<typeof GetStoreDetailsInputSchema>;

// Type for store details response
interface StoreDetailsResponse {
  id: string;
  name: string;
  myshopifyDomain: string;
  primaryDomain: {
    host: string;
    url: string;
    sslEnabled: boolean;
  };
  email: string;
  contactEmail: string;
  currencyCode: string;
  currencyFormats: {
    moneyFormat: string;
    moneyWithCurrencyFormat: string;
  };
  ianaTimezone: string;
  timezoneAbbreviation: string;
  timezoneOffset: string;
  weightUnit: string;
  unitSystem: string;
  checkoutApiSupported: boolean;
  taxesIncluded: boolean;
  taxShipping: boolean;
  customerAccounts: string;
  plan: {
    displayName: string;
    shopifyPlus: boolean;
    partnerDevelopment: boolean;
  };
  billingAddress: {
    address1: string;
    address2: string;
    city: string;
    company: string;
    country: string;
    countryCodeV2: string;
    province: string;
    provinceCode: string;
    zip: string;
    phone: string;
  };
  description: string;
  createdAt: string;
  updatedAt: string;
  url: string;
}

// GraphQL query to get store details
const GET_STORE_DETAILS_QUERY = gql`
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
`;

// GraphQL client for Shopify Admin API
let shopifyClient: GraphQLClient | null = null;

// Initialize GraphQL client with Shopify Admin API credentials
function initializeShopifyClient(): GraphQLClient {
  if (shopifyClient) {
    return shopifyClient;
  }

  const accessToken = process.env.SHOPIFY_ACCESS_TOKEN;
  const storeDomain = process.env.SHOPIFY_STORE_DOMAIN;

  if (!accessToken || !storeDomain) {
    throw new Error(
      "Shopify Admin API credentials not found. Please set SHOPIFY_ACCESS_TOKEN and SHOPIFY_STORE_DOMAIN environment variables."
    );
  }

  // Ensure store domain has proper format
  const normalizedDomain = storeDomain.replace(/^https?:\/\//, '').replace(/\/$/, '');
  const graphqlEndpoint = `https://${normalizedDomain}/admin/api/2025-07/graphql.json`;

  shopifyClient = new GraphQLClient(graphqlEndpoint, {
    headers: {
      'X-Shopify-Access-Token': accessToken,
      'Content-Type': 'application/json',
    },
  });

  return shopifyClient;
}

// Function to get store details
async function getStoreDetails(input: GetStoreDetailsInput): Promise<StoreDetailsResponse> {
  try {
    // Initialize GraphQL client
    const client = initializeShopifyClient();

    // Execute the query
    const data = await client.request(GET_STORE_DETAILS_QUERY) as { shop: StoreDetailsResponse };

    if (!data.shop) {
      throw new Error("Failed to retrieve store details");
    }

    // Record usage after successful execution
    recordUsage("get-store-details", input, data.shop);

    return data.shop;
  } catch (error) {
    console.error("Error fetching store details:", error);
    // Record usage even on error
    recordUsage("get-store-details", input, { error: error instanceof Error ? error.message : 'Unknown error' });
    throw new Error(`Failed to fetch store details: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// Tool to get store details
const getStoreDetailsTool = {
  name: "get-store-details",
  description: "Get comprehensive store details from Shopify Admin API including store information, settings, and configuration",
  inputSchema: GetStoreDetailsInputSchema,
  execute: getStoreDetails,
};

// Export the tool
export { getStoreDetailsTool };

// Default export for MCP server registration
export default async function storeTool(server: McpServer) {
  server.tool(
    "get_store_details",
    "Get comprehensive store details from Shopify Admin API including store information, settings, and configuration",
    withConversationId({}),
    async (params) => {
      try {
        const storeDetails = await getStoreDetails({
          conversationId: params.conversationId,
        });

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(storeDetails, null, 2),
            },
          ],
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        
        // Provide helpful error message with setup instructions
        if (errorMessage.includes("Shopify Admin API credentials not found")) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Error: ${errorMessage}

To fix this issue, please set up your Shopify Admin API credentials as environment variables:

Required Environment Variables:
- SHOPIFY_ACCESS_TOKEN: Your private app access token
- SHOPIFY_STORE_DOMAIN: Your store domain (e.g., "your-store.myshopify.com")

Example setup:
export SHOPIFY_ACCESS_TOKEN="shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"

For more information on setting up Shopify Admin API access, visit:
https://shopify.dev/docs/apps/auth/oauth/getting-started`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: "text" as const,
              text: `Error fetching store details: ${errorMessage}`,
            },
          ],
          isError: true,
        };
      }
    },
  );
}



