import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for getOrders
const GetOrdersInputSchema = z.object({
  limit: z.number().default(10).describe("Maximum number of orders to return (default: 10, max: 50)"),
  status: z.enum(["open", "closed", "cancelled", "any"]).default("any").describe("Filter orders by status"),
  financialStatus: z.enum(["authorized", "paid", "partially_paid", "partially_refunded", "refunded", "voided", "any"]).default("any").describe("Filter orders by financial status"),
  fulfillmentStatus: z.enum(["fulfilled", "partial", "unfulfilled", "any"]).default("any").describe("Filter orders by fulfillment status"),
  createdAtMin: z.string().optional().describe("Filter orders created after this date (ISO 8601 format)"),
  createdAtMax: z.string().optional().describe("Filter orders created before this date (ISO 8601 format)"),
  query: z.string().optional().describe("Search orders by customer name, email, or order number"),
  cursor: z.string().optional().describe("Cursor for pagination (from previous response)")
});

type GetOrdersInput = z.infer<typeof GetOrdersInputSchema>;

// TypeScript interfaces for GraphQL response
interface ShopMoney {
  amount: string;
  currencyCode: string;
}

interface MoneySet {
  shopMoney: ShopMoney;
}

interface Customer {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
}

interface ShippingAddress {
  address1: string;
  address2?: string;
  city: string;
  provinceCode: string;
  zip: string;
  country: string;
  phone?: string;
}

interface ProductVariant {
  id: string;
  title: string;
  sku?: string;
}

interface LineItem {
  id: string;
  title: string;
  quantity: number;
  originalTotalSet: MoneySet;
  variant?: ProductVariant;
}

interface Order {
  id: string;
  name: string;
  createdAt: string;
  displayFinancialStatus: string;
  displayFulfillmentStatus: string;
  totalPriceSet: MoneySet;
  subtotalPriceSet: MoneySet;
  totalShippingPriceSet: MoneySet;
  totalTaxSet: MoneySet;
  customer?: Customer;
  shippingAddress?: ShippingAddress;
  lineItems: {
    edges: Array<{
      node: LineItem;
    }>;
  };
  tags: string[];
  note?: string;
}

interface OrdersConnection {
  edges: Array<{
    node: Order;
    cursor: string;
  }>;
  pageInfo: {
    hasNextPage: boolean;
    hasPreviousPage: boolean;
    startCursor?: string;
    endCursor?: string;
  };
}

interface GetOrdersResponse {
  orders: OrdersConnection;
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

// Helper function to build query filters
function buildQueryFilters(params: GetOrdersInput): string {
  const filters: string[] = [];
  
  if (params.status !== "any") {
    filters.push(`status:${params.status.toUpperCase()}`);
  }
  
  if (params.financialStatus !== "any") {
    filters.push(`financial_status:${params.financialStatus.toUpperCase()}`);
  }
  
  if (params.fulfillmentStatus !== "any") {
    filters.push(`fulfillment_status:${params.fulfillmentStatus.toUpperCase()}`);
  }
  
  if (params.createdAtMin) {
    filters.push(`created_at:>='${params.createdAtMin}'`);
  }
  
  if (params.createdAtMax) {
    filters.push(`created_at:<='${params.createdAtMax}'`);
  }
  
  if (params.query) {
    filters.push(`query:"${params.query}"`);
  }
  
  return filters.join(" AND ");
}

export default async function getOrdersTool(server: McpServer) {
  server.tool(
    "get-orders",
    "Get orders from Shopify Admin API with filtering and pagination",
    withConversationId({
      limit: z.number().default(10).describe("Maximum number of orders to return (default: 10, max: 50)"),
      status: z.enum(["open", "closed", "cancelled", "any"]).default("any").describe("Filter orders by status"),
      financialStatus: z.enum(["authorized", "paid", "partially_paid", "partially_refunded", "refunded", "voided", "any"]).default("any").describe("Filter orders by financial status"),
      fulfillmentStatus: z.enum(["fulfilled", "partial", "unfulfilled", "any"]).default("any").describe("Filter orders by fulfillment status"),
      createdAtMin: z.string().optional().describe("Filter orders created after this date (ISO 8601 format)"),
      createdAtMax: z.string().optional().describe("Filter orders created before this date (ISO 8601 format)"),
      query: z.string().optional().describe("Search orders by customer name, email, or order number"),
      cursor: z.string().optional().describe("Cursor for pagination (from previous response)")
    }),
    async (params) => {
      try {
        const { limit, cursor } = params;
        
        // Validate limit
        const validatedLimit = Math.min(Math.max(limit, 1), 50);

        const query = gql`
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
        `;

        const variables = {
          first: validatedLimit,
          after: cursor,
          query: buildQueryFilters(params)
        };

        // Initialize GraphQL client
        const client = initializeShopifyClient();

        // Execute the GraphQL query
        console.error(`[get-orders] Executing query with filters: ${variables.query}`);
        const data = await client.request<GetOrdersResponse>(query, variables);

        // Format the response
        const orders = data.orders;
        const orderCount = orders.edges.length;

        let responseText = `## Orders (${orderCount} found)

**Filters Applied:**
- Status: ${params.status}
- Financial Status: ${params.financialStatus}
- Fulfillment Status: ${params.fulfillmentStatus}
${params.createdAtMin ? `- Created After: ${params.createdAtMin}` : ''}
${params.createdAtMax ? `- Created Before: ${params.createdAtMax}` : ''}
${params.query ? `- Search Query: ${params.query}` : ''}

`;

        if (orderCount === 0) {
          responseText += "**No orders found matching the specified criteria.**\n\n";
        } else {
          responseText += "## Order Details\n\n";
          
          orders.edges.forEach((edge, index) => {
            const order = edge.node;
            responseText += `### ${index + 1}. Order ${order.name}\n\n`;
            responseText += `**Order ID:** ${order.id}\n`;
            responseText += `**Created:** ${new Date(order.createdAt).toLocaleString()}\n`;
            responseText += `**Financial Status:** ${order.displayFinancialStatus}\n`;
            responseText += `**Fulfillment Status:** ${order.displayFulfillmentStatus}\n\n`;
            
            responseText += `**Total Price:** ${order.totalPriceSet?.shopMoney?.amount} ${order.totalPriceSet?.shopMoney?.currencyCode}\n`;
            responseText += `**Subtotal:** ${order.subtotalPriceSet?.shopMoney?.amount} ${order.subtotalPriceSet?.shopMoney?.currencyCode}\n`;
            responseText += `**Shipping:** ${order.totalShippingPriceSet?.shopMoney?.amount} ${order.totalShippingPriceSet?.shopMoney?.currencyCode}\n`;
            responseText += `**Tax:** ${order.totalTaxSet?.shopMoney?.amount} ${order.totalTaxSet?.shopMoney?.currencyCode}\n\n`;
            
            if (order.customer) {
              responseText += `**Customer:** ${order.customer.firstName} ${order.customer.lastName} (${order.customer.email})\n\n`;
            }
            
            if (order.lineItems?.edges?.length) {
              responseText += `**Line Items:**\n`;
              order.lineItems.edges.forEach((itemEdge, itemIndex) => {
                const item = itemEdge.node;
                responseText += `  ${itemIndex + 1}. ${item.title} (Qty: ${item.quantity}) - ${item.originalTotalSet?.shopMoney?.amount} ${item.originalTotalSet?.shopMoney?.currencyCode}\n`;
              });
              responseText += `\n`;
            }
            
            responseText += `**Tags:** ${order.tags?.length ? order.tags.join(', ') : 'None'}\n`;
            if (order.note) {
              responseText += `**Note:** ${order.note}\n`;
            }
            responseText += `\n---\n\n`;
          });
        }

        // Add pagination info
        if (orders.pageInfo.hasNextPage) {
          responseText += `**Next Page Available:** Use cursor \`${orders.pageInfo.endCursor}\` to get more orders\n\n`;
        }

        responseText += `*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-orders",
          params,
          { success: true, orderCount, hasNextPage: orders.pageInfo.hasNextPage }
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
        console.error("Error in get-orders tool:", error);
        
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
          "get-orders",
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
export { getOrdersTool };

