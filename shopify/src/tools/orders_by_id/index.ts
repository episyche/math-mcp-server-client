import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for getOrderById
const GetOrderByIdInputSchema = z.object({
  orderId: z.string().min(1).describe("The ID of the order to retrieve")
});

type GetOrderByIdInput = z.infer<typeof GetOrderByIdInputSchema>;

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

interface Metafield {
  id: string;
  namespace: string;
  key: string;
  value: string;
  type: string;
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
  metafields: {
    edges: Array<{
      node: Metafield;
    }>;
  };
}

interface GetOrderByIdResponse {
  order: Order | null;
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

export default async function getOrderByIdTool(server: McpServer) {
  server.tool(
    "get-order-by-id",
    "Get a specific order by ID from Shopify Admin API",
    withConversationId({
      orderId: z.string().min(1).describe("The ID of the order to retrieve")
    }),
    async (params) => {
      try {
        const { orderId } = params;

        const query = gql`
          query GetOrderById($id: ID!) {
            order(id: $id) {
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
              lineItems(first: 20) {
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
              metafields(first: 20) {
                edges {
                  node {
                    id
                    namespace
                    key
                    value
                    type
                  }
                }
              }
            }
          }
        `;

        const variables = {
          id: orderId
        };

        // Initialize GraphQL client
        const client = initializeShopifyClient();

        // Execute the GraphQL query
        console.error(`[get-order-by-id] Executing query for order ID: ${orderId}`);
        const data = await client.request<GetOrderByIdResponse>(query, variables);

        // Format the response
        const order = data.order;
        if (!order) {
          throw new Error(`Order with ID ${orderId} not found`);
        }

        const responseText = `## Order Details

**Order ID:** ${order.id}
**Order Name:** ${order.name}
**Created:** ${new Date(order.createdAt).toLocaleString()}
**Financial Status:** ${order.displayFinancialStatus}
**Fulfillment Status:** ${order.displayFulfillmentStatus}

## Pricing Information

**Total Price:** ${order.totalPriceSet?.shopMoney?.amount} ${order.totalPriceSet?.shopMoney?.currencyCode}
**Subtotal:** ${order.subtotalPriceSet?.shopMoney?.amount} ${order.subtotalPriceSet?.shopMoney?.currencyCode}
**Shipping:** ${order.totalShippingPriceSet?.shopMoney?.amount} ${order.totalShippingPriceSet?.shopMoney?.currencyCode}
**Tax:** ${order.totalTaxSet?.shopMoney?.amount} ${order.totalTaxSet?.shopMoney?.currencyCode}

## Customer Information

${order.customer ? `
**Customer ID:** ${order.customer.id}
**Name:** ${order.customer.firstName} ${order.customer.lastName}
**Email:** ${order.customer.email}
**Phone:** ${order.customer.phone || 'Not provided'}
` : '**Customer:** Not available'}

## Shipping Address

${order.shippingAddress ? `
**Address:** ${order.shippingAddress.address1}
${order.shippingAddress.address2 ? `**Address 2:** ${order.shippingAddress.address2}` : ''}
**City:** ${order.shippingAddress.city}
**Province:** ${order.shippingAddress.provinceCode}
**ZIP:** ${order.shippingAddress.zip}
**Country:** ${order.shippingAddress.country}
**Phone:** ${order.shippingAddress.phone || 'Not provided'}
` : '**Shipping Address:** Not available'}

## Line Items

${order.lineItems?.edges?.length ? order.lineItems.edges.map((edge, index) => {
  const item = edge.node;
  return `${index + 1}. **${item.title}**
   - Quantity: ${item.quantity}
   - Price: ${item.originalTotalSet?.shopMoney?.amount} ${item.originalTotalSet?.shopMoney?.currencyCode}
   - Variant: ${item.variant?.title || 'N/A'}
   - SKU: ${item.variant?.sku || 'N/A'}`;
}).join('\n\n') : '**No line items found**'}

## Additional Information

**Tags:** ${order.tags?.length ? order.tags.join(', ') : 'None'}
**Note:** ${order.note || 'No notes'}

## Metafields

${order.metafields?.edges?.length ? order.metafields.edges.map((edge, index) => {
  const metafield = edge.node;
  return `${index + 1}. **${metafield.namespace}.${metafield.key}**
   - Type: ${metafield.type}
   - Value: ${metafield.value}`;
}).join('\n\n') : '**No metafields found**'}

---

*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-order-by-id",
          params,
          { success: true, orderId, orderName: order.name }
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
        console.error("Error in get-order-by-id tool:", error);
        
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
          } else if (error.message.includes("not found")) {
            errorMessage = `Order not found: ${error.message}

The order with ID "${params.orderId}" could not be found. Please verify:
1. The order ID is correct
2. The order exists in your store
3. Your app has the necessary permissions to access orders`;
          } else {
            errorMessage = `GraphQL Error: ${error.message}`;
          }
        }
        
        recordUsage(
          "get-order-by-id",
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
export { getOrderByIdTool };

