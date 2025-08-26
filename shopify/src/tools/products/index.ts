import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { GraphQLClient, gql } from "graphql-request";
import { z } from "zod";
import { recordUsage } from "../../instrumentation.js";
import { withConversationId } from "../index.js";

// Input schema for getProducts
const GetProductsInputSchema = z.object({
  limit: z.number().default(10).describe("Maximum number of products to return (default: 10, max: 50)"),
  status: z.enum(["active", "archived", "draft", "any"]).default("any").describe("Filter products by status"),
  vendor: z.string().optional().describe("Filter products by vendor"),
  productType: z.string().optional().describe("Filter products by product type"),
  tag: z.string().optional().describe("Filter products by tag"),
  query: z.string().optional().describe("Search products by title, vendor, or product type"),
  cursor: z.string().optional().describe("Cursor for pagination (from previous response)"),
  includeVariants: z.boolean().default(true).describe("Include product variants in the response"),
  includeImages: z.boolean().default(true).describe("Include product images in the response"),
  includeInventory: z.boolean().default(false).describe("Include inventory information (requires additional permissions)")
});

type GetProductsInput = z.infer<typeof GetProductsInputSchema>;

// TypeScript interfaces for GraphQL response
interface Money {
  amount: string;
  currencyCode: string;
}

interface Image {
  id: string;
  url: string;
  altText?: string;
  width: number;
  height: number;
}

interface ProductVariant {
  id: string;
  title: string;
  sku?: string;
  barcode?: string;
  price: string;
  compareAtPrice?: string;
  inventoryQuantity?: number;
  inventoryPolicy?: string;
  taxable: boolean;
}

interface Product {
  id: string;
  title: string;
  handle: string;
  description: string;
  descriptionHtml: string;
  vendor: string;
  productType: string;
  status: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  publishedAt?: string;
  totalInventory: number;
  priceRangeV2: {
    minVariantPrice: Money;
    maxVariantPrice: Money;
  };
  images: {
    edges: Array<{
      node: Image;
    }>;
  };
  variants: {
    edges: Array<{
      node: ProductVariant;
    }>;
  };
  options: Array<{
    id: string;
    name: string;
    values: string[];
  }>;
}

interface ProductsConnection {
  edges: Array<{
    node: Product;
    cursor: string;
  }>;
  pageInfo: {
    hasNextPage: boolean;
    hasPreviousPage: boolean;
    startCursor?: string;
    endCursor?: string;
  };
}

interface GetProductsResponse {
  products: ProductsConnection;
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
function buildQueryFilters(params: GetProductsInput): string {
  const filters: string[] = [];
  
  if (params.status !== "any") {
    filters.push(`status:${params.status.toUpperCase()}`);
  }
  
  if (params.vendor) {
    filters.push(`vendor:"${params.vendor}"`);
  }
  
  if (params.productType) {
    filters.push(`product_type:"${params.productType}"`);
  }
  
  if (params.tag) {
    filters.push(`tag:"${params.tag}"`);
  }
  
  if (params.query) {
    filters.push(`query:"${params.query}"`);
  }
  
  return filters.join(" AND ");
}

export default async function getProductsTool(server: McpServer) {
  server.tool(
    "get-products",
    "Get products from Shopify Admin API with filtering and pagination",
    withConversationId({
      limit: z.number().default(10).describe("Maximum number of products to return (default: 10, max: 50)"),
      status: z.enum(["active", "archived", "draft", "any"]).default("any").describe("Filter products by status"),
      vendor: z.string().optional().describe("Filter products by vendor"),
      productType: z.string().optional().describe("Filter products by product type"),
      tag: z.string().optional().describe("Filter products by tag"),
      query: z.string().optional().describe("Search products by title, vendor, or product type"),
      cursor: z.string().optional().describe("Cursor for pagination (from previous response)"),
      includeVariants: z.boolean().default(true).describe("Include product variants in the response"),
      includeImages: z.boolean().default(true).describe("Include product images in the response"),
      includeInventory: z.boolean().default(false).describe("Include inventory information (requires additional permissions)")
    }),
    async (params) => {
      try {
        const { limit, cursor, includeVariants, includeImages, includeInventory } = params;
        
        // Validate limit
        const validatedLimit = Math.min(Math.max(limit, 1), 50);

        const query = gql`
          query GetProducts($first: Int!, $after: String, $query: String) {
            products(first: $first, after: $after, query: $query) {
              edges {
                node {
                  id
                  title
                  handle
                  description
                  descriptionHtml
                  vendor
                  productType
                  status
                  tags
                  createdAt
                  updatedAt
                  publishedAt
                  totalInventory
                  priceRangeV2 {
                    minVariantPrice {
                      amount
                      currencyCode
                    }
                    maxVariantPrice {
                      amount
                      currencyCode
                    }
                  }
                  ${includeImages ? `
                  images(first: 5) {
                    edges {
                      node {
                        id
                        url
                        altText
                        width
                        height
                      }
                    }
                  }
                  ` : ''}
                                     ${includeVariants ? `
                   variants(first: 50) {
                     edges {
                       node {
                         id
                         title
                         sku
                         barcode
                         price
                         compareAtPrice
                         ${includeInventory ? `
                         inventoryQuantity
                         inventoryPolicy
                         ` : ''}
                         taxable
                       }
                     }
                   }
                   ` : ''}
                  options {
                    id
                    name
                    values
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
        console.error(`[get-products] Executing query with filters: ${variables.query}`);
        const data = await client.request<GetProductsResponse>(query, variables);

        // Format the response
        const products = data.products;
        const productCount = products.edges.length;

        let responseText = `## Products (${productCount} found)

**Filters Applied:**
- Status: ${params.status}
${params.vendor ? `- Vendor: ${params.vendor}` : ''}
${params.productType ? `- Product Type: ${params.productType}` : ''}
${params.tag ? `- Tag: ${params.tag}` : ''}
${params.query ? `- Search Query: ${params.query}` : ''}

`;

        if (productCount === 0) {
          responseText += "**No products found matching the specified criteria.**\n\n";
        } else {
          responseText += "## Product Details\n\n";
          
          products.edges.forEach((edge, index) => {
            const product = edge.node;
            responseText += `### ${index + 1}. ${product.title}\n\n`;
            responseText += `**Product ID:** ${product.id}\n`;
            responseText += `**Handle:** ${product.handle}\n`;
            responseText += `**Status:** ${product.status}\n`;
            responseText += `**Vendor:** ${product.vendor}\n`;
            responseText += `**Product Type:** ${product.productType}\n`;
            responseText += `**Created:** ${new Date(product.createdAt).toLocaleString()}\n`;
            responseText += `**Updated:** ${new Date(product.updatedAt).toLocaleString()}\n`;
            if (product.publishedAt) {
              responseText += `**Published:** ${new Date(product.publishedAt).toLocaleString()}\n`;
            }
            responseText += `**Total Inventory:** ${product.totalInventory}\n\n`;
            
            responseText += `**Price Range:** ${product.priceRangeV2.minVariantPrice.amount} - ${product.priceRangeV2.maxVariantPrice.amount} ${product.priceRangeV2.minVariantPrice.currencyCode}\n\n`;
            
            if (product.description) {
              responseText += `**Description:** ${product.description.substring(0, 200)}${product.description.length > 200 ? '...' : ''}\n\n`;
            }
            
            if (product.tags?.length) {
              responseText += `**Tags:** ${product.tags.join(', ')}\n\n`;
            }
            
            if (includeImages && product.images?.edges?.length) {
              responseText += `**Images (${product.images.edges.length}):**\n`;
              product.images.edges.forEach((imageEdge, imgIndex) => {
                const image = imageEdge.node;
                responseText += `  ${imgIndex + 1}. ${image.url} (${image.width}x${image.height})${image.altText ? ` - ${image.altText}` : ''}\n`;
              });
              responseText += `\n`;
            }
            
                         if (includeVariants && product.variants?.edges?.length) {
               responseText += `**Variants (${product.variants.edges.length}):**\n`;
               product.variants.edges.forEach((variantEdge, varIndex) => {
                 const variant = variantEdge.node;
                 responseText += `  ${varIndex + 1}. ${variant.title}\n`;
                 responseText += `     - SKU: ${variant.sku || 'N/A'}\n`;
                 responseText += `     - Price: ${variant.price}\n`;
                 if (variant.compareAtPrice) {
                   responseText += `     - Compare at Price: ${variant.compareAtPrice}\n`;
                 }
                 if (includeInventory && variant.inventoryQuantity !== undefined) {
                   responseText += `     - Inventory: ${variant.inventoryQuantity}\n`;
                   responseText += `     - Policy: ${variant.inventoryPolicy || 'N/A'}\n`;
                 }
                 responseText += `     - Taxable: ${variant.taxable ? 'Yes' : 'No'}\n`;
               });
               responseText += `\n`;
             }
            
            if (product.options?.length) {
              responseText += `**Options:**\n`;
              product.options.forEach((option, optIndex) => {
                responseText += `  ${optIndex + 1}. ${option.name}: ${option.values.join(', ')}\n`;
              });
              responseText += `\n`;
            }
            
            responseText += `---\n\n`;
          });
        }

        // Add pagination info
        if (products.pageInfo.hasNextPage) {
          responseText += `**Next Page Available:** Use cursor \`${products.pageInfo.endCursor}\` to get more products\n\n`;
        }

        responseText += `*Query executed successfully against Shopify Admin API*`;

        recordUsage(
          "get-products",
          params,
          { success: true, productCount, hasNextPage: products.pageInfo.hasNextPage }
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
        console.error("Error in get-products tool:", error);
        
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
          "get-products",
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
export { getProductsTool };

