import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the GraphQL client before importing the module
vi.mock("graphql-request", () => ({
  GraphQLClient: vi.fn().mockImplementation(() => ({
    request: vi.fn(),
  })),
  gql: vi.fn((strings) => strings.join("")),
}));

// Import after mocking
import getOrderByIdTool from "./index.js";

// Mock environment variables
const originalEnv = process.env;

describe("getOrderByIdTool", () => {
  let server: McpServer;

  beforeEach(() => {
    // Reset environment
    process.env = { ...originalEnv };
    
    // Create mock server
    server = {
      tool: vi.fn(),
    } as any;
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.clearAllMocks();
  });

  it("should register the tool with correct parameters", async () => {
    await getOrderByIdTool(server);

    expect(server.tool).toHaveBeenCalledWith(
      "get-order-by-id",
      "Get a specific order by ID from Shopify Admin API",
      expect.any(Object), // schema
      expect.any(Function) // handler
    );
  });

  it("should throw error when credentials are missing", async () => {
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    // Test without environment variables
    const result = await toolHandler({
      conversationId: "test-conversation",
      orderId: "gid://shopify/Order/123",
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Authentication Error");
    expect(result.content[0].text).toContain("SHOPIFY_ACCESS_TOKEN");
    expect(result.content[0].text).toContain("SHOPIFY_STORE_DOMAIN");
  });

  it("should handle missing environment variables gracefully", async () => {
    // Test with missing access token
    process.env.SHOPIFY_STORE_DOMAIN = "test-store.myshopify.com";
    
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    const result = await toolHandler({
      conversationId: "test-conversation",
      orderId: "gid://shopify/Order/123",
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Authentication Error");
  });

  it("should handle missing store domain gracefully", async () => {
    // Test with missing store domain
    process.env.SHOPIFY_ACCESS_TOKEN = "test-token";
    
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    const result = await toolHandler({
      conversationId: "test-conversation",
      orderId: "gid://shopify/Order/123",
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Authentication Error");
  });

  it("should validate order ID parameter", async () => {
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    // Test with empty order ID
    const result = await toolHandler({
      conversationId: "test-conversation",
      orderId: "",
    });

    expect(result.isError).toBe(true);
  });

  it("should handle conversation ID parameter", async () => {
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    // Test with missing conversation ID
    const result = await toolHandler({
      orderId: "gid://shopify/Order/123",
    });

    expect(result.isError).toBe(true);
  });

  it("should provide helpful error messages", async () => {
    await getOrderByIdTool(server);
    const toolHandler = (server.tool as any).mock.calls[0][3];

    const result = await toolHandler({
      conversationId: "test-conversation",
      orderId: "gid://shopify/Order/123",
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("To use this tool, you need to set up Shopify Admin API credentials");
    expect(result.content[0].text).toContain("Create a private app in your Shopify admin");
    expect(result.content[0].text).toContain("SHOPIFY_ACCESS_TOKEN");
    expect(result.content[0].text).toContain("SHOPIFY_STORE_DOMAIN");
  });
});
