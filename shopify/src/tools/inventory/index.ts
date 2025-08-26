import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for getInventory
const GetInventoryInputSchema = z.object({
  limit: z.number().default(10).describe("Maximum number of inventory items to return (default: 10, max: 50)"),
  locationId: z.string().optional().describe("Filter by specific location ID"),
  productId: z.string().optional().describe("Filter by specific product ID"),
  variantId: z.string().optional().describe("Filter by specific variant ID"),
  lowStock: z.boolean().default(false).describe("Show only items with low stock (quantity <= 10)"),
  outOfStock: z.boolean().default(false).describe("Show only out of stock items"),
  cursor: z.string().optional().describe("Cursor for pagination (from previous response)")
});

type GetInventoryInput = z.infer<typeof GetInventoryInputSchema>;   

// TypeScript interfaces for GraphQL response
interface Money {
  amount: string;
  currencyCode: string;
}

interface Location {
  id: string;
  name: string;
  address: {
    address1: string;
    address2?: string;
    city: string;
    provinceCode: string;
    zip: string;
    country: string;
  };
}

interface ProductVariant {
  id: string;
  title: string;
  sku?: string;
  barcode?: string;
  price: string;
  product: {
    id: string;
    title: string;
    handle: string;
  };
}

interface InventoryItem {
  id: string;
  sku?: string;
  tracked: boolean;
  createdAt: string;
  updatedAt: string;
  variant: ProductVariant;
  inventoryLevels: {
    edges: Array<{
      node: {
        id: string;
        available: number;
        location: Location;
      };
    }>;
  };
}

interface InventoryItemsConnection {
  edges: Array<{
    node: InventoryItem;
    cursor: string;
  }>;
  pageInfo: {
    hasNextPage: boolean;
    hasPreviousPage: boolean;
    startCursor?: string;
    endCursor?: string;
  };
}

interface GetInventoryResponse {
  inventoryItems: InventoryItemsConnection;
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
function buildQueryFilters(params: GetInventoryInput): string {
  const filters: string[] = [];
  
  if (params.locationId) {
    filters.push(`location_id:${params.locationId}`);
  }
  
  if (params.productId) {
    filters.push(`product_id:${params.productId}`);
  }
  
  if (params.variantId) {
    filters.push(`variant_id:${params.variantId}`);
  }
  
  if (params.lowStock) {
    filters.push(`available:<=10`);
  }
  
  if (params.outOfStock) {
    filters.push(`available:0`);
  }
  
  return filters.join(" AND ");
}

export default async function getInventoryTool(server: McpServer) {
  server.tool(
    "get-inventory",
    "Get inventory information from Shopify Admin API with filtering and pagination",
    withConversationId({
      limit: z.number().default(10).describe("Maximum number of inventory items to return (default: 10, max: 50)"),
      locationId: z.string().optional().describe("Filter by specific location ID"),
      productId: z.string().optional().describe("Filter by specific product ID"),
      variantId: z.string().optional().describe("Filter by specific variant ID"),
      lowStock: z.boolean().default(false).describe("Show only items with low stock (quantity <= 10)"),
      outOfStock: z.boolean().default(false).describe("Show only out of stock items"),
      cursor: z.string().optional().describe("Cursor for pagination (from previous response)")
    }),
    async (params) => {
      try {
        const { limit, cursor } = params;
        
        // Validate limit
        const validatedLimit = Math.min(Math.max(limit, 1), 50);

        const query = gql`
          query GetInventory($first: Int!, $after: String, $query: String) {
            inventoryItems(first: $first, after: $after, query: $query) {
              edges {
                node {
                  id
                  sku
                  tracked
                  createdAt
                  updatedAt
                                     variant {
                     id
                     title
                     sku
                     barcode
                     price
                     product {
                       id
                       title
                       handle
                     }
                   }
                  inventoryLevels(first: 10) {
                    edges {
                      node {
                        id
                        available
                        location {
                          id
                          name
                          address {
                            address1
                            address2
                            city
                            provinceCode
                            zip
                            country
                          }
                        }
                      }
                    }
                  }
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
        console.error(`[get-inventory] Executing query with filters: ${variables.query}`);
        const data = await client.request<GetInventoryResponse>(query, variables);

        // Format the response
        const inventoryItems = data.inventoryItems;
        const itemCount = inventoryItems.edges.length;

        let responseText = `## Inventory Items (${itemCount} found)

**Filters Applied:**
${params.locationId ? `- Location ID: ${params.locationId}` : ''}
${params.productId ? `- Product ID: ${params.productId}` : ''}
${params.variantId ? `- Variant ID: ${params.variantId}` : ''}
${params.lowStock ? `- Low Stock Only (≤10)` : ''}
${params.outOfStock ? `- Out of Stock Only` : ''}

`;

        if (itemCount === 0) {
          responseText += "**No inventory items found matching the specified criteria.**\n\n";
        } else {
          responseText += "## Inventory Details\n\n";
          
          inventoryItems.edges.forEach((edge, index) => {
            const item = edge.node;
            const variant = item.variant;
            const product = variant.product;
            
            responseText += `### ${index + 1}. ${product.title} - ${variant.title}\n\n`;
            responseText += `**Inventory Item ID:** ${item.id}\n`;
            responseText += `**Product ID:** ${product.id}\n`;
            responseText += `**Variant ID:** ${variant.id}\n`;
            responseText += `**SKU:** ${item.sku || variant.sku || 'N/A'}\n`;
            responseText += `**Barcode:** ${variant.barcode || 'N/A'}\n`;
                         responseText += `**Price:** ${variant.price}\n`;
            responseText += `**Tracked:** ${item.tracked ? 'Yes' : 'No'}\n`;
            responseText += `**Created:** ${new Date(item.createdAt).toLocaleString()}\n`;
            responseText += `**Updated:** ${new Date(item.updatedAt).toLocaleString()}\n\n`;
            
            if (item.inventoryLevels?.edges?.length) {
              responseText += `**Inventory Levels (${item.inventoryLevels.edges.length} locations):**\n`;
              let totalAvailable = 0;
              
              item.inventoryLevels.edges.forEach((levelEdge, levelIndex) => {
                const level = levelEdge.node;
                const location = level.location;
                totalAvailable += level.available;
                
                responseText += `  ${levelIndex + 1}. ${location.name}\n`;
                responseText += `     - Available: ${level.available}\n`;
                responseText += `     - Location ID: ${location.id}\n`;
                responseText += `     - Address: ${location.address.address1}`;
                if (location.address.address2) {
                  responseText += `, ${location.address.address2}`;
                }
                responseText += `, ${location.address.city}, ${location.address.provinceCode} ${location.address.zip}, ${location.address.country}\n`;
              });
              
              responseText += `\n**Total Available:** ${totalAvailable}\n`;
              
              // Add stock status indicators
              if (totalAvailable === 0) {
                responseText += `**Status:** 🔴 Out of Stock\n`;
              } else if (totalAvailable <= 10) {
                responseText += `**Status:** 🟡 Low Stock\n`;
              } else {
                responseText += `**Status:** 🟢 In Stock\n`;
              }
            } else {
              responseText += `**Inventory Levels:** No inventory levels found\n`;
            }
            
            responseText += `\n---\n\n`;
          });
        }

        // Add pagination info
        if (inventoryItems.pageInfo.hasNextPage) {
          responseText += `**Next Page Available:** Use cursor \`${inventoryItems.pageInfo.endCursor}\` to get more inventory items\n\n`;
        }

        responseText += `*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-inventory",
          params,
          { success: true, itemCount, hasNextPage: inventoryItems.pageInfo.hasNextPage }
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
        console.error("Error in get-inventory tool:", error);
        
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
          "get-inventory",
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
export { getInventoryTool };

