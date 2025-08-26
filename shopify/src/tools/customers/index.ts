import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for getCustomers
const GetCustomersInputSchema = z.object({
  limit: z.number().default(10).describe("Maximum number of customers to return (default: 10, max: 50)"),
  query: z.string().optional().describe("Search customers by name, email, or phone"),
  cursor: z.string().optional().describe("Cursor for pagination (from previous response)"),
  includeAddresses: z.boolean().default(true).describe("Include customer addresses in the response"),
  includeOrders: z.boolean().default(false).describe("Include customer order information (requires additional permissions)")
});

type GetCustomersInput = z.infer<typeof GetCustomersInputSchema>;

// Input schema for getCustomerCounts
const GetCustomerCountsInputSchema = z.object({
  countType: z.enum(['all', 'subscribed', 'unsubscribed', 'custom']).default('all').describe("Type of customer count to retrieve"),
  customQuery: z.string().optional().describe("Custom query for filtering customers (used when countType is 'custom')")
});

type GetCustomerCountsInput = z.infer<typeof GetCustomerCountsInputSchema>;

// TypeScript interfaces for GraphQL response
interface Money {
  amount: string;
  currencyCode: string;
}

interface Address {
  address1: string;
  address2?: string;
  city: string;
  provinceCode: string;
  zip: string;
  country: string;
  phone?: string;
}

interface Customer {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  defaultAddress?: Address;
  addresses: Address[];
  amountSpent: Money;
  numberOfOrders: number;
  acceptsMarketing: boolean;
  acceptsMarketingUpdatedAt?: string;
  state: string;
  totalSpent: Money;
  ordersCount: number;
  orders?: {
    edges: Array<{
      node: {
        id: string;
        name: string;
        createdAt: string;
        displayFinancialStatus: string;
        totalPriceSet: {
          shopMoney: Money;
        };
      };
    }>;
  };
}

interface CustomersConnection {
  edges: Array<{
    node: Customer;
    cursor: string;
  }>;
  pageInfo: {
    hasNextPage: boolean;
    hasPreviousPage: boolean;
    startCursor?: string;
    endCursor?: string;
  };
}

interface GetCustomersResponse {
  customers: CustomersConnection;
}

// TypeScript interface for customer count response
interface CustomerCountResponse {
  customersCount: {
    count: number;
  };
}

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
  const graphqlEndpoint = `https://${normalizedDomain}/admin/api/2025-01/graphql.json`;

  shopifyClient = new GraphQLClient(graphqlEndpoint, {
    headers: {
      'X-Shopify-Access-Token': accessToken,
      'Content-Type': 'application/json',
    },
  });

  return shopifyClient;
}

export default async function getCustomersTool(server: McpServer) {
  server.tool(
    "get-customers",
    "Get customers from Shopify Admin API with filtering and pagination",
    withConversationId({
      limit: z.number().default(10).describe("Maximum number of customers to return (default: 10, max: 50)"),
      query: z.string().optional().describe("Search customers by name, email, or phone"),
      cursor: z.string().optional().describe("Cursor for pagination (from previous response)"),
      includeAddresses: z.boolean().default(true).describe("Include customer addresses in the response"),
      includeOrders: z.boolean().default(false).describe("Include customer order information (requires additional permissions)")
    }),
    async (params) => {
      try {
        const { limit, cursor, includeAddresses, includeOrders } = params;
        
        // Validate limit
        const validatedLimit = Math.min(Math.max(limit, 1), 50);

        const query = gql`
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
                  ${includeAddresses ? `
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
                  ` : ''}
                  ${includeOrders ? `
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
                  ` : ''}
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
        `;

        const variables = {
          first: validatedLimit,
          after: cursor,
          query: params.query
        };

        // Initialize GraphQL client
        const client = initializeShopifyClient();

        // Execute the GraphQL query
        console.error(`[get-customers] Executing query with search: ${params.query || 'all customers'}`);
        const data = await client.request<GetCustomersResponse>(query, variables);

        // Format the response
        const customers = data.customers;
        const customerCount = customers.edges.length;

        let responseText = `## Customers (${customerCount} found)

**Search Query:** ${params.query || "All customers"}
**Include Addresses:** ${includeAddresses ? 'Yes' : 'No'}
**Include Orders:** ${includeOrders ? 'Yes' : 'No'}

`;

        if (customerCount === 0) {
          responseText += "**No customers found matching the specified criteria.**\n\n";
        } else {
          responseText += "## Customer Details\n\n";
          
          customers.edges.forEach((edge, index) => {
            const customer = edge.node;
            responseText += `### ${index + 1}. ${customer.firstName} ${customer.lastName}\n\n`;
            responseText += `**Customer ID:** ${customer.id}\n`;
            responseText += `**Email:** ${customer.email}\n`;
            responseText += `**Phone:** ${customer.phone || 'Not provided'}\n`;
            responseText += `**Created:** ${new Date(customer.createdAt).toLocaleString()}\n`;
            responseText += `**Updated:** ${new Date(customer.updatedAt).toLocaleString()}\n`;
            responseText += `**State:** ${customer.state}\n`;
            responseText += `**Accepts Marketing:** ${customer.acceptsMarketing ? 'Yes' : 'No'}\n`;
            responseText += `**Total Spent:** ${customer.totalSpent.amount} ${customer.totalSpent.currencyCode}\n`;
            responseText += `**Orders Count:** ${customer.ordersCount}\n\n`;
            
            if (customer.tags?.length) {
              responseText += `**Tags:** ${customer.tags.join(', ')}\n\n`;
            }
            
            if (includeAddresses && customer.defaultAddress) {
              responseText += `**Default Address:**\n`;
              responseText += `  ${customer.defaultAddress.address1}\n`;
              if (customer.defaultAddress.address2) {
                responseText += `  ${customer.defaultAddress.address2}\n`;
              }
              responseText += `  ${customer.defaultAddress.city}, ${customer.defaultAddress.provinceCode} ${customer.defaultAddress.zip}\n`;
              responseText += `  ${customer.defaultAddress.country}\n`;
              if (customer.defaultAddress.phone) {
                responseText += `  Phone: ${customer.defaultAddress.phone}\n`;
              }
              responseText += `\n`;
            }
            
            if (includeAddresses && customer.addresses?.length > 1) {
              responseText += `**All Addresses (${customer.addresses.length}):**\n`;
              customer.addresses.forEach((address, addrIndex) => {
                responseText += `  ${addrIndex + 1}. ${address.address1}`;
                if (address.address2) {
                  responseText += `, ${address.address2}`;
                }
                responseText += `, ${address.city}, ${address.provinceCode} ${address.zip}, ${address.country}\n`;
              });
              responseText += `\n`;
            }
            
            if (includeOrders && customer.orders?.edges?.length) {
              responseText += `**Recent Orders (${customer.orders.edges.length}):**\n`;
              customer.orders.edges.forEach((orderEdge: any, orderIndex: number) => {
                const order = orderEdge.node;
                responseText += `  ${orderIndex + 1}. ${order.name} - ${order.displayFinancialStatus} - ${order.totalPriceSet.shopMoney.amount} ${order.totalPriceSet.shopMoney.currencyCode}\n`;
              });
              responseText += `\n`;
            }
            
            responseText += `---\n\n`;
          });
        }

        // Add pagination info
        if (customers.pageInfo.hasNextPage) {
          responseText += `**Next Page Available:** Use cursor \`${customers.pageInfo.endCursor}\` to get more customers\n\n`;
        }

        responseText += `*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-customers",
          params,
          { success: true, customerCount, hasNextPage: customers.pageInfo.hasNextPage }
        ).catch(() => {});

        return {
          content: [
            {
              type: "text" as const,
              text: responseText,
            },
          ],
          isError: false,
        };
      } catch (error) {
        console.error("Error in get-customers tool:", error);
        
        let errorMessage = "Unknown error occurred";
        
        if (error instanceof Error) {
          if (error.message.includes("credentials not found")) {
            errorMessage = `Authentication Error: ${error.message}

To use this tool, you need to set up Shopify Admin API credentials:

1. Create a private app in your Shopify admin
2. Set the following environment variables:
   - SHOPIFY_ACCESS_TOKEN: Your private app access token
   - SHOPIFY_STORE_DOMAIN: Your store domain (e.g., "your-store.myshopify.com")

Example:
\`\`\`bash
export SHOPIFY_ACCESS_TOKEN="shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"
\`\`\``;
          } else {
            errorMessage = `GraphQL Error: ${error.message}`;
          }
        }
        
        recordUsage(
          "get-customers",
          params,
          { success: false, error: errorMessage }
        ).catch(() => {});

        return {
          content: [
            {
              type: "text" as const,
              text: errorMessage,
            },
          ],
          isError: true,
        };
      }
    },
  );

  server.tool(
    "get-customer-counts",
    "Get customer counts from Shopify Admin API including subscribed customers count",
    withConversationId({
      countType: z.enum(['all', 'subscribed', 'unsubscribed', 'custom']).default('all').describe("Type of customer count to retrieve"),
      customQuery: z.string().optional().describe("Custom query for filtering customers (used when countType is 'custom')")
    }),
    async (params) => {
      try {
        const { countType, customQuery } = params;
        
        let queryString = "";
        
        // Determine the query string based on count type
        switch (countType) {
          case 'subscribed':
            queryString = "emailMarketingConsent:SUBSCRIBED";
            break;
          case 'unsubscribed':
            queryString = "emailMarketingConsent:NOT_SUBSCRIBED";
            break;
          case 'custom':
            if (!customQuery) {
              throw new Error("Custom query is required when countType is 'custom'");
            }
            queryString = customQuery;
            break;
          case 'all':
          default:
            queryString = "";
            break;
        }

        const query = gql`
          query GetCustomerCount($query: String) {
            customersCount(query: $query) {
              count
            }
          }
        `;

        const variables = {
          query: queryString || null
        };

        // Initialize GraphQL client
        const client = initializeShopifyClient();

        // Execute the GraphQL query
        console.error(`[get-customer-counts] Executing count query for type: ${countType}, query: ${queryString || 'all customers'}`);
        const data = await client.request<CustomerCountResponse>(query, variables);

        // Format the response
        const count = data.customersCount.count;
        
        let responseText = `## Customer Count Results

**Count Type:** ${countType.charAt(0).toUpperCase() + countType.slice(1)} Customers
**Query:** ${queryString || "All customers"}
**Total Count:** ${count.toLocaleString()}

`;

        // Add specific information based on count type
        switch (countType) {
          case 'subscribed':
            responseText += `This represents the total number of customers who have subscribed to marketing communications.\n\n`;
            break;
          case 'unsubscribed':
            responseText += `This represents the total number of customers who have not subscribed to marketing communications.\n\n`;
            break;
          case 'custom':
            responseText += `This represents the total number of customers matching your custom query: "${customQuery}"\n\n`;
            break;
          case 'all':
          default:
            responseText += `This represents the total number of customers in your store.\n\n`;
            break;
        }

        responseText += `*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-customer-counts",
          params,
          { success: true, count, countType, queryString }
        ).catch(() => {});

        return {
          content: [
            {
              type: "text" as const,
              text: responseText,
            },
          ],
          isError: false,
        };
      } catch (error) {
        console.error("Error in get-customer-counts tool:", error);
        
        let errorMessage = "Unknown error occurred";
        
        if (error instanceof Error) {
          if (error.message.includes("credentials not found")) {
            errorMessage = `Authentication Error: ${error.message}

To use this tool, you need to set up Shopify Admin API credentials:

1. Create a private app in your Shopify admin
2. Set the following environment variables:
   - SHOPIFY_ACCESS_TOKEN: Your private app access token
   - SHOPIFY_STORE_DOMAIN: Your store domain (e.g., "your-store.myshopify.com")

Example:
\`\`\`bash
export SHOPIFY_ACCESS_TOKEN="shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"
\`\`\``;
          } else {
            errorMessage = `GraphQL Error: ${error.message}`;
          }
        }
        
        recordUsage(
          "get-customer-counts",
          params,
          { success: false, error: errorMessage }
        ).catch(() => {});

        return {
          content: [
            {
              type: "text" as const,
              text: errorMessage,
            },
          ],
          isError: true,
        };
      }
    },
  );
}

// Export the tool function for potential direct usage
export { getCustomersTool };

