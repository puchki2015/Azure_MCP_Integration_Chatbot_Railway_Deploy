# Azure Price Calculator Status

## Goal
Build an Azure cost estimator that accepts plain-English resource needs, resolves them to Azure pricing data, and returns a cost estimate.

## Current Direction
- Use the official Azure Retail Prices API as the primary pricing source.
- Cache prices locally and refresh them on a schedule.
- Parse user intent into structured resource specs before pricing.

## v1 Scope
- Virtual Machines
- Storage Accounts
- Managed Disks
- Bandwidth
- App Service

## Backend Flow
1. Parse user input into normalized resources.
2. Resolve each resource to a pricing query.
3. Fetch latest matching price from Azure Retail Prices API when needed.
4. Store the price snapshot and normalized rows in the database.
5. Calculate monthly and hourly estimates from the cached price data.

## Pricing Source
- Official API:
  - https://prices.azure.com/api/retail/prices
- Microsoft documentation:
  - https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices

## Open Questions
- Which Azure services should be supported first beyond the initial v1 scope?
- Should the user input be free-form text, a form, or both?
- Which regions and currency should be supported?
- Should estimates be exact or approximate?

## Next Steps
- Define the database schema for pricing snapshots and estimates.
- Define the API endpoints for submitting resource needs and returning estimates.
- Implement the Azure pricing fetcher and cache layer.
- Implement the input parser and matching logic for resource-to-meter resolution.
