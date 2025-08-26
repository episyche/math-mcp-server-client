# Shopify MCP Server Integration

This directory contains the Shopify MCP (Model Context Protocol) server that integrates with your existing MCP client orchestrator.

## Overview

The Shopify MCP server provides Python interfaces to Shopify functionality, allowing you to:
- Manage products, customers, and orders
- Access store analytics and inventory
- Search Shopify documentation
- Learn about Shopify APIs
- Introspect GraphQL schemas
- Validate GraphQL code

## Files

- `shopify_mcp_server.py` - Main MCP server implementation
- `README_SHOPIFY.md` - This documentation file

## Features

### Core Shopify Operations
- **Products**: Retrieve, filter, and search products with variants, images, and inventory
- **Customers**: Manage customer data with addresses and order history
- **Orders**: Track orders with status, financial, and fulfillment information
- **Inventory**: Monitor stock levels across locations
- **Analytics**: Access store performance metrics

### Developer Tools
- **Documentation Search**: Find relevant Shopify documentation
- **API Learning**: Get structured learning resources for specific topics
- **GraphQL Introspection**: Explore available GraphQL operations
- **Code Validation**: Validate GraphQL queries and mutations

## Installation

1. Ensure you have the required Python packages:
   ```bash
   pip install mcp requests
   ```

2. Set environment variables for real Shopify API access (optional):
   ```bash
   export SHOPIFY_STORE_URL="your-store.myshopify.com"
   export SHOPIFY_ACCESS_TOKEN="your-access-token"
   export SHOPIFY_API_VERSION="2024-01"
   ```

   Note: If these are not set, the server will use mock data for demonstration.

## Usage

### Direct Server Usage
```bash
python shopify/shopify_mcp_server.py
```

### Through MCP Client Orchestrator
The server is automatically integrated with your main orchestrator. You can now ask questions like:

- "Show me the first 5 products from my Shopify store"
- "Get customer count statistics"
- "What are my recent orders?"
- "Search Shopify documentation for product API"
- "Learn about the Shopify orders API"
- "Get store analytics for the last 30 days"

### Example Tool Calls

#### Get Products
```python
# Get 10 active products
result = await session.call_tool(
    name="get_products",
    arguments={
        "limit": 10,
        "status": "active",
        "include_variants": True,
        "include_images": True
    }
)
```

#### Get Customers
```python
# Get customers with addresses included
result = await session.call_tool(
    name="get_customers",
    arguments={
        "limit": 20,
        "include_addresses": True,
        "include_orders": False
    }
)
```

#### Search Documentation
```python
# Search for product-related documentation
result = await session.call_tool(
    name="search_shopify_docs",
    arguments={"query": "product creation"}
)
```

## Testing

Run the test script to verify the server is working:

```bash
python test_shopify.py
```

This will test:
- Server initialization
- Tool listing
- Basic tool calls
- Response handling

## Configuration

### Environment Variables
- `SHOPIFY_STORE_URL`: Your Shopify store URL (e.g., "mystore.myshopify.com")
- `SHOPIFY_ACCESS_TOKEN`: Private app access token
- `SHOPIFY_API_VERSION`: Shopify API version (default: "2024-01")

### Mock Mode
When environment variables are not set, the server operates in mock mode, providing realistic sample data for testing and development.

## Integration with Existing MCP System

The Shopify server is automatically integrated into your MCP orchestrator:

1. **Server Discovery**: Added to `get_available_server_scripts()` in `mcp_client.py`
2. **Tool Schemas**: Defined in `DEFAULT_CAPABILITIES` in `orchestrator.py`
3. **Routing**: Integrated into the LLM routing system
4. **Argument Normalization**: Handles parameter type conversion

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_products` | Retrieve products with filtering | limit, status, vendor, product_type, tag, query, cursor, include_variants, include_images, include_inventory |
| `get_customers` | Retrieve customers with options | limit, query, cursor, include_addresses, include_orders |
| `get_orders` | Retrieve orders with filtering | limit, status, financial_status, fulfillment_status, created_at_min, created_at_max, query, cursor |
| `get_customer_counts` | Get customer statistics | count_type, custom_query |
| `search_shopify_docs` | Search documentation | query |
| `learn_shopify_api` | Get learning resources | topic |
| `introspect_graphql_schema` | Explore GraphQL schema | operation |
| `validate_graphql_codeblocks` | Validate GraphQL code | code |
| `get_store_info` | Get store details | (none) |
| `get_inventory_levels` | Get inventory data | location_ids |
| `get_analytics` | Get store metrics | metric, date_range |

## Error Handling

The server includes comprehensive error handling:
- Parameter validation
- API error responses
- Graceful fallbacks to mock data
- Detailed error logging

## Future Enhancements

Potential improvements:
- Real Shopify API integration
- Webhook support
- Bulk operations
- Advanced filtering
- Real-time inventory updates
- Custom app integration

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure MCP packages are installed
2. **Permission Errors**: Check file permissions on the server script
3. **Connection Issues**: Verify Shopify API credentials if using real API
4. **Tool Not Found**: Ensure the server is properly registered in the orchestrator

### Debug Mode
Enable debug logging by setting the log level:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues with the Shopify MCP server:
1. Check the logs for error messages
2. Verify environment variable configuration
3. Test with the provided test script
4. Review the MCP protocol implementation

## License

This integration follows the same license as your main project.
