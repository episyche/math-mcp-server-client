import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import getStoreAnalyticsTool from "./index.js";

// Mock the GraphQL client
vi.mock("graphql-request", () => ({
  GraphQLClient: vi.fn().mockImplementation(() => ({
    request: vi.fn().mockResolvedValue({
      shop: {
        id: "gid://shopify/Shop/123",
        name: "Test Store",
        email: "test@example.com",
        currencyCode: "USD",
        primaryDomain: {
          url: "https://test-store.myshopify.com",
          host: "test-store.myshopify.com"
        },
        plan: {
          displayName: "Basic Shopify",
          partnerDevelopment: false,
          shopifyPlus: false
        },
        createdAt: "2024-01-01T00:00:00Z",
        updatedAt: "2024-01-01T00:00:00Z"
      },
      orders: {
        edges: [
          {
            node: {
              id: "gid://shopify/Order/1",
              name: "#1001",
              createdAt: "2024-01-01T00:00:00Z",
              displayFinancialStatus: "PAID",
              totalPriceSet: {
                shopMoney: {
                  amount: "100.00",
                  currencyCode: "USD"
                }
              }
            }
          }
        ],
        pageInfo: {
          hasNextPage: false
        }
      },
      products: {
        edges: [
          {
            node: {
              id: "gid://shopify/Product/1",
              title: "Test Product",
              status: "ACTIVE",
              totalInventory: 10,
              createdAt: "2024-01-01T00:00:00Z"
            }
          }
        ],
        pageInfo: {
          hasNextPage: false
        }
      },
      customers: {
        edges: [
          {
            node: {
              id: "gid://shopify/Customer/1",
              firstName: "John",
              lastName: "Doe",
              email: "john@example.com",
              createdAt: "2024-01-01T00:00:00Z",
              amountSpent: {
                amount: "100.00",
                currencyCode: "USD"
              },
              numberOfOrders: 1
            }
          }
        ],
        pageInfo: {
          hasNextPage: false
        }
      }
    })
  })),
  gql: vi.fn((query) => query)
}));

// Mock instrumentation
vi.mock("../../instrumentation.js", () => ({
  recordUsage: vi.fn().mockResolvedValue(undefined)
}));

describe("getStoreAnalyticsTool", () => {
  let server: McpServer;

  beforeEach(() => {
    server = {
      tool: vi.fn()
    } as any;
  });

  it("should register the tool with correct parameters", () => {
    getStoreAnalyticsTool(server);
    
    expect(server.tool).toHaveBeenCalledWith(
      "get-store-analytics",
      "Get store analytics and statistics from Shopify Admin API",
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("should handle successful analytics request", async () => {
    getStoreAnalyticsTool(server);
    
    const toolFunction = (server.tool as any).mock.calls[0][3];
    const result = await toolFunction({
      includeOrders: true,
      includeProducts: true,
      includeCustomers: true,
      includeInventory: false,
      dateRange: "all_time",
      limit: 10
    });

    expect(result.isError).toBe(false);
    expect(result.content[0].text).toContain("Store Analytics - Test Store");
    expect(result.content[0].text).toContain("**Total Orders:** 1");
    expect(result.content[0].text).toContain("**Total Products:** 1");
    expect(result.content[0].text).toContain("**Total Customers:** 1");
  });

  it("should handle custom limit parameter", async () => {
    getStoreAnalyticsTool(server);
    
    const toolFunction = (server.tool as any).mock.calls[0][3];
    const result = await toolFunction({
      includeOrders: true,
      includeProducts: true,
      includeCustomers: true,
      includeInventory: false,
      dateRange: "all_time",
      limit: 5
    });

    expect(result.isError).toBe(false);
    expect(result.content[0].text).toContain("Store Analytics - Test Store");
  });

  it("should handle partial data requests", async () => {
    getStoreAnalyticsTool(server);
    
    const toolFunction = (server.tool as any).mock.calls[0][3];
    const result = await toolFunction({
      includeOrders: true,
      includeProducts: false,
      includeCustomers: false,
      includeInventory: false,
      dateRange: "all_time",
      limit: 10
    });

    expect(result.isError).toBe(false);
    expect(result.content[0].text).toContain("Orders Analytics (1 orders)");
    expect(result.content[0].text).not.toContain("Products Analytics");
    expect(result.content[0].text).not.toContain("Customers Analytics");
  });
});
