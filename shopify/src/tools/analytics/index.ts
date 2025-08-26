import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// This tool implements the GetStoreAnalytics GraphQL query for fetching store analytics
// including shop details, orders, products, and customers from Shopify Admin API

// Input schema for getStoreAnalytics
const GetStoreAnalyticsInputSchema = z.object({
  includeOrders: z.boolean().default(true).describe("Include order statistics"),
  includeProducts: z.boolean().default(true).describe("Include product statistics"),
  includeCustomers: z.boolean().default(true).describe("Include customer statistics"),
  includeInventory: z.boolean().default(false).describe("Include inventory statistics"),
  dateRange: z.enum(["today", "yesterday", "last_7_days", "last_30_days", "last_90_days", "all_time"]).default("all_time").describe("Date range for analytics"),
  limit: z.number().default(10).describe("Number of records to fetch for each category (orders, products, customers)")
});

type GetStoreAnalyticsInput = z.infer<typeof GetStoreAnalyticsInputSchema>;

// TypeScript interfaces for GraphQL response
interface Money {
  amount: string;
  currencyCode: string;
}

interface Store {
  id: string;
  name: string;
  email: string;
  currencyCode: string;
  primaryDomain: {
    url: string;
    host: string;
  };
  plan: {
    displayName: string;
    partnerDevelopment: boolean;
    shopifyPlus: boolean;
  };
  createdAt: string;
  updatedAt: string;
}

interface OrdersConnection {
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
  pageInfo: {
    hasNextPage: boolean;
  };
}

interface ProductsConnection {
  edges: Array<{
    node: {
      id: string;
      title: string;
      status: string;
      totalInventory: number;
      createdAt: string;
    };
  }>;
  pageInfo: {
    hasNextPage: boolean;
  };
}

interface CustomersConnection {
  edges: Array<{
    node: {
      id: string;
      firstName: string;
      lastName: string;
      email: string;
      createdAt: string;
      amountSpent: Money;
      numberOfOrders: number;
    };
  }>;
  pageInfo: {
    hasNextPage: boolean;
  };
}

interface GetStoreAnalyticsResponse {
  shop: Store;
  orders: OrdersConnection;
  products: ProductsConnection;
  customers: CustomersConnection;
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

// Helper function to build date filters
function buildDateFilter(dateRange: string): string {
  const now = new Date();
  let startDate: Date;
  
  switch (dateRange) {
    case "today":
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      break;
    case "yesterday":
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
      break;
    case "last_7_days":
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      break;
    case "last_30_days":
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      break;
    case "last_90_days":
      startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      break;
    default:
      return ""; // all_time
  }
  
  return `created_at:>='${startDate.toISOString()}'`;
}

export default async function getStoreAnalyticsTool(server: McpServer) {
  server.tool(
    "get-store-analytics",
    "Get store analytics and statistics from Shopify Admin API",
    withConversationId({
      includeOrders: z.boolean().default(true).describe("Include order statistics"),
      includeProducts: z.boolean().default(true).describe("Include product statistics"),
      includeCustomers: z.boolean().default(true).describe("Include customer statistics"),
      includeInventory: z.boolean().default(false).describe("Include inventory statistics"),
      dateRange: z.enum(["today", "yesterday", "last_7_days", "last_30_days", "last_90_days", "all_time"]).default("all_time").describe("Date range for analytics"),
      limit: z.number().default(10).describe("Number of records to fetch for each category (orders, products, customers)")
    }),
          async (params) => {
        try {
          const { includeOrders, includeProducts, includeCustomers, includeInventory, dateRange, limit } = params;

        const query = gql`
          query GetStoreAnalytics($orderQuery: String, $productQuery: String, $customerQuery: String, $limit: Int!) {
            shop {
              id
              name
              email
              currencyCode
              primaryDomain {
                url
                host
              }
              plan {
                displayName
                partnerDevelopment
                shopifyPlus
              }
              createdAt
              updatedAt
            }
            ${includeOrders ? `
            orders(first: $limit, query: $orderQuery) {
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
              pageInfo {
                hasNextPage
              }
            }
            ` : ''}
            ${includeProducts ? `
            products(first: $limit, query: $productQuery) {
              edges {
                node {
                  id
                  title
                  status
                  totalInventory
                  createdAt
                }
              }
              pageInfo {
                hasNextPage
              }
            }
            ` : ''}
            ${includeCustomers ? `
            customers(first: $limit, query: $customerQuery) {
              edges {
                node {
                  id
                  firstName
                  lastName
                  email
                  createdAt
                  amountSpent {
                    amount
                    currencyCode
                  }
                  numberOfOrders
                }
              }
              pageInfo {
                hasNextPage
              }
            }
            ` : ''}
          }
        `;

        const dateFilter = buildDateFilter(dateRange);
        
        const variables = {
          orderQuery: dateFilter,
          productQuery: dateFilter,
          customerQuery: dateFilter,
          limit: limit
        };

        // Initialize GraphQL client
        const client = initializeShopifyClient();

        // Execute the GraphQL query
        console.error(`[get-store-analytics] Executing query for date range: ${dateRange}`);
        const data = await client.request<GetStoreAnalyticsResponse>(query, variables);

        // Calculate analytics
        const shop = data.shop;
        let responseText = `# Store Analytics - ${shop.name}

**Date Range:** ${dateRange.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
**Generated:** ${new Date().toLocaleString()}

## Store Information

**Store Name:** ${shop.name}
**Store Email:** ${shop.email}
**Currency:** ${shop.currencyCode}
**Domain:** ${shop.primaryDomain.url}
**Plan:** ${shop.plan.displayName}
**Shopify Plus:** ${shop.plan.shopifyPlus ? 'Yes' : 'No'}
**Created:** ${new Date(shop.createdAt).toLocaleDateString()}
**Last Updated:** ${new Date(shop.updatedAt).toLocaleDateString()}

`;

        // Orders Analytics
        if (includeOrders && data.orders) {
          const orders = data.orders.edges;
          const totalOrders = orders.length;
          let totalRevenue = 0;
          let paidOrders = 0;
          let pendingOrders = 0;
          let refundedOrders = 0;
          
          orders.forEach(edge => {
            const order = edge.node;
            const amount = parseFloat(order.totalPriceSet.shopMoney.amount);
            totalRevenue += amount;
            
            switch (order.displayFinancialStatus.toLowerCase()) {
              case 'paid':
                paidOrders++;
                break;
              case 'pending':
                pendingOrders++;
                break;
              case 'refunded':
                refundedOrders++;
                break;
            }
          });
          
          responseText += `## Orders Analytics (${totalOrders} orders)

**Total Orders:** ${totalOrders}
**Total Revenue:** ${totalRevenue.toFixed(2)} ${shop.currencyCode}
**Average Order Value:** ${totalOrders > 0 ? (totalRevenue / totalOrders).toFixed(2) : '0.00'} ${shop.currencyCode}

**Order Status Breakdown:**
- Paid: ${paidOrders} (${totalOrders > 0 ? ((paidOrders / totalOrders) * 100).toFixed(1) : '0'}%)
- Pending: ${pendingOrders} (${totalOrders > 0 ? ((pendingOrders / totalOrders) * 100).toFixed(1) : '0'}%)
- Refunded: ${refundedOrders} (${totalOrders > 0 ? ((refundedOrders / totalOrders) * 100).toFixed(1) : '0'}%)

`;
        }

        // Products Analytics
        if (includeProducts && data.products) {
          const products = data.products.edges;
          const totalProducts = products.length;
          let activeProducts = 0;
          let draftProducts = 0;
          let archivedProducts = 0;
          let totalInventory = 0;
          
          products.forEach(edge => {
            const product = edge.node;
            totalInventory += product.totalInventory;
            
            switch (product.status.toLowerCase()) {
              case 'active':
                activeProducts++;
                break;
              case 'draft':
                draftProducts++;
                break;
              case 'archived':
                archivedProducts++;
                break;
            }
          });
          
          responseText += `## Products Analytics (${totalProducts} products)

**Total Products:** ${totalProducts}
**Total Inventory:** ${totalInventory} units
**Average Inventory per Product:** ${totalProducts > 0 ? (totalInventory / totalProducts).toFixed(1) : '0'} units

**Product Status Breakdown:**
- Active: ${activeProducts} (${totalProducts > 0 ? ((activeProducts / totalProducts) * 100).toFixed(1) : '0'}%)
- Draft: ${draftProducts} (${totalProducts > 0 ? ((draftProducts / totalProducts) * 100).toFixed(1) : '0'}%)
- Archived: ${archivedProducts} (${totalProducts > 0 ? ((archivedProducts / totalProducts) * 100).toFixed(1) : '0'}%)

`;
        }

        // Customers Analytics
        if (includeCustomers && data.customers) {
          const customers = data.customers.edges;
          const totalCustomers = customers.length;
          let totalCustomerSpent = 0;
          let totalCustomerOrders = 0;
          
          customers.forEach(edge => {
            const customer = edge.node;
            totalCustomerSpent += parseFloat(customer.amountSpent.amount);
            totalCustomerOrders += customer.numberOfOrders;
          });
          
          responseText += `## Customers Analytics (${totalCustomers} customers)

**Total Customers:** ${totalCustomers}
**Total Customer Spend:** ${totalCustomerSpent.toFixed(2)} ${shop.currencyCode}
**Total Customer Orders:** ${totalCustomerOrders}
**Average Customer Spend:** ${totalCustomers > 0 ? (totalCustomerSpent / totalCustomers).toFixed(2) : '0.00'} ${shop.currencyCode}
**Average Orders per Customer:** ${totalCustomers > 0 ? (totalCustomerOrders / totalCustomers).toFixed(1) : '0'}

`;
        }

        // Inventory Analytics (if requested)
        if (includeInventory) {
          responseText += `## Inventory Analytics

*Note: Detailed inventory analytics would require additional API calls to inventory endpoints.*

**Recommendation:** Use the \`get-inventory\` tool for detailed inventory analysis including:
- Low stock items
- Out of stock items
- Inventory by location
- Stock levels by product/variant

`;
        }

        responseText += `---
*Analytics generated from Shopify Admin API data*`;

        recordUsage(
          "get-store-analytics",
          params,
          { success: true, dateRange, shopName: shop.name }
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
        console.error("Error in get-store-analytics tool:", error);
        
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
          "get-store-analytics",
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
export { getStoreAnalyticsTool };

