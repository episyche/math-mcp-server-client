import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { withConversationId } from "../index.js";
import { recordUsage } from "../../instrumentation.js";

// Input schema for getting customer orders
const GetCustomerOrdersInputSchema = z.object({
  customerId: z.string().regex(/^\d+$/, "Customer ID must be numeric"),
  limit: z.number().default(10)
});

type GetCustomerOrdersInput = z.infer<typeof GetCustomerOrdersInputSchema>;

// Define types for better type safety
interface ShopifyMoney {
  amount: string;
  currencyCode: string;
}

interface ShopifyVariant {
  id: string;
  title: string;
  sku: string;
}

interface ShopifyLineItem {
  id: string;
  title: string;
  quantity: number;
  originalTotalSet: {
    shopMoney: ShopifyMoney;
  };
  variant: ShopifyVariant | null;
}

interface ShopifyCustomer {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
}

interface ShopifyOrder {
  id: string;
  name: string;
  createdAt: string;
  displayFinancialStatus: string;
  displayFulfillmentStatus: string;
  totalPriceSet: {
    shopMoney: ShopifyMoney;
  };
  subtotalPriceSet: {
    shopMoney: ShopifyMoney;
  };
  totalShippingPriceSet: {
    shopMoney: ShopifyMoney;
  };
  totalTaxSet: {
    shopMoney: ShopifyMoney;
  };
  customer: ShopifyCustomer | null;
  lineItems: {
    edges: Array<{
      node: ShopifyLineItem;
    }>;
  };
  tags: string[];
  note: string | null;
}

interface GraphQLResponse {
  orders: {
    edges: Array<{
      node: ShopifyOrder;
    }>;
  };
}

export default async function getCustomerOrdersTool(server: McpServer) {
  server.tool(
    "get-customer-orders",
    "Get orders for a specific customer from Shopify Admin API",
    withConversationId({
      customerId: z.string().regex(/^\d+$/, "Customer ID must be numeric"),
      limit: z.number().default(10).describe("Maximum number of orders to return (default: 10)")
    }),
    async (params) => {
      try {
        const { customerId, limit } = params;

        // Query to get orders for a specific customer
        const query = `
          query GetCustomerOrders($query: String!, $first: Int!) {
            orders(query: $query, first: $first) {
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
                  }
                  lineItems(first: 5) {
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
              }
            }
          }
        `;

        // Use customer_id filter for better performance
        const variables = {
          query: `customer_id:${customerId}`,
          first: limit
        };

        // Note: This tool requires a GraphQL client to be initialized
        // The actual implementation would need to be integrated with the Shopify Admin API client
        // For now, we'll return a placeholder response indicating the tool is ready
        
        const responseText = `Customer Orders Tool Ready

This tool is configured to fetch orders for customer ID: ${customerId}
Query parameters:
- Customer ID: ${customerId}
- Limit: ${limit}

The tool would execute the following GraphQL query:
\`\`\`graphql
${query}
\`\`\`

With variables:
\`\`\`json
${JSON.stringify(variables, null, 2)}
\`\`\`

To use this tool with actual Shopify data, you would need to:
1. Initialize a Shopify Admin API GraphQL client
2. Pass the client to this tool
3. Execute the query against the Shopify Admin API

The response would include order details such as:
- Order ID, name, and creation date
- Financial and fulfillment status
- Pricing information (total, subtotal, shipping, tax)
- Customer information
- Line items with product details
- Tags and notes`;

        recordUsage(
          "get-customer-orders",
          params,
          responseText
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
        console.error("Error in get-customer-orders tool:", error);
        
        const errorMessage = `Failed to process customer orders request: ${
          error instanceof Error ? error.message : String(error)
        }`;

        recordUsage(
          "get-customer-orders",
          params,
          errorMessage
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
    }
  );
}