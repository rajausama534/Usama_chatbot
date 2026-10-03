# Shopify integration for Usama (planned seventh service)

Shopify store creation requires the store owner to sign up or authorize a store. No store or account is created by adding this file.

**Architecture**: Keep Shopify as the storefront and source of truth for products, inventory, checkout and orders. Use a store-specific Shopify app created through the Shopify Dev Dashboard with only the necessary access scopes. Shopify's GraphQL Admin API handles store management. An optional, vetted MCP server can wrap the authorized API for Usama. The existing actions/mcp_read.py bridge supports only explicitly allowlisted, *read-only stdio* MCP tools: it does not itself authenticate with Shopify or support Shopify's hosted HTTP MCP endpoints.

**Sequence after account creation**
1. Choose business name, country, currency, domain, shipping, taxes and payment provider in the owner's Shopify account.
2. Build/publish the Shopify theme or storefront; test mobile layout, product pages, checkout and order notifications before launch.
3. Create and install a store-specific app in Shopify's Dev Dashboard; approve only needed scopes. Keep client secrets and generated credentials in local environment/secret storage, never in GitHub or prompts.
4. Read-only first: verify store identity, list sample products and (only if permission is necessary) read sample order metadata. Configure a reviewed read-only MCP tool in the local mcp_servers.json and USAMA_MCP_READ_ALLOWLIST if using a compatible stdio MCP server.
5. Separate confirmation-gated actions for creating products, editing prices/inventory, customer messaging and fulfilling/refunding orders. After timeouts, query operation status before attempting again.
6. Keep Shopify data separate from the existing Supabase/Vercel real-estate CRM unless the owner explicitly asks to sync specific data.

**Sources**: Shopify custom apps and API authorization: https://help.shopify.com/en/manual/apps/installing-apps ; Shopify GraphQL Admin API: https://shopify.dev/docs/apps/build/apis ; Shopify account/store creation: https://help.shopify.com/manual/organization-settings/stores/create-store .

**Status**: Implementation design documented; Shopify account creation, app installation, MCP server selection, authorization and end-to-end tests are not completed. The existing six integrations are not modified.
