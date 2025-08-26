# Get Order by ID Tool

This tool retrieves detailed information about a specific order from the Shopify Admin API using GraphQL.

## Features

- Retrieves complete order details including pricing, customer info, shipping address, and line items
- Handles authentication and error cases gracefully
- Provides formatted, readable output
- Includes comprehensive error messages with setup instructions

## Setup

### 1. Create a Shopify Private App

1. Go to your Shopify admin panel
2. Navigate to **Apps** > **Develop apps**
3. Click **Create an app**
4. Choose **Create app manually**
5. Give your app a name (e.g., "MCP Order Tool")
6. Click **Create app**

### 2. Configure App Permissions

1. In your app settings, go to **Configuration** > **Admin API access scopes**
2. Add the following scopes:
   - `read_orders` - To read order information
   - `read_customers` - To read customer information (optional, for customer details)
3. Click **Save**

### 3. Generate Access Token

1. Go to **API credentials** tab
2. Click **Install app**
3. Copy the **Admin API access token** (starts with `shpat_`)

### 4. Set Environment Variables

Set the following environment variables:

```bash
export SHOPIFY_ACCESS_TOKEN="shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"
```

**Note:** Replace `your-store.myshopify.com` with your actual store domain.

## Usage

### Tool Parameters

- `conversationId` (required): Conversation ID from learn_shopify_api tool
- `orderId` (required): The ID of the order to retrieve

### Example Usage

```typescript
// The tool will be called with:
{
  "conversationId": "your-conversation-id",
  "orderId": "gid://shopify/Order/123456789"
}
```

### Response Format

The tool returns a formatted markdown response with:

- **Order Details**: ID, name, creation date, status
- **Pricing Information**: Total, subtotal, shipping, tax
- **Customer Information**: Name, email, phone
- **Shipping Address**: Complete address details
- **Line Items**: Product details, quantities, prices
- **Additional Information**: Tags, notes
- **Metafields**: Custom order metadata

## Error Handling

The tool provides detailed error messages for common issues:

### Authentication Errors
- Missing or invalid access token
- Missing store domain
- Setup instructions included

### Order Not Found
- Invalid order ID
- Order doesn't exist
- Permission issues

### GraphQL Errors
- API errors
- Network issues
- Invalid queries

## GraphQL Query

The tool executes the following GraphQL query:

```graphql
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
```

## Security Notes

- Store your access token securely
- Never commit tokens to version control
- Use environment variables for configuration
- Regularly rotate your access tokens
- Only grant necessary permissions to your app

## Troubleshooting

### Common Issues

1. **"Order not found" error**
   - Verify the order ID is correct
   - Ensure the order exists in your store
   - Check that your app has the necessary permissions

2. **Authentication errors**
   - Verify your access token is correct
   - Ensure your store domain is properly formatted
   - Check that your app is installed and active

3. **Permission errors**
   - Verify your app has the `read_orders` scope
   - Check that the app is properly installed

### Getting Order IDs

Order IDs in Shopify are typically in the format `gid://shopify/Order/123456789`. You can find them:

1. In the Shopify admin under **Orders**
2. In the URL when viewing an order
3. Through the Shopify Admin API
4. In webhook payloads

## API Version

This tool uses the Shopify Admin API version `2025-01`. The GraphQL endpoint is:
```
https://{store-domain}/admin/api/2025-01/graphql.json
```
